"""Robust data curation pipeline with validation, metadata, and manifest output."""

from __future__ import annotations

import hashlib
import json
import shutil
from uuid import uuid4
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from src.ai_packager import AIPackager
from src.cleaning import DataCleaner
from src.config import Config
from src.dataset_catalog import DatasetCatalog
from src.metadata import MetadataGenerator


@dataclass
class PipelineValidationConfig:
    min_rows: int = 10
    min_columns: int = 2
    max_null_percentage: float = 40.0
    min_completeness_score: float = 60.0


@dataclass
class PipelineOptions:
    topic: str
    source: str
    coverage: str = "global"
    url: Optional[str] = None
    identifier: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    force: bool = False
    strict_validation: bool = True
    create_ai_package: bool = True
    rag_index: bool = False


class PipelineRunner:
    """Run the end-to-end data pipeline with validation and manifest output."""

    def __init__(
        self,
        config: Config,
        validation: Optional[PipelineValidationConfig] = None,
    ) -> None:
        self.config = config
        self.validation = validation or self._load_validation_config()

    def _load_validation_config(self) -> PipelineValidationConfig:
        cfg = self.config.config.get("pipeline") or {}
        return PipelineValidationConfig(
            min_rows=int(cfg.get("min_rows", 10)),
            min_columns=int(cfg.get("min_columns", 2)),
            max_null_percentage=float(cfg.get("max_null_percentage", 40.0)),
            min_completeness_score=float(cfg.get("min_completeness_score", 60.0)),
        )

    def run(self, input_file: Path, options: PipelineOptions) -> Dict[str, Any]:
        start_time = datetime.utcnow()
        run_id = uuid4().hex
        manifest: Dict[str, Any] = {
            "status": "started",
            "pipeline_version": "1.0",
            "run_id": run_id,
            "started_at": start_time.isoformat(),
        }

        output_path: Optional[Path] = None
        metadata_path: Optional[Path] = None
        quality_path: Optional[Path] = None

        try:
            raw_path = self._stage_raw_file(input_file)
            raw_hash = self._compute_file_hash(raw_path)
            manifest["input"] = {
                "path": str(raw_path),
                "hash": raw_hash,
                "size_bytes": raw_path.stat().st_size,
            }

            df = self._load_dataframe(raw_path)
            cleaner = DataCleaner(self.config)
            cleaned = cleaner.clean_dataset(df)

            if options.coverage and options.coverage.lower() != "global":
                cleaned = cleaner.filter_by_region(cleaned, options.coverage)

            data_summary = cleaner.get_data_summary(cleaned)
            validation = self._validate(cleaned, data_summary)
            manifest["validation"] = validation

            if options.strict_validation and not validation["passed"]:
                raise ValueError("Validation failed: " + "; ".join(validation["issues"]))

            output_path = cleaner.save_clean_dataset(
                cleaned,
                topic=options.topic,
                source=options.source,
                coverage=options.coverage,
                start_year=options.start_year,
                end_year=options.end_year,
                identifier=options.identifier,
            )

            manifest["output"] = {
                "clean_path": str(output_path),
                "clean_hash": self._compute_file_hash(output_path),
                "size_bytes": output_path.stat().st_size,
                "rows": data_summary.get("rows"),
                "columns": data_summary.get("columns"),
            }

            metadata_gen = MetadataGenerator(self.config)
            metadata_text = metadata_gen.generate_metadata(
                topic=options.topic,
                data_summary=data_summary,
                source=options.source,
                transformations=cleaner.get_transformations(),
                original_source_url=options.url,
                dataset_info={
                    "identifier": options.identifier,
                    "indicator_name": options.identifier or output_path.stem,
                    "file_name": output_path.name,
                },
                force_regenerate=options.force,
            )
            metadata_path = metadata_gen.save_metadata_for_dataset(output_path, metadata_text)

            ai_files: Dict[str, Any] = {}
            if options.create_ai_package:
                metadata_stub = self._build_ai_metadata_stub(
                    data_summary=data_summary,
                    topic=options.topic,
                    source=options.source,
                    identifier=options.identifier or output_path.stem,
                    description="",
                    source_url=options.url,
                )
                packager = AIPackager(output_path.parent)
                ai_files = {
                    k: str(v) for k, v in packager.package_dataset(
                        cleaned,
                        metadata_stub,
                        topic=options.topic,
                        source=options.source,
                        output_path=output_path.parent,
                    ).items()
                }

            catalog = DatasetCatalog(self.config)
            dataset_id = catalog.index_dataset(output_path, force=True)

            rag_indexed = False
            if options.rag_index and self.config.get_rag_config().get("enabled", False):
                from src.rag.index import build_index

                build_index(
                    config=self.config,
                    index_docs=False,
                    index_catalog=True,
                    index_tools=False,
                )
                rag_indexed = True

            manifest.update(
                {
                    "status": "success",
                    "metadata_path": str(metadata_path),
                    "ai_package": ai_files,
                    "catalog_id": dataset_id,
                    "rag_indexed": rag_indexed,
                }
            )

            return manifest

        except Exception as exc:
            manifest["status"] = "error"
            manifest["error"] = str(exc)
            raise

        finally:
            finish_time = datetime.utcnow()
            manifest["finished_at"] = finish_time.isoformat()
            if output_path:
                quality_path = self._write_quality_report(output_path, manifest.get("validation") or {})
            if metadata_path:
                manifest["metadata_path"] = str(metadata_path)
            if quality_path:
                manifest["quality_report_path"] = str(quality_path)
            self._write_manifest(output_path, manifest)

    def _load_dataframe(self, path: Path) -> pd.DataFrame:
        if path.suffix.lower() == ".parquet":
            return pd.read_parquet(path)
        return pd.read_csv(path)

    def _stage_raw_file(self, input_file: Path) -> Path:
        raw_dir = self.config.get_directory("raw")
        raw_dir.mkdir(parents=True, exist_ok=True)
        input_file = Path(input_file)
        try:
            input_file = input_file.resolve()
        except Exception:
            input_file = Path(input_file)

        if raw_dir in input_file.parents:
            return input_file

        dest = raw_dir / input_file.name
        if dest.exists():
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            dest = raw_dir / f"{input_file.stem}_{timestamp}{input_file.suffix}"
        shutil.copyfile(input_file, dest)
        return dest

    def _compute_file_hash(self, file_path: Path) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _validate(self, df: pd.DataFrame, summary: Dict[str, Any]) -> Dict[str, Any]:
        total_cells = int(df.shape[0] * df.shape[1])
        null_cells = int(df.isna().sum().sum()) if total_cells else 0
        null_percentage = (null_cells / total_cells * 100) if total_cells else 0
        completeness_score = max(0.0, 100.0 - null_percentage)

        issues = []
        if summary.get("rows", 0) < self.validation.min_rows:
            issues.append(f"row_count<{self.validation.min_rows}")
        if summary.get("columns", 0) < self.validation.min_columns:
            issues.append(f"column_count<{self.validation.min_columns}")
        if null_percentage > self.validation.max_null_percentage:
            issues.append(f"null_percentage>{self.validation.max_null_percentage}")
        if completeness_score < self.validation.min_completeness_score:
            issues.append(f"completeness_score<{self.validation.min_completeness_score}")

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "row_count": summary.get("rows"),
            "column_count": summary.get("columns"),
            "null_percentage": round(null_percentage, 2),
            "completeness_score": round(completeness_score, 2),
            "year_range": summary.get("year_range"),
            "country_count": summary.get("country_count"),
            "thresholds": {
                "min_rows": self.validation.min_rows,
                "min_columns": self.validation.min_columns,
                "max_null_percentage": self.validation.max_null_percentage,
                "min_completeness_score": self.validation.min_completeness_score,
            },
        }

    def _build_ai_metadata_stub(
        self,
        data_summary: Dict[str, Any],
        topic: str,
        source: str,
        identifier: str,
        description: str,
        source_url: Optional[str],
    ) -> Dict[str, Any]:
        return {
            "title": identifier,
            "slug": identifier,
            "description": description,
            "sources": [{"name": source, "url": source_url or ""}],
            "unit": "",
            "data_stats": {
                "total_rows": data_summary.get("rows"),
                "total_columns": data_summary.get("columns"),
                "columns": data_summary.get("column_names"),
                "date_range": {
                    "min_year": (data_summary.get("year_range") or [None, None])[0],
                    "max_year": (data_summary.get("year_range") or [None, None])[1],
                },
                "countries_count": data_summary.get("country_count"),
            },
            "topic": topic,
        }

    def _write_manifest(self, output_path: Optional[Path], manifest: Dict[str, Any]) -> None:
        metadata_dir = self.config.get_directory("metadata")
        metadata_dir.mkdir(parents=True, exist_ok=True)
        if output_path:
            stem = output_path.stem
        else:
            stem = f"pipeline_run_{manifest.get('run_id', 'unknown')}"
        manifest_path = metadata_dir / f"{stem}.manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=True)

    def _write_quality_report(self, output_path: Path, validation: Dict[str, Any]) -> Path:
        metadata_dir = self.config.get_directory("metadata")
        metadata_dir.mkdir(parents=True, exist_ok=True)
        report_path = metadata_dir / f"{output_path.stem}.quality.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(validation, f, indent=2, ensure_ascii=True)
        return report_path

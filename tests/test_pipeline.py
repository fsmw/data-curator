import json
from pathlib import Path

import pandas as pd
import pytest

from src.config import Config
from src.dataset_catalog import DatasetCatalog
from src.pipeline import PipelineRunner, PipelineOptions


def _write_config(tmp_path: Path) -> Path:
    config_text = """
directories:
  raw: "01_Raw_Data_Bank"
  clean: "02_Datasets_Limpios"
  metadata: "03_Metadata_y_Notas"
  graphics: "04_Graficos_Asociados"
sources:
  - test
topics:
  - general
cleaning:
  drop_empty_rows: true
  drop_empty_columns: true
  standardize_country_codes: false
  normalize_dates: false
metadata:
  use_llm: false
  fallback_template: true
  cache_enabled: false
  template_sections:
    - source
    - variables
    - coverage
    - transformations
    - warnings
pipeline:
  min_rows: 5
  min_columns: 2
  max_null_percentage: 40.0
  min_completeness_score: 60.0
rag:
  enabled: false
  top_k: 5
  embedding_provider: local
  embedding_model: all-MiniLM-L6-v2
  embedding_base_url: ""
llm:
  max_tokens: 2000
  temperature: 0.3
  system_prompt: "Test"
"""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(config_text.strip() + "\n", encoding="utf-8")
    return config_path


def _write_input_csv(tmp_path: Path, rows: int) -> Path:
    df = pd.DataFrame(
        {
            "year": list(range(2000, 2000 + rows)),
            "country": ["Argentina"] * rows,
            "value": list(range(rows)),
        }
    )
    input_path = tmp_path / "input.csv"
    df.to_csv(input_path, index=False)
    return input_path


def test_pipeline_success_creates_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))
    config_path = _write_config(tmp_path)
    input_path = _write_input_csv(tmp_path, rows=6)

    cfg = Config(str(config_path))
    runner = PipelineRunner(cfg)
    options = PipelineOptions(
        topic="general",
        source="test",
        coverage="global",
        identifier="sample",
        url="https://example.com",
        strict_validation=True,
        create_ai_package=True,
        rag_index=False,
    )

    manifest = runner.run(input_path, options)
    assert manifest["status"] == "success"

    output_path = Path(manifest["output"]["clean_path"])
    assert output_path.exists()

    metadata_path = Path(manifest["metadata_path"])
    assert metadata_path.exists()

    quality_path = Path(manifest["quality_report_path"])
    assert quality_path.exists()

    manifest_path = cfg.get_directory("metadata") / f"{output_path.stem}.manifest.json"
    assert manifest_path.exists()
    manifest_on_disk = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_on_disk["status"] == "success"
    assert manifest_on_disk["metadata_path"] == str(metadata_path)
    assert manifest_on_disk["quality_report_path"] == str(quality_path)

    ai_files = manifest["ai_package"]
    assert Path(ai_files["schema"]).exists()
    assert Path(ai_files["context"]).exists()
    assert Path(ai_files["prompts"]).exists()
    assert Path(ai_files["summary"]).exists()

    raw_dir = cfg.get_directory("raw")
    assert any(raw_dir.glob("input*.csv"))

    catalog = DatasetCatalog(cfg)
    dataset = catalog.get_dataset(manifest["catalog_id"])
    assert dataset is not None


def test_pipeline_validation_failure_writes_manifest(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))
    config_path = _write_config(tmp_path)
    input_path = _write_input_csv(tmp_path, rows=2)

    cfg = Config(str(config_path))
    runner = PipelineRunner(cfg)
    options = PipelineOptions(
        topic="general",
        source="test",
        coverage="global",
        strict_validation=True,
        create_ai_package=False,
    )

    with pytest.raises(ValueError):
        runner.run(input_path, options)

    metadata_dir = cfg.get_directory("metadata")
    manifests = list(metadata_dir.glob("pipeline_run_*.manifest.json"))
    assert len(manifests) == 1
    manifest_on_disk = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert manifest_on_disk["status"] == "error"

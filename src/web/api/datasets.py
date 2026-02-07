"""
Dataset API endpoints.

Handles dataset CRUD operations, preview, statistics, and management.
"""

from flask import request, jsonify, Response, send_file, after_this_request
import json
import math
import re
import sqlite3
import pandas as pd
from pathlib import Path
from io import StringIO
import os
import tempfile
import shutil
import zipfile
from datetime import datetime

from config import Config
from dataset_catalog import DatasetCatalog
from metadata import MetadataGenerator
from cleaning import DataCleaner
from src.logger import get_logger
from utils.serialization import clean_nan_recursive
from ingestion import OECDSource, OWIDSource
from ai_packager import AIPackager
import requests

from . import api_bp

logger = get_logger(__name__)


def _format_dataset(ds: dict) -> dict:
    dataset = dict(ds)
    if dataset.get("countries_json"):
        try:
            dataset["countries"] = json.loads(dataset["countries_json"])
        except Exception:
            dataset["countries"] = []
    else:
        dataset["countries"] = []

    if dataset.get("columns_json"):
        try:
            dataset["columns"] = json.loads(dataset["columns_json"])
        except Exception:
            dataset["columns"] = []
    else:
        dataset["columns"] = []

    for key in [
        "null_percentage",
        "completeness_score",
        "min_year",
        "max_year",
        "row_count",
        "column_count",
        "country_count",
        "file_size_bytes",
        "is_edited",
    ]:
        if key in dataset and (
            dataset[key] is None
            or (isinstance(dataset[key], float) and math.isnan(dataset[key]))
        ):
            dataset[key] = 0

    return dataset


def _add_directory_to_zip(zip_file: zipfile.ZipFile, directory: Path, arc_prefix: str) -> None:
    for root, _, files in os.walk(directory):
        for filename in files:
            file_path = Path(root) / filename
            arcname = Path(arc_prefix) / file_path.relative_to(directory)
            zip_file.write(file_path, arcname.as_posix())


@api_bp.route("/datasets")
def list_datasets() -> Response:
    """
    List and search datasets in the catalog.

    Query params:
        q: Search query (optional)
        source: Filter by source (optional)
        topic: Filter by topic (optional)
        limit: Max results (default 100)
        latest: Return only latest version per identifier (optional)
    """
    try:
        config = Config()
        catalog = DatasetCatalog(config)

        # Get query parameters
        query = request.args.get("q", "")
        source = request.args.get("source", "")
        topic = request.args.get("topic", "")
        limit = int(request.args.get("limit", 100))

        # Build filters
        filters = {}
        if source:
            filters["source"] = source
        if topic:
            filters["topic"] = topic

        # If user wants latest-per-identifier, use specialized method
        latest_only = request.args.get("latest", "false").lower() == "true"
        if latest_only:
            results = catalog.latest_per_identifier()
        else:
            # Search datasets
            results = catalog.search(query, filters=filters, limit=limit)

        # Format results
        datasets = [_format_dataset(ds) for ds in results]

        return jsonify(
            {"status": "success", "total": len(datasets), "datasets": datasets}
        )

    except Exception as e:
        logger.error(f"Error listing datasets: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/datasets/<int:dataset_id>")
def get_dataset_detail(dataset_id: int) -> Response:
    """Fetch a single dataset record."""
    try:
        config = Config()
        catalog = DatasetCatalog(config)
        dataset = catalog.get_dataset(dataset_id)
        if not dataset:
            return jsonify({"status": "error", "message": "Dataset not found"}), 404

        return jsonify({"status": "success", "dataset": _format_dataset(dataset)})

    except Exception as e:
        logger.error(f"Error getting dataset {dataset_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/datasets/refresh-selected", methods=["POST"])
def refresh_selected_datasets() -> Response:
    """Refresh selected datasets by re-indexing and updating OWID notes."""
    try:
        payload = request.get_json(silent=True) or {}
        dataset_ids = payload.get("dataset_ids") or []
        if not isinstance(dataset_ids, list) or not dataset_ids:
            return jsonify({"status": "error", "message": "Missing dataset_ids"}), 400

        parsed_ids = []
        for dataset_id in dataset_ids:
            try:
                parsed_ids.append(int(dataset_id))
            except (TypeError, ValueError):
                continue

        if not parsed_ids:
            return jsonify({"status": "error", "message": "Invalid dataset_ids"}), 400

        config = Config()
        catalog = DatasetCatalog(config)
        generator = MetadataGenerator(config)
        owid_source = OWIDSource(config.get_directory("raw"))

        updated = 0
        notes_updated = 0
        errors = []

        for dataset_id in parsed_ids:
            dataset = catalog.get_dataset(dataset_id)
            if not dataset:
                errors.append({"id": dataset_id, "error": "Dataset not found"})
                continue

            file_path = Path(dataset["file_path"])
            if not file_path.exists():
                errors.append({"id": dataset_id, "error": "Dataset file not found"})
                continue

            catalog.index_dataset(file_path, force=True)
            updated += 1

            if (dataset.get("source") or "").lower() == "owid" and dataset.get("indicator_id"):
                try:
                    owid_metadata = owid_source.fetch_metadata(dataset["indicator_id"])
                    if "error" not in owid_metadata:
                        ai_packager = AIPackager(file_path.parent)
                        metadata_text = ai_packager.create_context_owid(owid_metadata)
                        generator.save_metadata_for_dataset(file_path, metadata_text)
                        notes_updated += 1
                except Exception as e:
                    errors.append({"id": dataset_id, "error": f"OWID notes update failed: {e}"})

        return jsonify(
            {
                "status": "success",
                "updated": updated,
                "notes_updated": notes_updated,
                "errors": errors,
            }
        )

    except Exception as e:
        logger.error(f"Error refreshing selected datasets: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/datasets/<int:dataset_id>")
def get_dataset(dataset_id: int) -> Response:
    """Get detailed information about a specific dataset."""
    try:
        config = Config()
        catalog = DatasetCatalog(config)

        dataset = catalog.get_dataset(dataset_id)

        if not dataset:
            return jsonify({"status": "error", "message": "Dataset not found"}), 404

        # Parse JSON fields
        if dataset.get("countries_json"):
            dataset["countries"] = json.loads(dataset["countries_json"])
        if dataset.get("columns_json"):
            dataset["columns"] = json.loads(dataset["columns_json"])

        # Replace None/NaN with 0 for numeric fields
        for key in [
            "null_percentage",
            "completeness_score",
            "min_year",
            "max_year",
            "row_count",
            "column_count",
            "country_count",
            "file_size_bytes",
        ]:
            if key in dataset and (
                dataset[key] is None
                or (isinstance(dataset[key], float) and dataset[key] != dataset[key])
            ):
                dataset[key] = 0

        return jsonify({"status": "success", "dataset": dataset})

    except Exception as e:
        logger.error(f"Error getting dataset {dataset_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/datasets/<int:dataset_id>/preview")
def preview_dataset(dataset_id: int) -> Response:
    """
    Get preview data (first N rows) for a dataset.

    Query params:
        limit: Number of rows to return (default: 100, max: 1000)
    """
    try:
        config = Config()
        catalog = DatasetCatalog(config)

        limit = request.args.get("limit", default=100, type=int)
        limit = min(limit, 1000)  # Cap at 1000 rows

        # Get dataset info first
        dataset = catalog.get_dataset(dataset_id)
        if not dataset:
            return jsonify({"status": "error", "message": "Dataset not found"}), 404

        # Get preview data
        df = catalog.get_preview_data(dataset_id, limit=limit)

        if df is None:
            return jsonify(
                {"status": "error", "message": "Could not load dataset"}
            ), 500

        # Convert DataFrame to JSON-friendly format
        data_dict = df.to_dict(orient="records")
        cleaned_data = clean_nan_recursive(data_dict)

        preview_data = {
            "columns": df.columns.tolist(),
            "rows": cleaned_data,
            "total_rows": len(df),
            "dataset_info": {
                "id": dataset["id"],
                "file_name": dataset["file_name"],
                "source": dataset["source"],
                "indicator_name": dataset["indicator_name"],
                "row_count": dataset["row_count"],
                "column_count": dataset["column_count"],
            },
        }

        return jsonify({"status": "success", "preview": preview_data})

    except Exception as e:
        logger.error(f"Error previewing dataset {dataset_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/datasets/<int:dataset_id>/notes")
def get_dataset_notes(dataset_id: int) -> Response:
    """Get AI-generated notes for a dataset if available, generate on demand if missing."""
    try:
        config = Config()
        catalog = DatasetCatalog(config)
        dataset = catalog.get_dataset(dataset_id)

        if not dataset:
            return jsonify({"status": "error", "message": "Dataset not found"}), 404

        file_path = Path(dataset["file_path"])
        generator = MetadataGenerator(config)
        notes_path = generator.get_metadata_path_for_dataset(file_path)

        if not notes_path.exists():
            if (
                (dataset.get("source") or "").lower() == "owid"
                and dataset.get("indicator_id")
            ):
                try:
                    owid_source = OWIDSource(config.get_directory("raw"))
                    owid_metadata = owid_source.fetch_metadata(dataset["indicator_id"])
                    if "error" not in owid_metadata:
                        ai_packager = AIPackager(file_path.parent)
                        metadata_text = ai_packager.create_context_owid(owid_metadata)
                        notes_path = generator.save_metadata_for_dataset(file_path, metadata_text)
                except Exception as e:
                    logger.warning(f"OWID notes generation failed: {e}")

        if not notes_path.exists():
            topic_fallback = dataset.get("topic") or "general"
            fallback_path = generator.metadata_dir / f"{topic_fallback}.md"
            if fallback_path.exists():
                notes_path = fallback_path
            else:
                df = catalog.get_preview_data(dataset_id, limit=500)
                if df is None or df.empty:
                    return jsonify({"status": "success", "notes": ""})

                cleaner = DataCleaner(config)
                data_summary = cleaner.get_data_summary(df)
                metadata_text = generator.generate_metadata(
                    topic=topic_fallback,
                    data_summary=data_summary,
                    source=dataset.get("source", "unknown"),
                    transformations=[],
                    original_source_url="",
                    dataset_info={
                        "identifier": dataset.get("indicator_id") or dataset.get("file_name"),
                        "indicator_id": dataset.get("indicator_id"),
                        "indicator_name": dataset.get("indicator_name"),
                        "file_name": dataset.get("file_name"),
                    },
                    force_regenerate=False,
                )
                notes_path = generator.save_metadata_for_dataset(file_path, metadata_text)

        with open(notes_path, "r", encoding="utf-8") as f:
            notes = f.read()

        return jsonify({"status": "success", "notes": notes, "path": str(notes_path)})

    except Exception as e:
        logger.error(f"Error fetching notes for dataset {dataset_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/remote/owid/preview")
def preview_owid_remote() -> Response:
    """
    Preview OWID remote data without saving to disk.

    Query params:
        slug: OWID chart slug (required)
        countries: Comma-separated country names (optional)
        start_year: int (optional)
        end_year: int (optional)
        limit: max rows to return (default 200)
    """
    try:
        slug = request.args.get("slug", "").strip()
        if not slug:
            return jsonify(
                {"status": "error", "message": "Missing 'slug' parameter"}
            ), 400

        countries_arg = request.args.get("countries", "")
        countries = (
            [c.strip() for c in countries_arg.split(",") if c.strip()]
            if countries_arg
            else None
        )
        start_year = request.args.get("start_year", type=int)
        end_year = request.args.get("end_year", type=int)
        limit = request.args.get("limit", default=200, type=int)
        limit = min(limit, 1000)

        # Build OWID grapher CSV URL
        base = "https://ourworldindata.org/grapher"
        url = f"{base}/{slug}.csv"

        params = {"csvType": "filtered"}
        if countries:
            params["country"] = "~".join(countries)
        if start_year and end_year:
            params["time"] = f"{start_year}..{end_year}"
        elif start_year:
            params["time"] = f"{start_year}..latest"
        elif end_year:
            params["time"] = f"earliest..{end_year}"

        # Fetch CSV
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()

        df = pd.read_csv(StringIO(resp.text))

        # Standardize columns
        if "Entity" in df.columns:
            df = df.rename(columns={"Entity": "country"})
        if "Year" in df.columns:
            df = df.rename(columns={"Year": "year"})
        if "Code" in df.columns:
            df = df.rename(columns={"Code": "country_code"})

        total_rows = len(df)
        df_preview = df.head(limit).copy()

        # Convert to JSON-friendly structure
        data_records = df_preview.to_dict(orient="records")
        cleaned = clean_nan_recursive(data_records)

        preview = {
            "columns": df_preview.columns.tolist(),
            "rows": cleaned,
            "total_rows": total_rows,
            "dataset_info": {"slug": slug, "source": "owid", "preview_limit": limit},
        }

        return jsonify({"status": "success", "preview": preview})

    except Exception as e:
        logger.error(f"Error previewing OWID remote data: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/remote/worldbank/preview")
def preview_worldbank_remote() -> Response:
    """
    Preview World Bank indicator data without saving to disk.

    Query params:
        indicator: World Bank indicator code (required)
        countries: Semicolon-separated ISO3 codes (optional)
        start_year: int (optional)
        end_year: int (optional)
        limit: max rows to return (default 200)
    """
    try:
        indicator = request.args.get("indicator", "").strip()
        if not indicator:
            return jsonify({"status": "error", "message": "Missing 'indicator' parameter"}), 400

        countries_arg = request.args.get("countries", "")
        countries = (
            ";".join([c.strip() for c in countries_arg.split(";") if c.strip()])
            if countries_arg
            else "all"
        )
        start_year = request.args.get("start_year", type=int)
        end_year = request.args.get("end_year", type=int)
        limit = request.args.get("limit", default=200, type=int)
        limit = min(limit, 1000)

        base = "https://api.worldbank.org/v2/country"
        date_param = None
        if start_year and end_year:
            date_param = f"{start_year}:{end_year}"
        elif start_year:
            date_param = f"{start_year}:latest"
        elif end_year:
            date_param = f"earliest:{end_year}"

        params = {"format": "json", "per_page": limit}
        if date_param:
            params["date"] = date_param

        url = f"{base}/{countries}/indicator/{indicator}"

        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if not isinstance(data, list) or len(data) < 2:
            return jsonify({"status": "success", "preview": {"columns": [], "rows": [], "total_rows": 0}})

        rows = []
        for record in data[1]:
            if record.get("value") is None:
                continue
            rows.append({
                "country": record.get("country", {}).get("value"),
                "country_code": record.get("countryiso3code"),
                "year": record.get("date"),
                "value": record.get("value"),
            })

        series_map = {}
        series_count = {}
        for row in rows:
            year = row.get("year")
            value = row.get("value")
            if year is None or value is None:
                continue
            try:
                year_int = int(year)
                value_float = float(value)
            except (ValueError, TypeError):
                continue
            series_map[year_int] = series_map.get(year_int, 0.0) + value_float
            series_count[year_int] = series_count.get(year_int, 0) + 1

        series = [
            {"x": year, "y": series_map[year] / series_count[year]}
            for year in sorted(series_map.keys())
            if series_count.get(year)
        ]

        preview = {
            "columns": ["country", "country_code", "year", "value"],
            "rows": clean_nan_recursive(rows),
            "total_rows": len(rows),
            "series": clean_nan_recursive(series),
            "dataset_info": {"indicator": indicator, "source": "worldbank", "preview_limit": limit},
        }

        return jsonify({"status": "success", "preview": preview})

    except Exception as e:
        logger.error(f"Error previewing World Bank remote data: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/remote/oecd/preview")
def preview_oecd_remote() -> Response:
    """
    Preview OECD dataset data without saving to disk.

    Query params:
        dataset: OECD dataset id (required)
        indicator: indicator code within dataset (optional)
        countries: Semicolon-separated ISO3 codes (optional)
        start_year: int (optional)
        end_year: int (optional)
        limit: max rows to return (default 200)
    """
    try:
        dataset = request.args.get("dataset", "").strip()
        indicator = request.args.get("indicator", "").strip()
        if not dataset:
            return jsonify({"status": "error", "message": "Missing 'dataset' parameter"}), 400

        countries_arg = request.args.get("countries", "")
        countries = [c.strip() for c in countries_arg.split(";") if c.strip()] if countries_arg else None
        start_year = request.args.get("start_year", type=int) or 2015
        end_year = request.args.get("end_year", type=int) or 2024
        limit = request.args.get("limit", default=200, type=int)
        limit = min(limit, 1000)

        config = Config()
        oecd_source = OECDSource(config.get_directory("raw"))
        df = oecd_source.fetch(
            dataset=dataset,
            indicator=indicator,
            countries=countries,
            start_year=start_year,
            end_year=end_year,
        )

        if df is None or df.empty:
            preview = {
                "columns": ["country", "year", "value"],
                "rows": [],
                "total_rows": 0,
                "series": [],
                "dataset_info": {
                    "dataset": dataset,
                    "indicator": indicator,
                    "source": "oecd",
                    "preview_limit": limit,
                },
            }
            return jsonify({"status": "success", "preview": preview})

        df_preview = df.head(limit).copy()
        rows = df_preview.to_dict(orient="records")

        series_df = df.dropna(subset=["year", "value"]).groupby("year")["value"].mean().reset_index()
        series = []
        for _, row in series_df.iterrows():
            try:
                year_int = int(row["year"])
                value_float = float(row["value"])
            except (ValueError, TypeError):
                continue
            series.append({"x": year_int, "y": value_float})

        preview = {
            "columns": ["country", "year", "value"],
            "rows": clean_nan_recursive(rows),
            "total_rows": len(df),
            "series": clean_nan_recursive(series),
            "dataset_info": {
                "dataset": dataset,
                "indicator": indicator,
                "source": "oecd",
                "preview_limit": limit,
            },
        }

        return jsonify({"status": "success", "preview": preview})

    except Exception as e:
        logger.error(f"Error previewing OECD remote data: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/chart/export-pdf")
def export_chart_pdf() -> Response:
    """
    Export chart as PDF from OWID.

    Query params:
        slug: OWID chart slug (required)
    """
    try:
        slug = request.args.get("slug", "").strip()
        if not slug:
            return jsonify(
                {"status": "error", "message": "Missing 'slug' parameter"}
            ), 400

        # Construct OWID PDF URL
        owid_pdf_url = f"https://ourworldindata.org/grapher/{slug}.pdf"

        # Fetch PDF from OWID
        resp = requests.get(owid_pdf_url, timeout=30)
        resp.raise_for_status()

        # Return PDF directly
        return Response(
            resp.content,
            mimetype="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{slug}.pdf"',
                "Cache-Control": "public, max-age=3600",
            },
        )

    except Exception as e:
        logger.error(f"Error exporting chart PDF: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/chart/export-png")
def export_chart_png() -> Response:
    """
    Export chart as PNG from OWID.

    Query params:
        slug: OWID chart slug (required)
    """
    try:
        slug = request.args.get("slug", "").strip()
        if not slug:
            return jsonify(
                {"status": "error", "message": "Missing 'slug' parameter"}
            ), 400

        owid_png_url = f"https://ourworldindata.org/grapher/{slug}.png"
        resp = requests.get(owid_png_url, timeout=30)
        resp.raise_for_status()

        return Response(
            resp.content,
            mimetype="image/png",
            headers={
                "Content-Disposition": f'inline; filename="{slug}.png"',
                "Cache-Control": "public, max-age=3600",
            },
        )

    except Exception as e:
        logger.error(f"Error exporting chart PNG: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/datasets/refresh", methods=["POST"])
def refresh_datasets() -> Response:
    """Re-index datasets to refresh the catalog and regenerate metadata."""
    try:
        config = Config()
        catalog = DatasetCatalog(config)

        # Get force parameter
        force = request.get_json().get("force", False) if request.get_json() else False

        # Step 1: Reindex all datasets
        stats = catalog.index_all(force=force)
        
        # Step 2: Regenerate metadata for all datasets
        try:
            metadata_gen = MetadataGenerator(config)
            cleaner = DataCleaner(config)
            
            # Get all datasets from catalog
            all_datasets = catalog.search(query="", limit=1000)
            metadata_generated = 0
            metadata_errors = 0
            
            for ds in all_datasets:
                try:
                    file_path = Path(ds['file_path'])
                    if not file_path.exists():
                        continue
                        
                    # Load dataset
                    df = pd.read_csv(file_path)
                    
                    # Get summary
                    data_summary = cleaner.get_data_summary(df)
                    
                    # Generate metadata
                    topic = ds.get('topic', 'general')
                    source = ds.get('source', 'unknown')
                    
                    metadata_content = metadata_gen.generate_metadata(
                        topic=topic,
                        data_summary=data_summary,
                        source=source,
                        transformations=[],
                        original_source_url=f"https://{source}.org",
                        dataset_info={
                            "identifier": ds.get("indicator_id") or ds.get("file_name"),
                            "indicator_id": ds.get("indicator_id"),
                            "indicator_name": ds.get("indicator_name"),
                            "file_name": ds.get("file_name"),
                        },
                        force_regenerate=force
                    )
                    
                    # Save metadata using dataset filename stem
                    file_path = Path(ds['file_path'])
                    metadata_gen.save_metadata_for_dataset(file_path, metadata_content)
                    metadata_generated += 1
                    
                except Exception as e:
                    logger.error(f"Error generating metadata for dataset {ds.get('id')}: {e}")
                    metadata_errors += 1
            
            stats['metadata_generated'] = metadata_generated
            stats['metadata_errors'] = metadata_errors
            
        except Exception as e:
            logger.warning(f"Metadata generation failed: {e}")
            stats['metadata_warning'] = str(e)

        return jsonify(
            {"status": "success", "message": "Catalog refreshed and metadata regenerated", "stats": stats}
        )

    except Exception as e:
        logger.error(f"Error refreshing datasets: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/datasets/statistics")
def get_catalog_statistics() -> Response:
    """Get catalog-wide statistics."""
    try:
        config = Config()
        catalog = DatasetCatalog(config)

        stats = catalog.get_statistics()
        stats = clean_nan_recursive(stats)

        return jsonify({"status": "success", "statistics": stats})

    except Exception as e:
        logger.error(f"Error getting catalog statistics: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/datasets/backup", methods=["GET"])
def download_backup() -> Response:
    """Download a zip backup of raw, clean, and metadata directories."""
    try:
        config = Config()
        raw_dir = config.get_directory("raw")
        clean_dir = config.get_directory("clean")
        metadata_dir = config.get_directory("metadata")

        missing_dirs = [
            str(p)
            for p in [raw_dir, clean_dir, metadata_dir]
            if not p.exists()
        ]
        if len(missing_dirs) == 3:
            return jsonify({
                "status": "error",
                "message": "No data directories found to back up."
            }), 404

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        temp_path = Path(temp_file.name)
        temp_file.close()

        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            if raw_dir.exists():
                _add_directory_to_zip(zip_file, raw_dir, raw_dir.name)
            if clean_dir.exists():
                _add_directory_to_zip(zip_file, clean_dir, clean_dir.name)
            if metadata_dir.exists():
                _add_directory_to_zip(zip_file, metadata_dir, metadata_dir.name)

        @after_this_request
        def cleanup(response: Response) -> Response:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass
            return response

        return send_file(
            temp_path,
            as_attachment=True,
            download_name="mises_data_backup.zip",
            mimetype="application/zip",
        )

    except Exception as e:
        logger.error(f"Error creating backup zip: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/datasets/<int:dataset_id>/delete", methods=["DELETE", "POST"])
def delete_dataset(dataset_id: int) -> Response:
    """Delete a dataset from catalog and filesystem."""
    try:
        config = Config()
        catalog = DatasetCatalog(config)

        # Get dataset info first
        dataset = catalog.get_dataset(dataset_id)
        if not dataset:
            return jsonify({"status": "error", "message": "Dataset not found"}), 404

        # Delete the physical file
        file_path = Path(dataset["file_path"])
        if file_path.exists():
            file_path.unlink()

        # Delete from catalog
        success = catalog.delete_dataset(dataset_id)

        if success:
            return jsonify(
                {
                    "status": "success",
                    "message": f"Dataset '{dataset['indicator_name']}' deleted successfully",
                }
            )
        else:
            return jsonify(
                {"status": "error", "message": "Failed to delete dataset"}
            ), 500

    except Exception as e:
        logger.error(f"Error deleting dataset {dataset_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/datasets/<int:dataset_id>/redownload", methods=["POST"])
def redownload_dataset(dataset_id: int) -> Response:
    """Re-download a dataset to refresh incomplete or corrupted data."""
    try:
        config = Config()
        catalog = DatasetCatalog(config)

        # Get dataset info
        dataset = catalog.get_dataset(dataset_id)
        if not dataset:
            return jsonify({"status": "error", "message": "Dataset not found"}), 404

        # First, delete the old file and catalog entry
        file_path = Path(dataset["file_path"])
        if file_path.exists():
            file_path.unlink()
        catalog.delete_dataset(dataset_id)

        # NOTE: We cannot fully reconstruct the original download without the indicator ID or slug
        return jsonify({
            "status": "error",
            "message": "Please re-download this dataset from the Search page. Auto re-download not yet supported.",
        }), 501

    except Exception as e:
        logger.error(f"Error re-downloading dataset {dataset_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route('/datasets/versions')
def get_dataset_versions() -> Response:
    """
    Return all versions for a given identifier and optional source.

    Query params:
        identifier: required (indicator_id or indicator_name)
        source: optional source filter
    """
    try:
        identifier = request.args.get('identifier', '')
        source = request.args.get('source', '')
        if not identifier:
            return jsonify({"status": "error", "message": "Missing 'identifier' parameter"}), 400

        config = Config()
        catalog = DatasetCatalog(config)
        versions = catalog.get_versions_for_identifier(identifier, source=source or None)

        return jsonify({"status": "success", "total": len(versions), "versions": versions})
    except Exception as e:
        logger.error(f"Error getting dataset versions: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/datasets/<int:dataset_id>/fields")
def get_dataset_fields(dataset_id: int) -> Response:
    """
    Get field/column information for a dataset with inferred types.
    
    Returns fields in Data Formulator format for use in Concept Shelf.
    """
    try:
        config = Config()
        catalog = DatasetCatalog(config)
        
        # Get dataset info
        dataset = catalog.get_dataset(dataset_id)
        if not dataset:
            return jsonify({"status": "error", "message": "Dataset not found"}), 404
        
        # Load preview data to infer types
        df = catalog.get_preview_data(dataset_id, limit=100)
        if df is None:
            return jsonify({"status": "error", "message": "Could not load dataset"}), 500
        
        # Build fields list with type inference
        fields = []
        for col_name in df.columns:
            col = df[col_name]
            
            # Infer type from pandas dtype
            dtype_str = str(col.dtype)
            if 'int' in dtype_str:
                field_type = 'integer'
            elif 'float' in dtype_str:
                field_type = 'number'
            elif 'bool' in dtype_str:
                field_type = 'boolean'
            elif 'datetime' in dtype_str:
                field_type = 'date'
            elif 'object' in dtype_str:
                # Check if it looks like a date
                sample = col.dropna().head(10).tolist()
                if sample and all(isinstance(s, str) for s in sample):
                    # Check if values look numeric
                    try:
                        [float(s) for s in sample if s]
                        field_type = 'number'
                    except (ValueError, TypeError):
                        # Check if looks like date (contains - or /)
                        if any('-' in str(s) or '/' in str(s) for s in sample):
                            field_type = 'date'
                        else:
                            field_type = 'string'
                else:
                    field_type = 'string'
            else:
                field_type = 'string'
            
            # Get unique value count for categorical detection
            unique_count = col.nunique()
            total_count = len(col)
            
            # Determine semantic type
            semantic_type = None
            col_lower = col_name.lower()
            if 'country' in col_lower or 'entity' in col_lower:
                semantic_type = 'geographic'
            elif 'year' in col_lower or 'date' in col_lower or 'time' in col_lower:
                semantic_type = 'temporal'
            elif unique_count < 20 and unique_count < total_count * 0.1:
                semantic_type = 'categorical'
            elif field_type in ['integer', 'number']:
                semantic_type = 'quantitative'
            
            fields.append({
                "id": f"original--{dataset_id}--{col_name}",
                "name": col_name,
                "type": field_type,
                "semanticType": semantic_type,
                "source": "original",
                "tableRef": str(dataset_id),
                "uniqueCount": int(unique_count),
                "nullCount": int(col.isnull().sum()),
                "sampleValues": [str(v) for v in col.dropna().head(5).tolist()]
            })
        
        return jsonify({
            "status": "success",
            "datasetId": dataset_id,
            "datasetName": dataset.get("indicator_name", dataset.get("file_name", "Unknown")),
            "fields": fields,
            "rowCount": dataset.get("row_count", len(df)),
            "source": dataset.get("source", "unknown")
        })
        
    except Exception as e:
        logger.error(f"Error getting dataset fields {dataset_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route('/llm/models')
def get_llm_models() -> Response:
    """
    Return available models for GitHub Copilot SDK.

    Returns models available via GitHub Copilot subscription.
    """
    try:
        config = Config()
        llm_cfg = config.get_llm_config()
        
        # Default models available with Copilot subscription
        available_models = [
            "gpt-4.1",           # Latest GPT-4 Turbo
            "claude-3.5-sonnet", # Anthropic Claude 3.5 Sonnet
            "claude-3-opus",     # Anthropic Claude 3 Opus
            "gpt-4",             # GPT-4
        ]
        
        return jsonify({
            "status": "success",
            "provider": "github_copilot_sdk",
            "source": "GitHub Copilot subscription",
            "models": available_models,
            "note": "Actual availability depends on your Copilot subscription tier"
        }), 200

    except Exception as e:
        logger.error(f"Error getting LLM models: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


SQL_SAMPLE_LIMIT = int(os.getenv("SMOOTHCSV_SQL_SAMPLE_LIMIT", "5000"))
SQL_PREVIEW_LIMIT = int(os.getenv("SMOOTHCSV_SQL_PREVIEW_LIMIT", "200"))


def _get_smoothcsv_db_path(config: Config) -> Path:
    return config.data_root / "smoothcsv_cache.db"


def _init_smoothcsv_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dataset_mapping (
            dataset_id INTEGER PRIMARY KEY,
            table_name TEXT NOT NULL,
            file_hash TEXT,
            sample_limit INTEGER,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def _smoothcsv_table_name(dataset_id: int) -> str:
    return f"table{dataset_id:06d}"


def _ensure_smoothcsv_table(
    conn: sqlite3.Connection,
    dataset: dict,
    sample_limit: int,
) -> str:
    _init_smoothcsv_db(conn)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT table_name, file_hash, sample_limit FROM dataset_mapping WHERE dataset_id = ?",
        (dataset["id"],),
    )
    row = cursor.fetchone()
    table_name = row["table_name"] if row else _smoothcsv_table_name(dataset["id"])
    current_hash = dataset.get("file_hash")
    needs_reload = (
        row is None
        or row["file_hash"] != current_hash
        or row["sample_limit"] != sample_limit
    )

    if needs_reload:
        file_path = Path(dataset["file_path"])
        if not file_path.exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")
        df = pd.read_csv(file_path, nrows=sample_limit)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        cursor.execute(
            """
            INSERT INTO dataset_mapping (dataset_id, table_name, file_hash, sample_limit)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(dataset_id) DO UPDATE SET
                table_name = excluded.table_name,
                file_hash = excluded.file_hash,
                sample_limit = excluded.sample_limit,
                updated_at = CURRENT_TIMESTAMP
            """,
            (dataset["id"], table_name, current_hash, sample_limit),
        )
        conn.commit()

    return table_name


def _prepare_smoothcsv_sql(sql: str, limit: int) -> str:
    sql = sql.strip().rstrip(";")
    if not sql:
        raise ValueError("Missing SQL query.")
    if not sql.lower().startswith("select"):
        raise ValueError("Only SELECT queries are supported.")
    if not re.search(r"\blimit\b", sql, flags=re.IGNORECASE):
        sql = f"{sql} LIMIT {limit}"
    return sql


@api_bp.route("/edit/sql/query", methods=["POST"])
def edit_sql_query() -> Response:
    """Run a SQL query against the selected dataset (sampled)."""
    try:
        payload = request.get_json(silent=True) or {}
        dataset_id = payload.get("dataset_id")
        sql = payload.get("sql", "")
        limit = int(payload.get("limit", SQL_PREVIEW_LIMIT))

        if not dataset_id:
            return jsonify({"status": "error", "message": "Missing dataset_id"}), 400

        config = Config()
        catalog = DatasetCatalog(config)
        dataset = catalog.get_dataset(int(dataset_id))
        if not dataset:
            return jsonify({"status": "error", "message": "Dataset not found"}), 404

        db_path = _get_smoothcsv_db_path(config)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            table_name = _ensure_smoothcsv_table(conn, dataset, SQL_SAMPLE_LIMIT)
            cursor = conn.cursor()
            cursor.execute("DROP VIEW IF EXISTS dataset")
            cursor.execute(f'CREATE TEMP VIEW dataset AS SELECT * FROM "{table_name}"')

            query_sql = _prepare_smoothcsv_sql(sql, limit)
            cursor.execute(query_sql)
            rows = cursor.fetchall()
            columns = [col[0] for col in cursor.description] if cursor.description else []
            values = [list(row) for row in rows]

            return jsonify(
                {
                    "status": "success",
                    "columns": columns,
                    "rows": values,
                    "table_name": table_name,
                    "sample_limit": SQL_SAMPLE_LIMIT,
                    "query": query_sql,
                }
            )
        finally:
            conn.close()

    except (ValueError, FileNotFoundError) as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception as exc:
        logger.error("SQL query error: %s", exc, exc_info=True)
        return jsonify({"status": "error", "message": str(exc)}), 500


@api_bp.route("/datasets/<int:dataset_id>/fork", methods=["POST"])
def fork_dataset(dataset_id: int) -> Response:
    """Create a forked dataset marked as edited."""
    try:
        payload = request.get_json(silent=True) or {}
        fork_name = (payload.get("name") or "").strip()

        config = Config()
        catalog = DatasetCatalog(config)
        dataset = catalog.get_dataset(dataset_id)
        if not dataset:
            return jsonify({"status": "error", "message": "Dataset not found"}), 404

        source_path = Path(dataset["file_path"])
        if not source_path.exists():
            return jsonify({"status": "error", "message": "Dataset file not found"}), 404

        safe_base = fork_name or f"{source_path.stem}_edited"
        safe_base = "".join(c if c.isalnum() or c in "-_" else "_" for c in safe_base).strip("_")
        if not safe_base:
            safe_base = f"dataset_{dataset_id}_edited"

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        dest_name = f"{safe_base}_{timestamp}.csv"
        dest_path = source_path.parent / dest_name

        shutil.copyfile(source_path, dest_path)
        new_id = catalog.index_dataset(dest_path, force=True)
        if not new_id:
            return jsonify({"status": "error", "message": "Failed to index forked dataset"}), 500

        conn = sqlite3.connect(catalog.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE datasets SET is_edited = 1 WHERE id = ?", (new_id,))
            conn.commit()
        finally:
            conn.close()

        return jsonify(
            {
                "status": "success",
                "dataset": {
                    "id": new_id,
                    "file_name": dest_name,
                    "file_path": str(dest_path),
                },
            }
        )

    except Exception as exc:
        logger.error("Fork dataset error: %s", exc, exc_info=True)
        return jsonify({"status": "error", "message": str(exc)}), 500

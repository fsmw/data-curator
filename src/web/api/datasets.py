"""
Dataset API endpoints.

Handles dataset CRUD operations, preview, statistics, and management.
"""

from flask import request, jsonify, Response, send_file, after_this_request
from flask_login import login_required, current_user
import json
import math
import sqlite3
import pandas as pd
from pathlib import Path
from io import StringIO
import os
import tempfile
import shutil
import zipfile
from datetime import datetime

from src.config import Config
from src.dataset_catalog import DatasetCatalog
from src.metadata import MetadataGenerator
from src.cleaning import DataCleaner
from src.logger import get_logger
from src.model_governance import ALLOWED_COPILOT_MODELS
from src.utils.storage import sanitize_username
from src.utils.serialization import clean_nan_recursive
from src.ingestion import OECDSource, OWIDSource
from src.ai_packager import AIPackager
from src.smoothcsv_cache import (
    SQL_PREVIEW_LIMIT,
    SQL_SAMPLE_LIMIT,
    ensure_smoothcsv_table,
    get_smoothcsv_db_path,
    prepare_smoothcsv_sql,
)
import requests

from . import api_bp

logger = get_logger(__name__)

JSON_PARSE_ERRORS = (json.JSONDecodeError, TypeError)
DATASET_API_ERRORS = (
    AttributeError,
    KeyError,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
    json.JSONDecodeError,
    sqlite3.Error,
    pd.errors.EmptyDataError,
    pd.errors.ParserError,
    requests.RequestException,
)


def _format_dataset(ds: dict) -> dict:
    if isinstance(ds, dict):
        dataset = dict(ds)
    elif hasattr(ds, "__dict__"):
        dataset = {
            key: value
            for key, value in vars(ds).items()
            if not key.startswith("_sa_")
        }
    else:
        dataset = {}

    dataset.pop("_sa_instance_state", None)
    if dataset.get("countries_json"):
        try:
            dataset["countries"] = json.loads(dataset["countries_json"])
        except JSON_PARSE_ERRORS:
            dataset["countries"] = []
    else:
        dataset["countries"] = []

    if dataset.get("columns_json"):
        try:
            dataset["columns"] = json.loads(dataset["columns_json"])
        except JSON_PARSE_ERRORS:
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


def _add_directory_to_zip(
    zip_file: zipfile.ZipFile,
    directory: Path,
    arc_prefix: str,
    csv_display_names: dict[str, str] | None = None,
) -> None:
    used_arc_names: set[str] = set()
    for root, _, files in os.walk(directory):
        for filename in files:
            file_path = Path(root) / filename
            relative_path = file_path.relative_to(directory)
            if csv_display_names and file_path.suffix.lower() == ".csv":
                display_name = csv_display_names.get(str(file_path))
                if display_name:
                    relative_path = relative_path.with_name(Path(display_name).name)

            arcname = Path(arc_prefix) / relative_path
            arcname_str = arcname.as_posix()
            if arcname_str in used_arc_names:
                base = arcname
                counter = 2
                while arcname_str in used_arc_names:
                    arcname = base.with_name(f"{base.stem}_{counter}{base.suffix}")
                    arcname_str = arcname.as_posix()
                    counter += 1
            used_arc_names.add(arcname_str)
            zip_file.write(file_path, arcname.as_posix())


@api_bp.route("/datasets")
@login_required
def list_datasets() -> Response:
    """
    List and search datasets in the catalog.
    Returns only datasets visible to the current user.

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

        filters = {}
        if source:
            filters["source"] = source
        if topic:
            filters["topic"] = topic

        owner_segment = sanitize_username(current_user.username)
        filtered_results = catalog.search(
            query=query,
            filters=filters if filters else None,
            limit=limit,
            owner_username=owner_segment,
        )

        latest_only = request.args.get("latest", "false").lower() == "true"
        if latest_only:
            from collections import defaultdict
            by_indicator = defaultdict(list)
            for ds in filtered_results:
                gid = ds.get("indicator_id") or ds.get("indicator_name")
                by_indicator[gid].append(ds)

            filtered_results = []
            for datasets in by_indicator.values():
                datasets.sort(
                    key=lambda x: (x.get("modified_at") or x.get("indexed_at") or ""),
                    reverse=True,
                )
                filtered_results.append(datasets[0])

        datasets = [_format_dataset(ds) for ds in filtered_results]

        return jsonify(
            {"status": "success", "total": len(datasets), "datasets": datasets}
        )

    except DATASET_API_ERRORS as e:
        logger.error(f"Error listing datasets: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/datasets/<int:dataset_id>")
@login_required
def get_dataset_detail(dataset_id: int) -> Response:
    """Fetch a single dataset record."""
    try:
        config = Config()
        catalog = DatasetCatalog(config)
        dataset = catalog.get_dataset(dataset_id)
        if not dataset:
            return jsonify({"status": "error", "message": "Dataset not found"}), 404

        if not catalog.can_access(dataset_id, current_user.username, "read"):
            return jsonify({"status": "error", "message": "Dataset not found"}), 404

        return jsonify({"status": "success", "dataset": _format_dataset(dataset)})

    except DATASET_API_ERRORS as e:
        logger.error(f"Error retrieving dataset detail: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/datasets/<int:dataset_id>/download", methods=["GET"])
@login_required
def download_dataset(dataset_id: int) -> Response:
    """Download a zip bundle for a specific dataset (CSV + notes + visuals)."""
    try:
        config = Config()
        catalog = DatasetCatalog(config)
        dataset = catalog.get_dataset(dataset_id)
        if not dataset:
            return jsonify({"status": "error", "message": "Dataset not found"}), 404

        if not catalog.can_access(dataset_id, current_user.username, "read"):
            return jsonify({"status": "error", "message": "Dataset not found"}), 404

        file_path = Path(dataset["file_path"])
        if not file_path.exists():
            return jsonify({"status": "error", "message": "Dataset file missing"}), 404

        metadata_gen = MetadataGenerator(config)
        metadata_path = metadata_gen.get_metadata_path_for_dataset(file_path)

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        temp_path = Path(temp_file.name)
        temp_file.close()

        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            csv_name = (
                dataset.get("display_file_name")
                or dataset.get("file_name")
                or file_path.name
            )
            zip_file.write(file_path, Path(csv_name).name)

            if metadata_path.exists():
                zip_file.write(metadata_path, f"metadata/{metadata_path.name}")

            dataset_dir = file_path.parent
            for child in dataset_dir.iterdir():
                if child.name in {file_path.name, metadata_path.name}:
                    continue
                if child.is_file():
                    zip_file.write(child, f"package/{child.name}")

        @after_this_request
        def cleanup(response: Response) -> Response:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError as exc:
                logger.warning("Could not remove temporary zip %s: %s", temp_path, exc)
            return response

        download_name = f"{dataset.get('indicator_name') or dataset.get('file_name', 'dataset')}.zip"

        return send_file(
            temp_path,
            as_attachment=True,
            download_name=download_name,
            mimetype="application/zip",
        )

    except DATASET_API_ERRORS as e:
        logger.error(f"Error downloading dataset {dataset_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/datasets/refresh-selected", methods=["POST"])
@login_required
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
            if not catalog.can_access(dataset_id, current_user.username, "write"):
                errors.append({"id": dataset_id, "error": "Access denied"})
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
                except DATASET_API_ERRORS as e:
                    errors.append({"id": dataset_id, "error": f"OWID notes update failed: {e}"})

        return jsonify(
            {
                "status": "success",
                "updated": updated,
                "notes_updated": notes_updated,
                "errors": errors,
            }
        )

    except DATASET_API_ERRORS as e:
        logger.error(f"Error refreshing selected datasets: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route("/datasets/<int:dataset_id>/preview")
@login_required
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
        if not catalog.can_access(dataset_id, current_user.username, "read"):
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

    except DATASET_API_ERRORS as e:
        logger.error(f"Error previewing dataset {dataset_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/datasets/<int:dataset_id>/notes")
@login_required
def get_dataset_notes(dataset_id: int) -> Response:
    """Get AI-generated notes for a dataset if available, generate on demand if missing."""
    try:
        config = Config()
        catalog = DatasetCatalog(config)
        dataset = catalog.get_dataset(dataset_id)

        if not dataset:
            return jsonify({"status": "error", "message": "Dataset not found"}), 404
        if not catalog.can_access(dataset_id, current_user.username, "read"):
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
                except DATASET_API_ERRORS as e:
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

    except DATASET_API_ERRORS as e:
        logger.error(f"Error fetching notes for dataset {dataset_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/remote/owid/preview")
@login_required
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

    except DATASET_API_ERRORS as e:
        logger.error(f"Error previewing OWID remote data: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/remote/worldbank/preview")
@login_required
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

    except DATASET_API_ERRORS as e:
        logger.error(f"Error previewing World Bank remote data: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/remote/oecd/preview")
@login_required
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

    except DATASET_API_ERRORS as e:
        logger.error(f"Error previewing OECD remote data: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/chart/export-pdf")
@login_required
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

    except DATASET_API_ERRORS as e:
        logger.error(f"Error exporting chart PDF: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/chart/export-png")
@login_required
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

    except DATASET_API_ERRORS as e:
        logger.error(f"Error exporting chart PNG: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/datasets/refresh", methods=["POST"])
@login_required
def refresh_datasets() -> Response:
    """Re-index current user's datasets and regenerate metadata."""
    try:
        config = Config()
        catalog = DatasetCatalog(config)
        owner_segment = sanitize_username(current_user.username)

        payload = request.get_json(silent=True) or {}
        force = bool(payload.get("force", False))
        user_datasets = catalog.search(
            query="",
            filters=None,
            limit=100000,
            owner_username=owner_segment,
        )
        stats = {"indexed": 0, "skipped": 0, "errors": 0}

        for ds in user_datasets:
            file_path = Path(ds["file_path"])
            if not file_path.exists():
                stats["errors"] += 1
                continue
            previous_hash = ds.get("file_hash")
            current_hash = catalog._compute_file_hash(file_path)
            result = catalog.index_dataset(
                file_path,
                display_file_name=ds.get("display_file_name"),
                force=force,
            )
            if not result:
                stats["errors"] += 1
            elif not force and previous_hash == current_hash:
                stats["skipped"] += 1
            else:
                stats["indexed"] += 1

        # Regenerate metadata for current user's datasets
        try:
            metadata_gen = MetadataGenerator(config)
            cleaner = DataCleaner(config)
            metadata_generated = 0
            metadata_errors = 0

            refreshed_datasets = catalog.search(
                query="",
                filters=None,
                limit=100000,
                owner_username=owner_segment,
            )
            for ds in refreshed_datasets:
                try:
                    file_path = Path(ds['file_path'])
                    if not file_path.exists():
                        continue

                    df = pd.read_csv(file_path)
                    data_summary = cleaner.get_data_summary(df)
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
                    
                    metadata_gen.save_metadata_for_dataset(file_path, metadata_content)
                    metadata_generated += 1
                except DATASET_API_ERRORS as e:
                    logger.error(f"Error generating metadata for dataset {ds.get('id')}: {e}")
                    metadata_errors += 1

            stats['metadata_generated'] = metadata_generated
            stats['metadata_errors'] = metadata_errors

        except DATASET_API_ERRORS as e:
            logger.warning(f"Metadata generation failed: {e}")
            stats['metadata_warning'] = str(e)

        return jsonify(
            {"status": "success", "message": "Catalog refreshed and metadata regenerated", "stats": stats}
        )

    except DATASET_API_ERRORS as e:
        logger.error(f"Error refreshing datasets: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/datasets/statistics")
@login_required
def get_catalog_statistics() -> Response:
    """Get catalog statistics scoped to the current user."""
    try:
        if not current_user.is_authenticated:
            empty_stats = {
                "total_datasets": 0,
                "by_source": {},
                "by_topic": {},
                "total_size_mb": 0,
                "avg_completeness": 0,
            }
            return jsonify({"status": "success", "statistics": empty_stats})

        config = Config()
        catalog = DatasetCatalog(config)
        owner_segment = sanitize_username(current_user.username)
        stats = catalog.get_statistics(owner_username=owner_segment)
        stats = clean_nan_recursive(stats)

        return jsonify({"status": "success", "statistics": stats})

    except DATASET_API_ERRORS as e:
        logger.error(f"Error getting catalog statistics: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/datasets/backup", methods=["GET"])
@login_required
def download_backup() -> Response:
    """Download a zip archive containing the current user's cleaned datasets."""
    try:
        config = Config()
        catalog = DatasetCatalog(config)
        clean_dir = config.get_directory("clean")
        owner_segment = sanitize_username(current_user.username)
        user_dir = clean_dir / owner_segment

        if not user_dir.exists():
            return jsonify(
                {
                    "status": "error",
                    "message": "No datasets found for the current user.",
                }
            ), 404

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        temp_path = Path(temp_file.name)
        temp_file.close()

        datasets = catalog.search(
            query="",
            filters=None,
            limit=100000,
            owner_username=owner_segment,
        )
        csv_display_names = {
            record["file_path"]: (
                record.get("display_file_name")
                or record.get("file_name")
                or Path(record["file_path"]).name
            )
            for record in datasets
            if record.get("file_path")
        }

        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            _add_directory_to_zip(
                zip_file,
                user_dir,
                owner_segment,
                csv_display_names=csv_display_names,
            )

        @after_this_request
        def cleanup(response: Response) -> Response:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError as exc:
                logger.warning("Could not remove temporary backup zip %s: %s", temp_path, exc)
            return response

        return send_file(
            temp_path,
            as_attachment=True,
            download_name=f"{owner_segment}_datasets.zip",
            mimetype="application/zip",
        )

    except DATASET_API_ERRORS as e:
        logger.error(f"Error creating backup zip: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/datasets/<int:dataset_id>/delete", methods=["DELETE", "POST"])
@login_required
def delete_dataset(dataset_id: int) -> Response:
    """Delete a dataset from catalog and filesystem."""
    try:
        config = Config()
        catalog = DatasetCatalog(config)

        # Get dataset info first
        dataset = catalog.get_dataset(dataset_id)
        if not dataset:
            return jsonify({"status": "error", "message": "Dataset not found"}), 404

        if not catalog.can_access(dataset_id, current_user.username, "admin"):
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

    except DATASET_API_ERRORS as e:
        logger.error(f"Error deleting dataset {dataset_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/datasets/clear-my-data", methods=["POST"])
@login_required
def clear_my_data() -> Response:
    """Delete all datasets and files for the current user."""
    try:
        config = Config()
        catalog = DatasetCatalog(config)
        owner_segment = sanitize_username(current_user.username)

        with sqlite3.connect(catalog.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, file_path FROM datasets WHERE owner_username = ?",
                (owner_segment,),
            )
            rows = cursor.fetchall()
            dataset_ids = [row[0] for row in rows]
            file_paths = [row[1] for row in rows]

            for file_path in file_paths:
                path = Path(file_path)
                if path.exists():
                    path.unlink()

            if dataset_ids:
                placeholders = ",".join(["?"] * len(dataset_ids))
                cursor.execute(
                    f"DELETE FROM dataset_columns WHERE dataset_id IN ({placeholders})",
                    dataset_ids,
                )

            cursor.execute(
                "DELETE FROM datasets WHERE owner_username = ?",
                (owner_segment,),
            )

        clean_dir = config.get_directory("clean") / owner_segment
        if clean_dir.exists():
            shutil.rmtree(clean_dir)

        return jsonify(
            {
                "status": "success",
                "deleted_count": len(dataset_ids),
                "message": "All your local data has been deleted permanently.",
            }
        )
    except DATASET_API_ERRORS as e:
        logger.error(f"Error clearing data for {current_user.username}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/datasets/<int:dataset_id>/redownload", methods=["POST"])
@login_required
def redownload_dataset(dataset_id: int) -> Response:
    """Re-download a dataset to refresh incomplete or corrupted data."""
    try:
        config = Config()
        catalog = DatasetCatalog(config)

        # Get dataset info
        dataset = catalog.get_dataset(dataset_id)
        if not dataset:
            return jsonify({"status": "error", "message": "Dataset not found"}), 404
        if not catalog.can_access(dataset_id, current_user.username, "write"):
            return jsonify({"status": "error", "message": "Dataset not found"}), 404

        # NOTE: Auto re-download is not supported yet; keep current dataset intact.
        return jsonify({
            "status": "error",
            "message": "Please re-download this dataset from the Search page. Auto re-download not yet supported.",
        }), 501

    except DATASET_API_ERRORS as e:
        logger.error(f"Error re-downloading dataset {dataset_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route('/datasets/versions')
@login_required
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
        versions = [
            version for version in versions
            if catalog.can_access(version.get("id", 0), current_user.username, "read")
        ]

        return jsonify({"status": "success", "total": len(versions), "versions": versions})
    except DATASET_API_ERRORS as e:
        logger.error(f"Error getting dataset versions: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/datasets/<int:dataset_id>/fields")
@login_required
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
        if not catalog.can_access(dataset_id, current_user.username, "read"):
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
        
    except DATASET_API_ERRORS as e:
        logger.error(f"Error getting dataset fields {dataset_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route('/llm/models')
@login_required
def get_llm_models() -> Response:
    """
    Return available models for GitHub Copilot SDK.

    Returns models available via GitHub Copilot subscription.
    """
    try:
        config = Config()
        llm_cfg = config.get_llm_config()
        
        # Enforced allowlist aligned with Copilot Chat UI governance
        available_models = list(ALLOWED_COPILOT_MODELS)
        
        return jsonify({
            "status": "success",
            "provider": "github_copilot_sdk",
            "source": "GitHub Copilot subscription",
            "models": available_models,
            "note": "Actual availability depends on your Copilot subscription tier"
        }), 200

    except DATASET_API_ERRORS as e:
        logger.error(f"Error getting LLM models: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/edit/sql/query", methods=["POST"])
@login_required
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
        if not catalog.can_access(int(dataset_id), current_user.username, "read"):
            return jsonify({"status": "error", "message": "Dataset not found"}), 404

        db_path = get_smoothcsv_db_path(config.data_root)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            table_name = ensure_smoothcsv_table(conn, dataset, SQL_SAMPLE_LIMIT)
            cursor = conn.cursor()
            cursor.execute("DROP VIEW IF EXISTS dataset")
            cursor.execute(f'CREATE TEMP VIEW dataset AS SELECT * FROM "{table_name}"')

            query_sql = prepare_smoothcsv_sql(sql, limit)
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
    except DATASET_API_ERRORS as exc:
        logger.error("SQL query error: %s", exc, exc_info=True)
        return jsonify({"status": "error", "message": str(exc)}), 500


@api_bp.route("/datasets/<int:dataset_id>/fork", methods=["POST"])
@login_required
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
        if not catalog.can_access(dataset_id, current_user.username, "write"):
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
        new_id = catalog.index_dataset(
            dest_path,
            owner_username=current_user.username,
            display_file_name=dest_name,
            force=True,
        )
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

    except DATASET_API_ERRORS as exc:
        logger.error("Fork dataset error: %s", exc, exc_info=True)
        return jsonify({"status": "error", "message": str(exc)}), 500

"""
Dataset API endpoints.

Handles dataset CRUD operations, preview, statistics, and management.
"""

from flask import request, jsonify, Response
import json
import math
import pandas as pd
from pathlib import Path
from io import StringIO

from config import Config
from dataset_catalog import DatasetCatalog
from metadata import MetadataGenerator
from cleaning import DataCleaner
from logger import get_logger
from utils.serialization import clean_nan_recursive
import requests

from . import api_bp

logger = get_logger(__name__)


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
        datasets = []
        for ds in results:
            # Clean up the dataset object
            dataset = dict(ds)

            # Parse JSON fields
            if dataset.get("countries_json"):
                try:
                    dataset["countries"] = json.loads(dataset["countries_json"])
                except:
                    dataset["countries"] = []
            else:
                dataset["countries"] = []

            if dataset.get("columns_json"):
                try:
                    dataset["columns"] = json.loads(dataset["columns_json"])
                except:
                    dataset["columns"] = []
            else:
                dataset["columns"] = []

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
                    or (isinstance(dataset[key], float) and math.isnan(dataset[key]))
                ):
                    dataset[key] = 0

            datasets.append(dataset)

        return jsonify(
            {"status": "success", "total": len(datasets), "datasets": datasets}
        )

    except Exception as e:
        logger.error(f"Error listing datasets: {e}", exc_info=True)
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
                        force_regenerate=force
                    )
                    
                    # Save metadata
                    metadata_gen.save_metadata(topic, metadata_content)
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

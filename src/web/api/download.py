"""
Download API endpoints.

Handles data ingestion and download progress tracking.
"""

from flask import request, jsonify, Response, stream_with_context
from typing import Dict
import time
import json

from config import Config
from searcher import IndicatorSearcher
from ingestion import DataIngestionManager
from cleaning import DataCleaner
from metadata import MetadataGenerator
from ai_packager import AIPackager
from src.logger import get_logger

from . import api_bp

logger = get_logger(__name__)

# In-memory progress tracking for SSE
_download_progress: Dict[str, Dict] = {}


@api_bp.route("/download/start", methods=["POST"])
def start_download() -> Response:
    """Start automatic download for selected indicator.

    Supports two modes:
    1. Local indicators from indicators.yaml (requires 'id' to match entry in YAML)
    2. Remote API results (requires 'remote': true and source-specific parameters like 'slug')
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400

        indicator_id = data.get("id", "")
        source = data.get("source", "").lower()
        indicator_name = data.get("indicator", "")
        is_remote = data.get("remote", False)

        if not indicator_id or not source or not indicator_name:
            return jsonify(
                {
                    "status": "error",
                    "message": "Missing required fields (id, source, indicator)",
                }
            ), 400

        config = Config()
        indicator_config = None

        if is_remote:
            # For remote API results, construct config from request data
            indicator_config = {
                "id": indicator_id,
                "source": source,
                "name": indicator_name,
                "slug": data.get("slug"),
                "url": data.get("url"),
                "description": data.get("description", ""),
            }
        else:
            # For local indicators, look up in indicators.yaml
            searcher = IndicatorSearcher(config)
            indicators = config.get_indicators()

            for ind in indicators:
                if ind.get("id") == indicator_id:
                    indicator_config = ind
                    break

            if not indicator_config:
                return jsonify(
                    {
                        "status": "error",
                        "message": f"Indicator {indicator_id} not found in indicators.yaml",
                    }
                ), 404

        # Download data using DataIngestionManager
        manager = DataIngestionManager(config)
        fetch_params = {}

        # Source-specific parameter mapping
        if source == "owid":
            if "slug" not in indicator_config:
                return jsonify({"status": "error", "message": "OWID indicator missing 'slug' field"}), 400
            fetch_params["slug"] = indicator_config["slug"]
        elif source == "ilostat":
            fetch_params["indicator"] = indicator_config.get("indicator_code") or indicator_config.get("code", indicator_name)
        elif source == "oecd":
            if "dataset" in indicator_config and "indicator_code" in indicator_config:
                fetch_params["dataset"] = indicator_config["dataset"]
                fetch_params["indicator"] = indicator_config["indicator_code"]
            elif "code" in indicator_config:
                code = indicator_config["code"]
                if "." in code:
                    parts = code.split(".", 1)
                    fetch_params["dataset"] = parts[0]
                    fetch_params["indicator"] = parts[1]
                else:
                    fetch_params["dataset"] = code
            else:
                return jsonify({"status": "error", "message": "OECD indicator missing 'dataset' or 'code' field"}), 400
        elif source == "imf":
            if "database" in indicator_config and "indicator_code" in indicator_config:
                fetch_params["database"] = indicator_config["database"]
                fetch_params["indicator"] = indicator_config["indicator_code"]
            elif "code" in indicator_config:
                code = indicator_config["code"]
                if "." in code:
                    parts = code.split(".", 1)
                    fetch_params["database"] = parts[0]
                    fetch_params["indicator"] = parts[1]
                else:
                    fetch_params["database"] = "IFS"
                    fetch_params["indicator"] = code
            else:
                return jsonify({"status": "error", "message": "IMF indicator missing 'database' or 'code' field"}), 400
        elif source == "worldbank":
            fetch_params["indicator"] = indicator_config.get("indicator_code") or indicator_config.get("code")
            if not fetch_params["indicator"]:
                return jsonify({"status": "error", "message": "World Bank indicator missing 'indicator_code' or 'code' field"}), 400
        elif source == "eclac":
            fetch_params["table"] = indicator_config.get("table") or indicator_config.get("code")
            if not fetch_params["table"]:
                return jsonify({"status": "error", "message": "ECLAC indicator missing 'table' or 'code' field"}), 400

        if "url" in indicator_config:
            fetch_params["url"] = indicator_config["url"]

        try:
            raw_data = manager.ingest(source=source, **fetch_params)

            if raw_data is None or raw_data.empty:
                return jsonify({"status": "error", "message": "No data returned from source"}), 500

        except Exception as e:
            return jsonify({"status": "error", "message": f"Data ingestion failed: {str(e)}"}), 500

        # Clean the data
        cleaner = DataCleaner(config)
        topic = (
            indicator_config.get("tags", ["general"])[0]
            if indicator_config.get("tags")
            else "general"
        )
        coverage = "global"

        try:
            cleaned_data = cleaner.clean_dataset(raw_data)
            
            # Detect implicit region filter from identifier or tags
            target_region = "global"
            identifier_lower = (
                str(indicator_config.get("slug") or indicator_config.get("id") or indicator_id).lower()
            )
            
            if "latam" in identifier_lower or "latin america" in indicator_name.lower():
                target_region = "latam"
                coverage = "latam" 
                
            # Apply filter if needed
            if target_region != "global":
                cleaned_data = cleaner.filter_by_region(cleaned_data, target_region)

            data_summary = cleaner.get_data_summary(cleaned_data)

            identifier = (
                indicator_config.get("slug")
                or indicator_config.get("id")
                or indicator_id
            )
            output_path = cleaner.save_clean_dataset(
                data=cleaned_data,
                topic=topic,
                source=source,
                coverage=coverage,
                start_year=None,
                end_year=None,
                identifier=identifier,
            )

        except Exception as e:
            return jsonify({"status": "error", "message": f"Data cleaning failed: {str(e)}"}), 500

        # Generate metadata documentation
        generator = MetadataGenerator(config)
        metadata_text = None
        owid_metadata = None

        if source.lower() == "owid" and indicator_config.get("slug"):
            try:
                owid_source = manager.sources.get("owid")
                if owid_source:
                    owid_metadata = owid_source.fetch_metadata(indicator_config["slug"])
                    if "error" not in owid_metadata:
                        ai_packager = AIPackager(output_path.parent)
                        metadata_text = ai_packager.create_context_owid(owid_metadata)
                        generator.save_metadata_for_dataset(output_path, metadata_text)
            except Exception as e:
                logger.warning(f"OWID metadata notes failed: {e}")

        if metadata_text is None:
            try:
                metadata_text = generator.generate_metadata(
                    topic=topic,
                    data_summary=data_summary,
                    source=source,
                    transformations=data_summary.get("transformations", []),
                    original_source_url=indicator_config.get("url", ""),
                    dataset_info={
                        "identifier": identifier,
                        "indicator_id": indicator_config.get("id"),
                        "indicator_name": indicator_name,
                        "file_name": output_path.name,
                    },
                    force_regenerate=False,
                )
                generator.save_metadata_for_dataset(output_path, metadata_text)
            except Exception as e:
                logger.warning(f"Metadata generation failed: {e}")
                metadata_text = None

        # Create AI-ready package (for OWID sources)
        ai_package_files = {}
        if source.lower() == "owid" and indicator_config.get("slug"):
            try:
                if owid_metadata is None:
                    owid_source = manager.sources.get("owid")
                    if owid_source:
                        owid_metadata = owid_source.fetch_metadata(indicator_config["slug"])

                if owid_metadata and "error" not in owid_metadata:
                    ai_packager = AIPackager(output_path.parent)
                    ai_package_files = ai_packager.enhance_existing_dataset(
                        csv_path=output_path,
                        metadata=owid_metadata,
                        topic=topic,
                    )
                    logger.info(f"AI package created: {len(ai_package_files)} files")
            except Exception as e:
                logger.warning(f"AI packaging failed: {e}")
                ai_package_files = {}

        # Index the new dataset in the catalog
        try:
            from dataset_catalog import DatasetCatalog
            catalog = DatasetCatalog(config)
            catalog.index_dataset(output_path, force=True)
            logger.info(f"Indexed dataset: {output_path}")
        except Exception as e:
            logger.error(f"Failed to index dataset: {e}")

        # Success response
        response_payload = {
            "status": "success",
            "message": f"✓ Descarga completada: {indicator_name}",
            "details": {
                "output_file": str(output_path),
                "rows": int(data_summary.get("rows", 0)),
                "columns": int(data_summary.get("columns", 0)),
                "countries": int(len(data_summary.get("countries", []))),
                "date_range": data_summary.get("date_range", []),
                "metadata_generated": bool(metadata_text is not None),
                "ai_package": bool(ai_package_files),
            },
        }

        return jsonify(response_payload), 200

    except Exception as e:
        logger.error(f"Download error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/progress/stream")
def progress_stream() -> Response:
    """SSE endpoint for real-time download progress."""
    def generate():
        last_sent = None
        while True:
            progress = _download_progress.get('current', {
                'step': 'idle',
                'status': 'waiting',
                'percent': 0
            })
            
            if progress != last_sent:
                yield f"data: {json.dumps(progress)}\n\n"
                last_sent = progress.copy()
            
            time.sleep(1)
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@api_bp.route("/progress/poll")
def progress_poll() -> Response:
    """Polling fallback for browsers without SSE support."""
    progress = _download_progress.get('current', {
        'step': 'idle',
        'status': 'waiting',
        'percent': 0
    })
    return jsonify(progress)

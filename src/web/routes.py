from __future__ import annotations

import json
import time
import math
from typing import Any, Dict, List
from pathlib import Path
import glob
import pandas as pd

from flask import (
    Blueprint,
    Response,
    render_template,
    stream_with_context,
    request,
    jsonify,
    session,
)

# Import the real search functionality
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Config
from searcher import IndicatorSearcher
from dynamic_search import DynamicSearcher  # NEW: Dynamic search with API integration
from ingestion import DataIngestionManager
from cleaning import DataCleaner
from metadata import MetadataGenerator
from dataset_catalog import DatasetCatalog
from ai_chat import ChatAssistant
from chat_history import ChatHistory
from ai_packager import AIPackager, create_ai_package_from_owid
from pathlib import Path
from uuid import uuid4

ui_bp = Blueprint(
    "ui",
    __name__,
    template_folder="templates",
    static_folder="static",
)

# In-memory progress tracking for SSE
_download_progress: Dict[str, Dict] = {}


def check_indicator_downloaded(config: Config, indicator_id: str, source: str) -> bool:
    """
    Check if an indicator has already been downloaded by querying the dataset catalog.

    This looks for a matching `indicator_id` (preferred) or a matching `indicator_name`.
    Returns True if any matching dataset exists for the given source.
    """
    try:
        catalog = DatasetCatalog(config)
        # Prefer matching by indicator_id (exact match)
        conn_matches = [
            d
            for d in catalog.latest_per_identifier()
            if (
                d.get("indicator_id")
                and str(d.get("indicator_id")) == str(indicator_id)
                and d.get("source") == source.lower()
            )
        ]
        if conn_matches:
            return True

        # Fall back to matching by indicator_name (case-insensitive)
        name_matches = [
            d
            for d in catalog.latest_per_identifier()
            if (
                str(d.get("indicator_name", "")).lower() == str(indicator_id).lower()
                and d.get("source") == source.lower()
            )
        ]
        return len(name_matches) > 0
    except Exception as e:
        print(f"Error checking downloaded status via catalog: {e}")
        return False


NAV_ITEMS: List[Dict[str, str]] = [
    {"slug": "status", "label": "Status", "icon": "house"},
    {"slug": "browse_local", "label": "Browse Local", "icon": "folder"},
    {"slug": "browse_available", "label": "Browse Available", "icon": "cloud-download"},
    {"slug": "search", "label": "Search", "icon": "search"},
    {"slug": "chat", "label": "Chat AI", "icon": "chat"},
    {"slug": "help", "label": "Help", "icon": "question-circle"},
]


def base_context(active: str, title: str, subtitle: str = "") -> Dict[str, Any]:
    return {
        "nav_items": NAV_ITEMS,
        "active": active,
        "title": title,
        "subtitle": subtitle,
    }


def clean_nan_recursive(obj):
    """Recursively replace NaN values with None (null in JSON)."""
    if isinstance(obj, dict):
        return {k: clean_nan_recursive(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan_recursive(item) for item in obj]
    elif isinstance(obj, float) and math.isnan(obj):
        return None
    return obj


@ui_bp.route("/")
@ui_bp.route("/status")
def status() -> str:
    ctx = base_context("status", "Status", "Estado del proyecto")
    return render_template("status.html", **ctx)


@ui_bp.route("/browse/local")
@ui_bp.route("/browse_local")  # Also accept underscore version for convenience
def browse_local() -> str:
    ctx = base_context(
        "browse_local", "Browse Local", "Datasets disponibles localmente"
    )
    return render_template("browse_local.html", **ctx)


@ui_bp.route("/browse/available")
@ui_bp.route("/browse_available")
def browse_available() -> str:
    ctx = base_context(
        "browse_available", "Browse Available", "Indicadores disponibles para descargar"
    )
    return render_template("browse_available.html", **ctx)


@ui_bp.route("/search")
def search() -> str:
    ctx = base_context("search", "Search", "Buscar indicadores y temas")
    return render_template("search.html", **ctx)


# REMOVED: /download route - downloads now happen directly from /search page
# Users can click "Descargar" button on search results to download immediately

# REMOVED: /progress route and related API endpoints
# Progress tracking not needed - downloads are fast (<15s) and happen in /search page
# Removed routes: /progress, /api/progress/stream, /api/progress/poll


@ui_bp.route("/help")
def help_page() -> str:
    ctx = base_context("help", "Help", "Atajos y guia")
    return render_template("help.html", **ctx)


# Demo search data
MOCK_INDICATORS = [
    # Our World in Data (OWID) - Most comprehensive source
    {
        "id": "1",
        "indicator": "gdp_per_capita",
        "source": "owid",
        "topic": "salarios_reales",
        "keywords": "pib per cápita producto renta income",
    },
    {
        "id": "2",
        "indicator": "life_expectancy",
        "source": "owid",
        "topic": "libertad_economica",
        "keywords": "esperanza vida salud health",
    },
    {
        "id": "3",
        "indicator": "poverty_ratio",
        "source": "owid",
        "topic": "libertad_economica",
        "keywords": "pobreza razón ratio poverty",
    },
    {
        "id": "4",
        "indicator": "gini_coefficient_owid",
        "source": "owid",
        "topic": "libertad_economica",
        "keywords": "desigualdad gini coeficiente inequality",
    },
    {
        "id": "5",
        "indicator": "co2_emissions",
        "source": "owid",
        "topic": "libertad_economica",
        "keywords": "emisiones carbono co2 ambiental environmental",
    },
    {
        "id": "6",
        "indicator": "education_enrollment",
        "source": "owid",
        "topic": "libertad_economica",
        "keywords": "educación matrícula escolaridad education",
    },
    {
        "id": "7",
        "indicator": "unemployment_rate_owid",
        "source": "owid",
        "topic": "libertad_economica",
        "keywords": "desempleo tasa empleo unemployment",
    },
    {
        "id": "8",
        "indicator": "real_wages_owid",
        "source": "owid",
        "topic": "salarios_reales",
        "keywords": "salarios reales ingresos wages salary",
    },
    {
        "id": "9",
        "indicator": "tax_revenues_gdp",
        "source": "owid",
        "topic": "presion_fiscal",
        "keywords": "impuestos recaudación fiscal tax revenue tributaria",
    },
    {
        "id": "10",
        "indicator": "government_spending",
        "source": "owid",
        "topic": "presion_fiscal",
        "keywords": "gasto público government spending fiscal",
    },
    {
        "id": "11",
        "indicator": "income_distribution",
        "source": "owid",
        "topic": "libertad_economica",
        "keywords": "distribución ingresos income distribution wealth",
    },
    {
        "id": "12",
        "indicator": "labor_productivity",
        "source": "owid",
        "topic": "salarios_reales",
        "keywords": "productividad laboral productivity labor",
    },
    {
        "id": "13",
        "indicator": "inflation_consumer_prices",
        "source": "owid",
        "topic": "libertad_economica",
        "keywords": "inflación precios consumidor inflation prices",
    },
    {
        "id": "14",
        "indicator": "trade_openness",
        "source": "owid",
        "topic": "libertad_economica",
        "keywords": "comercio apertura trade openness",
    },
    {
        "id": "15",
        "indicator": "human_capital_index",
        "source": "owid",
        "topic": "libertad_economica",
        "keywords": "capital humano índice human capital education",
    },
    # ILOSTAT - Labor data
    {
        "id": "20",
        "indicator": "unemployment_rate",
        "source": "ilostat",
        "topic": "libertad_economica",
        "keywords": "desempleo tasa empleo unemployment",
    },
    {
        "id": "21",
        "indicator": "real_wage_index",
        "source": "ilostat",
        "topic": "salarios_reales",
        "keywords": "salario sueldo ingresos reales wage",
    },
    {
        "id": "22",
        "indicator": "informal_employment",
        "source": "ilostat",
        "topic": "informalidad_laboral",
        "keywords": "informalidad empleo informal trabajadores informality",
    },
    {
        "id": "23",
        "indicator": "wage_growth",
        "source": "ilostat",
        "topic": "salarios_reales",
        "keywords": "salarios crecimiento remuneración wage growth",
    },
    # OECD
    {
        "id": "30",
        "indicator": "gdp_growth",
        "source": "oecd",
        "topic": "libertad_economica",
        "keywords": "pib crecimiento producto interno bruto gdp growth",
    },
    {
        "id": "31",
        "indicator": "tax_revenue",
        "source": "oecd",
        "topic": "presion_fiscal",
        "keywords": "impuestos recaudación fiscal presión tributaria tax",
    },
    {
        "id": "32",
        "indicator": "minimum_wage",
        "source": "oecd",
        "topic": "salarios_reales",
        "keywords": "salario mínimo base piso minimum wage",
    },
    # World Bank
    {
        "id": "40",
        "indicator": "income_inequality",
        "source": "worldbank",
        "topic": "libertad_economica",
        "keywords": "ingresos desigualdad inequidad income inequality",
    },
    {
        "id": "41",
        "indicator": "per_capita_income",
        "source": "worldbank",
        "topic": "salarios_reales",
        "keywords": "ingresos per cápita renta promedio income capita",
    },
    {
        "id": "42",
        "indicator": "economic_freedom_index",
        "source": "worldbank",
        "topic": "libertad_economica",
        "keywords": "libertad económica índice freedom economic",
    },
    # IMF
    {
        "id": "50",
        "indicator": "inflation_rate",
        "source": "imf",
        "topic": "libertad_economica",
        "keywords": "inflación precios inflation",
    },
    # ECLAC
    {
        "id": "60",
        "indicator": "labor_informality_rate",
        "source": "eclac",
        "topic": "informalidad_laboral",
        "keywords": "informalidad laboral trabajadores informality labor",
    },
    {
        "id": "61",
        "indicator": "tax_pressure",
        "source": "eclac",
        "topic": "presion_fiscal",
        "keywords": "presión fiscal impuestos carga tributaria tax",
    },
]


@ui_bp.route("/api/search")
def search_api() -> Response:
    """
    Search API endpoint with hybrid local + remote search.

    Query params:
        q: Search query
        source: Filter by source (owid, oecd, etc.)
        topic: Filter by topic
        include_remote: Include remote API results (default: true)
    """
    query = request.args.get("q", "").strip()
    source_filter = request.args.get("source", "").lower().strip()
    topic_filter = request.args.get("topic", "").lower().strip()
    include_remote = request.args.get("include_remote", "true").lower() == "true"

    try:
        config = Config()

        # If filtering by source or topic, use old searcher (local only)
        if source_filter or topic_filter:
            searcher = IndicatorSearcher(config)
            if topic_filter:
                raw_results = searcher.search_by_topic(topic_filter)
            elif source_filter:
                raw_results = searcher.search_by_source(source_filter)
            else:
                raw_results = []

            # Format results
            results = []
            for r in raw_results:
                indicator_id = r.get("id", "")
                source = r.get("source", "")
                is_downloaded = check_indicator_downloaded(config, indicator_id, source)

                results.append(
                    {
                        "id": indicator_id,
                        "indicator": r.get("name", ""),
                        "source": source.upper(),
                        "description": r.get("description", ""),
                        "tags": ", ".join(r.get("tags", [])),
                        "downloaded": is_downloaded,
                        "remote": False,
                    }
                )

            return jsonify({"results": results, "total": len(results), "query": query})

        # Use dynamic searcher for general queries
        elif query:
            dynamic_searcher = DynamicSearcher(config, cache_ttl_minutes=5)
            search_results = dynamic_searcher.search(
                query, include_remote=include_remote
            )

            # Combine local and remote results
            all_indicators = (
                search_results["local_results"] + search_results["remote_results"]
            )

            # Format results for web frontend
            results = []
            for r in all_indicators:
                indicator_id = r.get("id", "")
                source = r.get("source", "")
                is_remote = r.get("remote", False)

                # Only check downloaded status for local indicators
                is_downloaded = (
                    False
                    if is_remote
                    else check_indicator_downloaded(config, indicator_id, source)
                )

                result = {
                    "id": indicator_id,
                    "indicator": r.get("name", ""),
                    "source": source.upper(),
                    "description": r.get("description", ""),
                    "tags": ", ".join(r.get("tags", []))
                    if isinstance(r.get("tags", []), list)
                    else r.get("tags", ""),
                    "downloaded": is_downloaded,
                    "remote": is_remote,  # Flag to show if from API
                }

                # Add slug and url for OWID remote indicators
                if is_remote and source.lower() == "owid":
                    if "slug" in r:
                        result["slug"] = r["slug"]
                    if "url" in r:
                        result["url"] = r["url"]

                results.append(result)

            return jsonify(
                {
                    "results": results,
                    "total": len(results),
                    "query": query,
                    "sources": search_results["sources"],
                }
            )
        else:
            # Return empty if no search criteria
            return jsonify({"results": [], "total": 0})
    except Exception as e:
        # Fallback to mock data if real searcher fails
        import traceback

        print(f"Search API error: {e}")
        traceback.print_exc()

        # Use mock data as fallback
        results = []
        for ind in MOCK_INDICATORS:
            # Match by query (searches indicator, topic, and keywords)
            if query:
                query_match = (
                    query in ind["indicator"].lower()
                    or query in ind["topic"].lower()
                    or query in ind.get("keywords", "").lower()
                )
                if not query_match:
                    continue

            # Match by source
            if source_filter and source_filter != ind["source"].lower():
                continue

            # Match by topic
            if topic_filter and topic_filter != ind["topic"].lower():
                continue

            results.append(ind)

        return jsonify({"results": results})


@ui_bp.route("/api/download/start", methods=["POST"])
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
        is_remote = data.get("remote", False)  # Flag for API results

        if not indicator_id or not source or not indicator_name:
            return jsonify(
                {
                    "status": "error",
                    "message": "Missing required fields (id, source, indicator)",
                }
            ), 400

        # Initialize configuration
        config = Config()

        # Step 1: Get indicator details
        indicator_config = None

        if is_remote:
            # For remote API results, construct config from request data
            indicator_config = {
                "id": indicator_id,
                "source": source,
                "name": indicator_name,
                "slug": data.get("slug"),  # OWID slug from API
                "url": data.get("url"),
                "description": data.get("description", ""),
            }
        else:
            # For local indicators, look up in indicators.yaml
            searcher = IndicatorSearcher(config)
            indicators = config.get_indicators()

            # Find the full indicator config
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

        # Step 2: Download data using DataIngestionManager
        manager = DataIngestionManager(config)

        # Get indicator-specific parameters based on source
        fetch_params = {}

        # OWID requires 'slug' parameter
        if source == "owid":
            if "slug" not in indicator_config:
                return jsonify(
                    {
                        "status": "error",
                        "message": f"OWID indicator missing 'slug' field",
                    }
                ), 400
            fetch_params["slug"] = indicator_config["slug"]

        # ILOSTAT requires 'indicator' code
        elif source == "ilostat":
            if "indicator_code" in indicator_config:
                fetch_params["indicator"] = indicator_config["indicator_code"]
            else:
                fetch_params["indicator"] = indicator_config.get("code", indicator_name)

        # OECD requires 'dataset' and optionally 'indicator'
        elif source == "oecd":
            # Check for explicit dataset and indicator_code fields first
            if "dataset" in indicator_config and "indicator_code" in indicator_config:
                fetch_params["dataset"] = indicator_config["dataset"]
                fetch_params["indicator"] = indicator_config["indicator_code"]
            # Otherwise, try to parse 'code' field in format "DATASET.INDICATOR"
            elif "code" in indicator_config:
                code = indicator_config["code"]
                if "." in code:
                    parts = code.split(".", 1)
                    fetch_params["dataset"] = parts[0]
                    fetch_params["indicator"] = parts[1]
                else:
                    # If no dot, assume entire code is dataset
                    fetch_params["dataset"] = code
            else:
                return jsonify(
                    {
                        "status": "error",
                        "message": f"OECD indicator missing 'dataset' or 'code' field",
                    }
                ), 400

        # IMF requires 'database' and 'indicator'
        elif source == "imf":
            # Check for explicit fields first
            if "database" in indicator_config and "indicator_code" in indicator_config:
                fetch_params["database"] = indicator_config["database"]
                fetch_params["indicator"] = indicator_config["indicator_code"]
            # Otherwise, try to parse 'code' field in format "DATABASE.INDICATOR"
            elif "code" in indicator_config:
                code = indicator_config["code"]
                if "." in code:
                    parts = code.split(".", 1)
                    fetch_params["database"] = parts[0]
                    fetch_params["indicator"] = parts[1]
                else:
                    # Default database if not specified
                    fetch_params["database"] = (
                        "IFS"  # International Financial Statistics
                    )
                    fetch_params["indicator"] = code
            else:
                return jsonify(
                    {
                        "status": "error",
                        "message": f"IMF indicator missing 'database' or 'code' field",
                    }
                ), 400

        # World Bank requires 'indicator' code
        elif source == "worldbank":
            if "indicator_code" in indicator_config:
                fetch_params["indicator"] = indicator_config["indicator_code"]
            elif "code" in indicator_config:
                fetch_params["indicator"] = indicator_config["code"]
            else:
                return jsonify(
                    {
                        "status": "error",
                        "message": f"World Bank indicator missing 'indicator_code' or 'code' field",
                    }
                ), 400

        # ECLAC requires 'table'
        elif source == "eclac":
            if "table" in indicator_config:
                fetch_params["table"] = indicator_config["table"]
            elif "code" in indicator_config:
                fetch_params["table"] = indicator_config["code"]
            else:
                return jsonify(
                    {
                        "status": "error",
                        "message": f"ECLAC indicator missing 'table' or 'code' field",
                    }
                ), 400

        # Add URL if present (for reference)
        if "url" in indicator_config:
            fetch_params["url"] = indicator_config["url"]

        try:
            raw_data = manager.ingest(source=source, **fetch_params)

            if raw_data is None or raw_data.empty:
                return jsonify(
                    {"status": "error", "message": "No data returned from source"}
                ), 500

        except Exception as e:
            return jsonify(
                {"status": "error", "message": f"Data ingestion failed: {str(e)}"}
            ), 500

        # Step 3: Clean the data
        cleaner = DataCleaner(config)

        # Use default cleaning parameters
        # TODO: Allow frontend to configure topic, coverage, year range
        topic = (
            indicator_config.get("tags", ["general"])[0]
            if indicator_config.get("tags")
            else "general"
        )
        coverage = "global"  # Default coverage

        try:
            cleaned_data = cleaner.clean_dataset(raw_data)
            data_summary = cleaner.get_data_summary(cleaned_data)

            # Save cleaned dataset — include slug/id to avoid filename collisions
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
                start_year=None,  # Auto-detect
                end_year=None,  # Auto-detect
                identifier=identifier,
            )

        except Exception as e:
            return jsonify(
                {"status": "error", "message": f"Data cleaning failed: {str(e)}"}
            ), 500

        # Step 4: Generate metadata documentation
        generator = MetadataGenerator(config)

        try:
            metadata_text = generator.generate_metadata(
                topic=topic,
                data_summary=data_summary,
                source=source,
                transformations=data_summary.get("transformations", []),
                original_source_url=indicator_config.get("url", ""),
                force_regenerate=False,
            )

        except Exception as e:
            # Metadata generation is optional, don't fail the entire process
            print(f"Warning: Metadata generation failed: {e}")
            metadata_text = None

        # Step 5: Create AI-ready package (for OWID sources)
        ai_package_files = {}
        if source.lower() == "owid" and indicator_config.get("slug"):
            try:
                # Fetch OWID metadata
                owid_source = manager.sources.get("owid")
                if owid_source:
                    owid_metadata = owid_source.fetch_metadata(indicator_config["slug"])

                    if "error" not in owid_metadata:
                        # Create AI package
                        ai_packager = AIPackager(output_path.parent)
                        ai_package_files = ai_packager.enhance_existing_dataset(
                            csv_path=output_path,
                            metadata=owid_metadata,
                            topic=topic,
                        )
                        print(f"✓ AI package created: {len(ai_package_files)} files")
            except Exception as e:
                print(f"Warning: AI packaging failed: {e}")
                ai_package_files = {}

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
        import traceback

        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


# ============================================================================
# AI Chat Assistant Routes
# ============================================================================


@ui_bp.route("/chat")
def chat_page() -> str:
    """Render AI chat assistant page."""
    ctx = base_context(
        "chat", "Chat Assistant", "Asistente de IA para consultas de datos"
    )
    return render_template("chat.html", **ctx)


# Chat history: per-user using Flask session
def _get_history_store() -> ChatHistory:
    """Return a ChatHistory instance scoped to the current Flask session user.

    Assigns a random `chat_user_id` into `session` if one does not exist yet.
    """
    user_id = session.get('chat_user_id')
    if not user_id:
        user_id = str(uuid4())
        session['chat_user_id'] = user_id
    user_dir = Path('.chat_history') / user_id
    return ChatHistory(user_dir)


@ui_bp.route('/api/chat/history')
def list_chat_history() -> Response:
    """Return recent chat sessions for the current user."""
    try:
        limit = int(request.args.get('limit', 50))
        store = _get_history_store()
        items = store.list_recent(limit=limit)
        # Return summary (id, title, provider, model, created_at)
        summaries = [
            {"id": it["id"], "title": it.get("title"), "provider": it.get("provider"), "model": it.get("model"), "created_at": it.get("created_at")} for it in items
        ]
        return jsonify({"status": "success", "history": summaries})
    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@ui_bp.route('/api/chat/history/<string:entry_id>')
def get_chat_history(entry_id: str) -> Response:
    """Return a full chat session by id for the current user.

    Supports optional history token via `history_token` query param or `X-History-Token` header
    to allow loading histories across contexts (use carefully).
    """
    try:
        history_token = request.args.get('history_token') or request.headers.get('X-History-Token')
        if history_token:
            user_dir = Path('.chat_history') / history_token
            store = ChatHistory(user_dir)
        else:
            store = _get_history_store()

        entry = store.get(entry_id)
        if not entry:
            return jsonify({"status": "error", "message": "Not found"}), 404
        return jsonify({"status": "success", "session": entry})
    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@ui_bp.route('/api/chat/history/<string:entry_id>/delete', methods=['DELETE', 'POST'])
def delete_chat_history(entry_id: str) -> Response:
    """Delete a chat history entry for the current user or provided token."""
    try:
        history_token = request.args.get('history_token') or request.headers.get('X-History-Token')
        if history_token:
            user_dir = Path('.chat_history') / history_token
            store = ChatHistory(user_dir)
        else:
            store = _get_history_store()

        ok = store.delete_entry(entry_id)
        if not ok:
            return jsonify({"status": "error", "message": "Not found"}), 404
        return jsonify({"status": "success", "message": "Deleted"})
    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@ui_bp.route('/api/chat/history/<string:entry_id>/rename', methods=['POST'])
def rename_chat_history(entry_id: str) -> Response:
    """Rename a chat history entry's title.

    JSON body: { "title": "New title" }
    """
    try:
        payload = request.get_json() or {}
        new_title = payload.get('title')
        if not new_title:
            return jsonify({"status": "error", "message": "Missing 'title'"}), 400

        history_token = request.args.get('history_token') or request.headers.get('X-History-Token')
        if history_token:
            user_dir = Path('.chat_history') / history_token
            store = ChatHistory(user_dir)
        else:
            store = _get_history_store()

        ok = store.rename_entry(entry_id, new_title)
        if not ok:
            return jsonify({"status": "error", "message": "Not found"}), 404
        return jsonify({"status": "success", "message": "Renamed"})
    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@ui_bp.route("/api/chat", methods=["POST"])
def chat_api() -> Response:
    """
    Process chat messages with AI assistant.

    Expected JSON body:
    {
        "message": "user's message",
        "conversation_history": []  // optional, for context
    }

    Returns:
    {
        "response": "assistant's response",
        "tool_calls": [...],  // tools used
        "conversation_history": [...]  // updated history
    }
    """
    try:
        data = request.get_json()
        message = data.get("message", "").strip()
        conversation_history = data.get("conversation_history", [])

        if not message:
            return jsonify({"status": "error", "message": "Message is required"}), 400

        # Initialize chat assistant
        config = Config()
        assistant = ChatAssistant(config)

        # Allow frontend to override provider/model selection
        provider = data.get('provider')
        model = data.get('model')
        if provider:
            try:
                if provider == 'ollama':
                    # Configure assistant to use Ollama
                    import requests as _requests
                    assistant.provider = 'ollama'
                    assistant._ollama_requests = _requests
                    assistant.ollama_host = assistant.llm_config.get('host', 'http://localhost:11434')
                    assistant.ollama_model = model or assistant.llm_config.get('model')
                    assistant.client = None
                else:
                    # Default to OpenRouter/OpenAI-compatible client
                    assistant.provider = 'openrouter'
                    assistant.llm_config['provider'] = 'openrouter'
                    if model:
                        assistant.llm_config['model'] = model
                    # Ensure OpenAI client exists (recreate if needed)
                    try:
                        from openai import OpenAI as _OpenAI
                        import os as _os
                        # Get API key from environment variable (not from llm_config which might be configured for ollama)
                        api_key = _os.getenv('OPENROUTER_API_KEY') or assistant.llm_config.get('api_key')
                        if not api_key:
                            raise ValueError("OPENROUTER_API_KEY not found in environment variables")
                        assistant.client = _OpenAI(
                            base_url=assistant.llm_config.get('base_url', 'https://openrouter.ai/api/v1'),
                            api_key=api_key
                        )
                    except Exception as e:
                        # If OpenAI client not available, leave assistant.client as-is
                        print(f"ERROR: Failed to create OpenRouter client: {e}")
                        pass
            except Exception as e:
                print(f"Warning: failed to apply provider/model override: {e}")

        # Process message
        result = assistant.chat(message, conversation_history)

        # Save chat session to history (store raw conversation history + metadata)
        try:
            # Allow optional history token from client to target a specific store
            history_token = data.get('history_token') or request.headers.get('X-History-Token')
            if history_token:
                user_dir = Path('.chat_history') / history_token
                history_store_local = ChatHistory(user_dir)
            else:
                history_store_local = _get_history_store()

            saved_id = history_store_local.add_entry(
                messages=result.get("conversation_history", []),
                provider=assistant.provider,
                model=assistant.ollama_model if assistant.provider == 'ollama' else assistant.llm_config.get('model'),
                title=(message[:120] if message else None),
            )
        except Exception as e:
            print(f"Warning: failed to save chat history: {e}")
            saved_id = None

        # Server-side convert markdown to HTML and sanitize
        try:
            import markdown as _md
            import bleach as _bleach

            md_text = result.get("response", "")
            # Convert Markdown -> HTML
            html = _md.markdown(md_text, extensions=["fenced_code", "tables", "nl2br"])
            # Sanitize HTML
            cleaned_html = _bleach.clean(
                html,
                tags=_bleach.sanitizer.ALLOWED_TAGS
                + [
                    "p",
                    "pre",
                    "code",
                    "h1",
                    "h2",
                    "h3",
                    "h4",
                    "h5",
                    "table",
                    "thead",
                    "tbody",
                    "tr",
                    "th",
                    "td",
                ],
                attributes={
                    "*": ["class", "id", "data-*"],
                    "a": ["href", "title", "rel"],
                    "img": ["src", "alt", "title"],
                },
                protocols=_bleach.sanitizer.ALLOWED_PROTOCOLS + ["data"],
            )
        except Exception as e:
            # If conversion/sanitization fails, fallback to plain text with simple escaping
            import html as _html

            cleaned_html = _html.escape(result.get("response", ""))

        return jsonify(
            {
                "status": "success",
                "response": cleaned_html,
                "tool_calls": result["tool_calls"],
                "conversation_history": result["conversation_history"],
                "history_id": saved_id,
            }
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify(
            {"status": "error", "message": f"Error processing chat: {str(e)}"}
        ), 500


@ui_bp.route("/api/datasets")
def list_datasets() -> Response:
    """
    List and search datasets in the catalog.

    Query params:
        q: Search query (optional)
        source: Filter by source (optional)
        topic: Filter by topic (optional)
        limit: Max results (default 100)
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
        import traceback

        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@ui_bp.route("/api/datasets/<int:dataset_id>")
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
        import traceback

        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@ui_bp.route("/api/datasets/<int:dataset_id>/preview")
def preview_dataset(dataset_id: int) -> Response:
    """Get preview data (first N rows) for a dataset.

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
        # Replace NaN with None (which becomes null in JSON)
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
        import traceback

        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@ui_bp.route("/api/remote/owid/preview")
def preview_owid_remote() -> Response:
    """Preview OWID remote data without saving to disk.

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
        import requests as _requests
        from io import StringIO as _StringIO
        import pandas as _pd

        resp = _requests.get(url, params=params, timeout=30)
        resp.raise_for_status()

        df = _pd.read_csv(_StringIO(resp.text))

        # Standardize columns
        if "Entity" in df.columns:
            df = df.rename(columns={"Entity": "country"})
        if "Year" in df.columns:
            df = df.rename(columns={"Year": "year"})
        if "Code" in df.columns:
            df = df.rename(columns={"Code": "country_code"})

        total_rows = len(df)
        # Truncate rows for preview
        df_preview = df.head(limit).copy()

        # Convert to JSON-friendly structure
        data_records = df_preview.to_dict(orient="records")

        # Replace NaN with None
        def replace_nan(obj):
            if isinstance(obj, dict):
                return {k: replace_nan(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [replace_nan(i) for i in obj]
            try:
                if obj != obj:  # NaN check
                    return None
            except Exception:
                pass
            return obj

        cleaned = replace_nan(data_records)

        preview = {
            "columns": df_preview.columns.tolist(),
            "rows": cleaned,
            "total_rows": total_rows,
            "dataset_info": {"slug": slug, "source": "owid", "preview_limit": limit},
        }

        return jsonify({"status": "success", "preview": preview})

    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@ui_bp.route("/api/chart/export-pdf")
def export_chart_pdf() -> Response:
    """Export chart as PDF from OWID.

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
        import requests as _requests

        resp = _requests.get(owid_pdf_url, timeout=30)
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
        import traceback

        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@ui_bp.route("/api/datasets/refresh", methods=["POST"])
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
            from src.metadata import MetadataGenerator
            from src.cleaning import DataCleaner
            import pandas as pd
            
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
                    print(f"Error generating metadata for dataset {ds.get('id')}: {e}")
                    metadata_errors += 1
            
            stats['metadata_generated'] = metadata_generated
            stats['metadata_errors'] = metadata_errors
            
        except Exception as e:
            print(f"Warning: Metadata generation failed: {e}")
            stats['metadata_warning'] = str(e)

        return jsonify(
            {"status": "success", "message": "Catalog refreshed and metadata regenerated", "stats": stats}
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@ui_bp.route("/api/datasets/statistics")
def get_catalog_statistics() -> Response:
    """Get catalog-wide statistics."""
    try:
        config = Config()
        catalog = DatasetCatalog(config)

        stats = catalog.get_statistics()

        # Clean up any NaN values in statistics
        def clean_nan(obj):
            if isinstance(obj, dict):
                return {k: clean_nan(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_nan(item) for item in obj]
            elif isinstance(obj, float) and obj != obj:  # NaN check
                return 0
            return obj

        stats = clean_nan(stats)

        return jsonify({"status": "success", "statistics": stats})

    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@ui_bp.route("/api/datasets/<int:dataset_id>/delete", methods=["DELETE", "POST"])
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
        import traceback

        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@ui_bp.route("/api/datasets/<int:dataset_id>/redownload", methods=["POST"])
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

        # Now trigger a new download
        # We need to reconstruct the download request
        source = dataset["source"].lower()
        indicator_name = dataset["indicator_name"]

        # NOTE: We cannot fully reconstruct the original download without the indicator ID or slug
        # For now, return an error message asking user to re-download from search
        return jsonify({
            "status": "error",
            "message": "Please re-download this dataset from the Search page. Auto re-download not yet supported.",
        }), 501

    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@ui_bp.route('/api/datasets/versions')
def get_dataset_versions() -> Response:
    """Return all versions for a given identifier and optional source.

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
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@ui_bp.route('/api/llm/models')
def get_llm_models() -> Response:
    """Return available models for a given LLM provider.

    Query params:
        provider: 'ollama' or 'openrouter' (default: openrouter)
    """
    try:
        provider = request.args.get('provider', 'openrouter').lower()
        config = Config()
        llm_cfg = config.get_llm_config()

        if provider == 'ollama':
            # Query local Ollama HTTP API for models; try several common endpoints
            host = llm_cfg.get('host', 'http://localhost:11434').rstrip('/')
            import requests as _requests

            endpoints = ["/v1/models", "/api/models", "/models"]
            models = []
            tried = []
            last_error = None

            for ep in endpoints:
                url = f"{host}{ep}"
                tried.append(url)
                try:
                    resp = _requests.get(url, timeout=5)
                    if resp.status_code != 200:
                        # record and continue
                        last_error = f"HTTP {resp.status_code} for {url}"
                        continue
                    try:
                        data = resp.json()
                    except Exception:
                        data = resp.text

                    # Normalize multiple shapes
                    if isinstance(data, dict):
                        if "data" in data and isinstance(data["data"], list):
                            for item in data["data"]:
                                if isinstance(item, dict) and "id" in item:
                                    models.append(item["id"])
                                elif isinstance(item, str):
                                    models.append(item)
                        elif "models" in data and isinstance(data["models"], list):
                            for m in data["models"]:
                                if isinstance(m, str):
                                    models.append(m)
                                elif isinstance(m, dict):
                                    name = m.get("name") or m.get("id") or m.get("model")
                                    tag = m.get("tag") or m.get("version")
                                    if name and tag:
                                        models.append(f"{name}:{tag}")
                                    elif name:
                                        models.append(name)
                        else:
                            # try to extract ids from lists inside dict
                            for v in data.values():
                                if isinstance(v, list):
                                    for it in v:
                                        if isinstance(it, dict) and "id" in it:
                                            models.append(it["id"])
                    elif isinstance(data, list):
                        for m in data:
                            if isinstance(m, str):
                                models.append(m)
                            elif isinstance(m, dict):
                                name = m.get("name") or m.get("id") or m.get("model")
                                tag = m.get("tag") or m.get("version")
                                if name and tag:
                                    models.append(f"{name}:{tag}")
                                elif name:
                                    models.append(name)

                    # If we found models, stop trying further endpoints
                    if models:
                        break

                except Exception as e:
                    last_error = str(e)
                    continue

            if models:
                return jsonify({"status": "success", "provider": "ollama", "models": models}), 200
            else:
                # If we could not fetch models, return 502 Bad Gateway with details
                msg = f"No models found from Ollama (tried: {', '.join(tried)}). Last error: {last_error}"
                print(msg)
                return jsonify({"status": "error", "provider": "ollama", "message": msg, "tried": tried}), 502

        else:
            # For OpenRouter or default, return configured model and a small default list
            configured_model = llm_cfg.get('model')
            default_models = [configured_model] if configured_model else ["gpt-oss-small", "gpt-oss-medium"]
            return jsonify({"status": "success", "provider": "openrouter", "models": default_models}), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@ui_bp.route("/api/progress/stream")
def progress_stream() -> Response:
    """SSE endpoint for real-time download progress."""
    def generate():
        last_sent = None
        while True:
            # Get current progress (would be updated by download process)
            progress = _download_progress.get('current', {
                'step': 'idle',
                'status': 'waiting',
                'percent': 0
            })
            
            # Only send if changed
            if progress != last_sent:
                yield f"data: {json.dumps(progress)}\n\n"
                last_sent = progress.copy()
            
            time.sleep(1)  # Check every second
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@ui_bp.route("/api/progress/poll")
def progress_poll() -> Response:
    """Polling fallback for browsers without SSE support."""
    progress = _download_progress.get('current', {
        'step': 'idle',
        'status': 'waiting',
        'percent': 0
    })
    return jsonify(progress)

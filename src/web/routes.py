from __future__ import annotations

import json
import time
import math
from typing import Any, Dict, List
from pathlib import Path
import glob
import pandas as pd

from flask import Blueprint, Response, render_template, stream_with_context, request, jsonify, session

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

ui_bp = Blueprint(
    "ui",
    __name__,
    template_folder="templates",
    static_folder="static",
)


def check_indicator_downloaded(config: Config, indicator_id: str, source: str) -> bool:
    """
    Check if an indicator has already been downloaded.
    
    Args:
        config: Configuration object
        indicator_id: Indicator ID
        source: Data source name
    
    Returns:
        True if indicator has been downloaded, False otherwise
    """
    try:
        clean_dir = config.get_directory('clean')
        
        # Search for any files matching the pattern *_{source}_*.csv
        # across all topic subdirectories
        for topic_dir in clean_dir.iterdir():
            if topic_dir.is_dir():
                # Look for files with source name in them
                pattern = f"*_{source.lower()}_*.csv"
                matching_files = list(topic_dir.glob(pattern))
                if matching_files:
                    # Found at least one file from this source
                    # Could enhance this to check indicator_id in filename
                    return True
        
        return False
    except Exception as e:
        print(f"Error checking downloaded status: {e}")
        return False

NAV_ITEMS: List[Dict[str, str]] = [
    {"slug": "status", "label": "Status", "icon": "house"},
    {"slug": "browse_local", "label": "Browse Local", "icon": "folder"},
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
    ctx = base_context("browse_local", "Browse Local", "Datasets disponibles localmente")
    return render_template("browse_local.html", **ctx)




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
    {"id": "1", "indicator": "gdp_per_capita", "source": "owid", "topic": "salarios_reales", "keywords": "pib per cápita producto renta income"},
    {"id": "2", "indicator": "life_expectancy", "source": "owid", "topic": "libertad_economica", "keywords": "esperanza vida salud health"},
    {"id": "3", "indicator": "poverty_ratio", "source": "owid", "topic": "libertad_economica", "keywords": "pobreza razón ratio poverty"},
    {"id": "4", "indicator": "gini_coefficient_owid", "source": "owid", "topic": "libertad_economica", "keywords": "desigualdad gini coeficiente inequality"},
    {"id": "5", "indicator": "co2_emissions", "source": "owid", "topic": "libertad_economica", "keywords": "emisiones carbono co2 ambiental environmental"},
    {"id": "6", "indicator": "education_enrollment", "source": "owid", "topic": "libertad_economica", "keywords": "educación matrícula escolaridad education"},
    {"id": "7", "indicator": "unemployment_rate_owid", "source": "owid", "topic": "libertad_economica", "keywords": "desempleo tasa empleo unemployment"},
    {"id": "8", "indicator": "real_wages_owid", "source": "owid", "topic": "salarios_reales", "keywords": "salarios reales ingresos wages salary"},
    {"id": "9", "indicator": "tax_revenues_gdp", "source": "owid", "topic": "presion_fiscal", "keywords": "impuestos recaudación fiscal tax revenue tributaria"},
    {"id": "10", "indicator": "government_spending", "source": "owid", "topic": "presion_fiscal", "keywords": "gasto público government spending fiscal"},
    {"id": "11", "indicator": "income_distribution", "source": "owid", "topic": "libertad_economica", "keywords": "distribución ingresos income distribution wealth"},
    {"id": "12", "indicator": "labor_productivity", "source": "owid", "topic": "salarios_reales", "keywords": "productividad laboral productivity labor"},
    {"id": "13", "indicator": "inflation_consumer_prices", "source": "owid", "topic": "libertad_economica", "keywords": "inflación precios consumidor inflation prices"},
    {"id": "14", "indicator": "trade_openness", "source": "owid", "topic": "libertad_economica", "keywords": "comercio apertura trade openness"},
    {"id": "15", "indicator": "human_capital_index", "source": "owid", "topic": "libertad_economica", "keywords": "capital humano índice human capital education"},
    
    # ILOSTAT - Labor data
    {"id": "20", "indicator": "unemployment_rate", "source": "ilostat", "topic": "libertad_economica", "keywords": "desempleo tasa empleo unemployment"},
    {"id": "21", "indicator": "real_wage_index", "source": "ilostat", "topic": "salarios_reales", "keywords": "salario sueldo ingresos reales wage"},
    {"id": "22", "indicator": "informal_employment", "source": "ilostat", "topic": "informalidad_laboral", "keywords": "informalidad empleo informal trabajadores informality"},
    {"id": "23", "indicator": "wage_growth", "source": "ilostat", "topic": "salarios_reales", "keywords": "salarios crecimiento remuneración wage growth"},
    
    # OECD
    {"id": "30", "indicator": "gdp_growth", "source": "oecd", "topic": "libertad_economica", "keywords": "pib crecimiento producto interno bruto gdp growth"},
    {"id": "31", "indicator": "tax_revenue", "source": "oecd", "topic": "presion_fiscal", "keywords": "impuestos recaudación fiscal presión tributaria tax"},
    {"id": "32", "indicator": "minimum_wage", "source": "oecd", "topic": "salarios_reales", "keywords": "salario mínimo base piso minimum wage"},
    
    # World Bank
    {"id": "40", "indicator": "income_inequality", "source": "worldbank", "topic": "libertad_economica", "keywords": "ingresos desigualdad inequidad income inequality"},
    {"id": "41", "indicator": "per_capita_income", "source": "worldbank", "topic": "salarios_reales", "keywords": "ingresos per cápita renta promedio income capita"},
    {"id": "42", "indicator": "economic_freedom_index", "source": "worldbank", "topic": "libertad_economica", "keywords": "libertad económica índice freedom economic"},
    
    # IMF
    {"id": "50", "indicator": "inflation_rate", "source": "imf", "topic": "libertad_economica", "keywords": "inflación precios inflation"},
    
    # ECLAC
    {"id": "60", "indicator": "labor_informality_rate", "source": "eclac", "topic": "informalidad_laboral", "keywords": "informalidad laboral trabajadores informality labor"},
    {"id": "61", "indicator": "tax_pressure", "source": "eclac", "topic": "presion_fiscal", "keywords": "presión fiscal impuestos carga tributaria tax"},
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
                
                results.append({
                    "id": indicator_id,
                    "indicator": r.get("name", ""),
                    "source": source.upper(),
                    "description": r.get("description", ""),
                    "tags": ", ".join(r.get("tags", [])),
                    "downloaded": is_downloaded,
                    "remote": False
                })
            
            return jsonify({"results": results, "total": len(results), "query": query})
        
        # Use dynamic searcher for general queries
        elif query:
            dynamic_searcher = DynamicSearcher(config, cache_ttl_minutes=5)
            search_results = dynamic_searcher.search(query, include_remote=include_remote)
            
            # Combine local and remote results
            all_indicators = search_results["local_results"] + search_results["remote_results"]
            
            # Format results for web frontend
            results = []
            for r in all_indicators:
                indicator_id = r.get("id", "")
                source = r.get("source", "")
                is_remote = r.get("remote", False)
                
                # Only check downloaded status for local indicators
                is_downloaded = False if is_remote else check_indicator_downloaded(config, indicator_id, source)
                
                result = {
                    "id": indicator_id,
                    "indicator": r.get("name", ""),
                    "source": source.upper(),
                    "description": r.get("description", ""),
                    "tags": ", ".join(r.get("tags", [])) if isinstance(r.get("tags", []), list) else r.get("tags", ""),
                    "downloaded": is_downloaded,
                    "remote": is_remote  # Flag to show if from API
                }
                
                # Add slug and url for OWID remote indicators
                if is_remote and source.lower() == "owid":
                    if "slug" in r:
                        result["slug"] = r["slug"]
                    if "url" in r:
                        result["url"] = r["url"]
                
                results.append(result)
            
            return jsonify({
                "results": results,
                "total": len(results),
                "query": query,
                "sources": search_results["sources"]
            })
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
                    query in ind["indicator"].lower() or
                    query in ind["topic"].lower() or
                    query in ind.get("keywords", "").lower()
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
            return jsonify({"status": "error", "message": "Missing required fields (id, source, indicator)"}), 400
        
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
                return jsonify({"status": "error", "message": f"Indicator {indicator_id} not found in indicators.yaml"}), 404
        
        # Step 2: Download data using DataIngestionManager
        manager = DataIngestionManager(config)
        
        # Get indicator-specific parameters based on source
        fetch_params = {}
        
        # OWID requires 'slug' parameter
        if source == 'owid':
            if 'slug' not in indicator_config:
                return jsonify({"status": "error", "message": f"OWID indicator missing 'slug' field"}), 400
            fetch_params["slug"] = indicator_config["slug"]
        
        # ILOSTAT requires 'indicator' code
        elif source == 'ilostat':
            if 'indicator_code' in indicator_config:
                fetch_params["indicator"] = indicator_config["indicator_code"]
            else:
                fetch_params["indicator"] = indicator_config.get("code", indicator_name)
        
        # OECD requires 'dataset' and optionally 'indicator'
        elif source == 'oecd':
            # Check for explicit dataset and indicator_code fields first
            if 'dataset' in indicator_config and 'indicator_code' in indicator_config:
                fetch_params["dataset"] = indicator_config["dataset"]
                fetch_params["indicator"] = indicator_config["indicator_code"]
            # Otherwise, try to parse 'code' field in format "DATASET.INDICATOR"
            elif 'code' in indicator_config:
                code = indicator_config["code"]
                if '.' in code:
                    parts = code.split('.', 1)
                    fetch_params["dataset"] = parts[0]
                    fetch_params["indicator"] = parts[1]
                else:
                    # If no dot, assume entire code is dataset
                    fetch_params["dataset"] = code
            else:
                return jsonify({"status": "error", "message": f"OECD indicator missing 'dataset' or 'code' field"}), 400
        
        # IMF requires 'database' and 'indicator'
        elif source == 'imf':
            # Check for explicit fields first
            if 'database' in indicator_config and 'indicator_code' in indicator_config:
                fetch_params["database"] = indicator_config["database"]
                fetch_params["indicator"] = indicator_config["indicator_code"]
            # Otherwise, try to parse 'code' field in format "DATABASE.INDICATOR"
            elif 'code' in indicator_config:
                code = indicator_config["code"]
                if '.' in code:
                    parts = code.split('.', 1)
                    fetch_params["database"] = parts[0]
                    fetch_params["indicator"] = parts[1]
                else:
                    # Default database if not specified
                    fetch_params["database"] = "IFS"  # International Financial Statistics
                    fetch_params["indicator"] = code
            else:
                return jsonify({"status": "error", "message": f"IMF indicator missing 'database' or 'code' field"}), 400
        
        # World Bank requires 'indicator' code
        elif source == 'worldbank':
            if 'indicator_code' in indicator_config:
                fetch_params["indicator"] = indicator_config["indicator_code"]
            elif 'code' in indicator_config:
                fetch_params["indicator"] = indicator_config["code"]
            else:
                return jsonify({"status": "error", "message": f"World Bank indicator missing 'indicator_code' or 'code' field"}), 400
        
        # ECLAC requires 'table'
        elif source == 'eclac':
            if 'table' in indicator_config:
                fetch_params["table"] = indicator_config["table"]
            elif 'code' in indicator_config:
                fetch_params["table"] = indicator_config["code"]
            else:
                return jsonify({"status": "error", "message": f"ECLAC indicator missing 'table' or 'code' field"}), 400
        
        # Add URL if present (for reference)
        if "url" in indicator_config:
            fetch_params["url"] = indicator_config["url"]
        
        try:
            raw_data = manager.ingest(source=source, **fetch_params)
            
            if raw_data is None or raw_data.empty:
                return jsonify({"status": "error", "message": "No data returned from source"}), 500
            
        except Exception as e:
            return jsonify({"status": "error", "message": f"Data ingestion failed: {str(e)}"}), 500
        
        # Step 3: Clean the data
        cleaner = DataCleaner(config)
        
        # Use default cleaning parameters
        # TODO: Allow frontend to configure topic, coverage, year range
        topic = indicator_config.get("tags", ["general"])[0] if indicator_config.get("tags") else "general"
        coverage = "global"  # Default coverage
        
        try:
            cleaned_data = cleaner.clean_dataset(raw_data)
            data_summary = cleaner.get_data_summary(cleaned_data)
            
            # Save cleaned dataset
            output_path = cleaner.save_clean_dataset(
                data=cleaned_data,
                topic=topic,
                source=source,
                coverage=coverage,
                start_year=None,  # Auto-detect
                end_year=None     # Auto-detect
            )
            
        except Exception as e:
            return jsonify({"status": "error", "message": f"Data cleaning failed: {str(e)}"}), 500
        
        # Step 4: Generate metadata documentation
        generator = MetadataGenerator(config)
        
        try:
            metadata_text = generator.generate_metadata(
                topic=topic,
                data_summary=data_summary,
                source=source,
                transformations=data_summary.get("transformations", []),
                original_source_url=indicator_config.get("url", ""),
                force_regenerate=False
            )
            
        except Exception as e:
            # Metadata generation is optional, don't fail the entire process
            print(f"Warning: Metadata generation failed: {e}")
            metadata_text = None
        
        # Success response
        return jsonify({
            "status": "success",
            "message": f"✓ Descarga completada: {indicator_name}",
            "details": {
                "output_file": str(output_path),
                "rows": data_summary.get("rows", 0),
                "columns": data_summary.get("columns", 0),  # Already an int, not a list
                "countries": len(data_summary.get("countries", [])),
                "date_range": data_summary.get("date_range", []),
                "metadata_generated": metadata_text is not None
            }
        })
        
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
    ctx = base_context("chat", "Chat Assistant", "Asistente de IA para consultas de datos")
    return render_template("chat.html", **ctx)


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
        
        # Process message
        result = assistant.chat(message, conversation_history)
        
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
                tags=_bleach.sanitizer.ALLOWED_TAGS + ["p", "pre", "code", "h1", "h2", "h3", "h4", "h5", "table", "thead", "tbody", "tr", "th", "td"],
                attributes={
                    "*": ["class", "id", "data-*"],
                    "a": ["href", "title", "rel"],
                    "img": ["src", "alt", "title"],
                },
                protocols=_bleach.sanitizer.ALLOWED_PROTOCOLS + ["data"]
            )
        except Exception as e:
            # If conversion/sanitization fails, fallback to plain text with simple escaping
            import html as _html
            cleaned_html = _html.escape(result.get("response", ""))

        return jsonify({
            "status": "success",
            "response": cleaned_html,
            "tool_calls": result["tool_calls"],
            "conversation_history": result["conversation_history"]
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"Error processing chat: {str(e)}"
        }), 500



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
        query = request.args.get('q', '')
        source = request.args.get('source', '')
        topic = request.args.get('topic', '')
        limit = int(request.args.get('limit', 100))
        
        # Build filters
        filters = {}
        if source:
            filters['source'] = source
        if topic:
            filters['topic'] = topic
        
        # Search datasets
        results = catalog.search(query, filters=filters, limit=limit)
        
        # Format results
        datasets = []
        for ds in results:
            # Clean up the dataset object
            dataset = dict(ds)
            
            # Parse JSON fields
            if dataset.get('countries_json'):
                try:
                    dataset['countries'] = json.loads(dataset['countries_json'])
                except:
                    dataset['countries'] = []
            else:
                dataset['countries'] = []
                
            if dataset.get('columns_json'):
                try:
                    dataset['columns'] = json.loads(dataset['columns_json'])
                except:
                    dataset['columns'] = []
            else:
                dataset['columns'] = []
            
            # Replace None/NaN with 0 for numeric fields
            for key in ['null_percentage', 'completeness_score', 'min_year', 'max_year', 
                       'row_count', 'column_count', 'country_count', 'file_size_bytes']:
                if key in dataset and (dataset[key] is None or 
                                      (isinstance(dataset[key], float) and math.isnan(dataset[key]))):
                    dataset[key] = 0
            
            datasets.append(dataset)
        
        return jsonify({
            "status": "success",
            "total": len(datasets),
            "datasets": datasets
        })
        
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
        if dataset.get('countries_json'):
            dataset['countries'] = json.loads(dataset['countries_json'])
        if dataset.get('columns_json'):
            dataset['columns'] = json.loads(dataset['columns_json'])
        
        # Replace None/NaN with 0 for numeric fields
        for key in ['null_percentage', 'completeness_score', 'min_year', 'max_year', 
                   'row_count', 'column_count', 'country_count', 'file_size_bytes']:
            if key in dataset and (dataset[key] is None or (isinstance(dataset[key], float) and dataset[key] != dataset[key])):
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
            return jsonify({"status": "error", "message": "Could not load dataset"}), 500
        
        # Convert DataFrame to JSON-friendly format
        # Replace NaN with None (which becomes null in JSON)
        data_dict = df.to_dict(orient='records')
        cleaned_data = clean_nan_recursive(data_dict)
        
        preview_data = {
            "columns": df.columns.tolist(),
            "rows": cleaned_data,
            "total_rows": len(df),
            "dataset_info": {
                "id": dataset['id'],
                "file_name": dataset['file_name'],
                "source": dataset['source'],
                "indicator_name": dataset['indicator_name'],
                "row_count": dataset['row_count'],
                "column_count": dataset['column_count']
            }
        }
        
        return jsonify({"status": "success", "preview": preview_data})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@ui_bp.route("/api/datasets/refresh", methods=["POST"])
def refresh_datasets() -> Response:
    """Re-index datasets to refresh the catalog."""
    try:
        config = Config()
        catalog = DatasetCatalog(config)
        
        # Get force parameter
        force = request.get_json().get("force", False) if request.get_json() else False
        
        # Reindex all
        stats = catalog.index_all(force=force)
        
        return jsonify({
            "status": "success",
            "message": "Catalog refreshed",
            "stats": stats
        })
        
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
        file_path = Path(dataset['file_path'])
        if file_path.exists():
            file_path.unlink()
        
        # Delete from catalog
        success = catalog.delete_dataset(dataset_id)
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"Dataset '{dataset['indicator_name']}' deleted successfully"
            })
        else:
            return jsonify({"status": "error", "message": "Failed to delete dataset"}), 500
        
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
        file_path = Path(dataset['file_path'])
        if file_path.exists():
            file_path.unlink()
        catalog.delete_dataset(dataset_id)
        
        # Now trigger a new download
        # We need to reconstruct the download request
        source = dataset['source'].lower()
        indicator_name = dataset['indicator_name']
        
        # NOTE: We cannot fully reconstruct the original download without the indicator ID or slug
        # For now, return an error message asking user to re-download from search
        return jsonify({
            "status": "error",
            "message": "Please re-download this dataset from the Search page. Auto re-download not yet supported."
        }), 501
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500



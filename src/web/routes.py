"""
UI Routes for the Mises Data Curator Flask application.

This module contains only UI routes (HTML rendering).
All API routes have been migrated to src/web/api/*.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pathlib import Path
import json

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    request,
    Response,
)

# Import base configuration
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.const import NAV_ITEMS

# UI Blueprint
ui_bp = Blueprint(
    "ui",
    __name__,
    template_folder="templates",
    static_folder="static",
)

# NAV_ITEMS moved to src.const.py


def base_context(active: str, title: str, subtitle: str = "") -> Dict[str, Any]:
    """Create base context for all pages."""
    return {
        "nav_items": NAV_ITEMS,
        "active": active,
        "title": title,
        "subtitle": subtitle,
    }


def _infer_chart_field_type(field_name: str) -> str:
    field_lower = field_name.lower()
    if "year" in field_lower:
        return "quantitative"
    if any(token in field_lower for token in ["date", "time", "fecha"]):
        return "temporal"
    return "nominal"


def _build_chart_spec(chart_intent: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    encodings = chart_intent.get("encodings") or {}
    x_field = encodings.get("x") or encodings.get("x_field") or chart_intent.get("x")
    y_field = encodings.get("y") or encodings.get("y_field") or chart_intent.get("y")
    if not x_field or not y_field:
        return None

    chart_type = (chart_intent.get("type") or "line").lower()
    if chart_type in {"scatter_compare"}:
        chart_type = "scatter"
    if chart_type in {"map", "mapa"}:
        return None

    if chart_type == "bar":
        mark: Any = "bar"
    elif chart_type == "area":
        mark = {"type": "area", "opacity": 0.7}
    elif chart_type in {"scatter", "bubble"}:
        mark = {"type": "point", "filled": True, "size": 80}
    else:
        mark = {"type": "line", "point": True}

    spec: Dict[str, Any] = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "mark": mark,
        "encoding": {
            "x": {"field": x_field, "type": _infer_chart_field_type(x_field)},
            "y": {"field": y_field, "type": "quantitative"},
        },
    }

    title = chart_intent.get("title")
    if title:
        spec["title"] = title

    color_field = encodings.get("color")
    if color_field:
        spec["encoding"]["color"] = {"field": color_field, "type": "nominal"}

    size_field = encodings.get("size")
    if size_field:
        spec["encoding"]["size"] = {"field": size_field, "type": "quantitative"}

    return spec


# ============================================================================
# UI ROUTES (HTML Pages)
# ============================================================================

# Import for data access
from src.config import Config
from src.dataset_catalog import DatasetCatalog

@ui_bp.route("/")
@ui_bp.route("/status")
def status() -> str:
    """Render the status/home page."""
    ctx = base_context("status", "Status", "Estado del proyecto")
    
    try:
        config = Config()
        catalog = DatasetCatalog(config)
        
        # Get statistics
        catalog_stats = catalog.get_statistics()
        
        # Get recent datasets (activity)
        recent_datasets = catalog.search(limit=5)
        
        # Format for template
        ctx["stats"] = {
            "local_datasets": catalog_stats.get("total_datasets", 0),
            "recent_downloads": catalog_stats.get("total_datasets", 0), # Using total count as proxy for now
            "sources_count": len(catalog_stats.get("by_source", {})),
            "completeness": catalog_stats.get("avg_completeness", 0)
        }
        
        # Format recent activity
        ctx["recent_activity"] = [
            {
                "name": ds.get("indicator_name", "Unknown Dataset"),
                "date": ds.get("indexed_at", ""),
                "source": ds.get("source", "unknown")
            }
            for ds in recent_datasets
        ]
        
    except Exception as e:
        print(f"Error loading status data: {e}")
        ctx["stats"] = {}
        ctx["recent_activity"] = []
    
    return render_template("status.html", **ctx)


@ui_bp.route("/browse/local")
@ui_bp.route("/browse_local")
def browse_local() -> str:
    """Render the local datasets browser page."""
    ctx = base_context(
        "browse_local", "Browse Local", "Datasets disponibles localmente"
    )
    return render_template("browse_local.html", **ctx)


@ui_bp.route("/browse/available")
@ui_bp.route("/browse_available")
def browse_available():
    """Redirect to search view (consolidated view)."""
    return redirect(url_for("ui.search"))


@ui_bp.route("/edit")
def edit_page() -> str:
    """Render the dataset editor page."""
    ctx = base_context("edit", "Edit", "Editar datasets")
    ctx["dataset_id"] = request.args.get("dataset_id", type=int)
    return render_template("visualization_canvas.html", **ctx)


@ui_bp.route("/search")
def search() -> str:
    """Render the search page."""
    ctx = base_context("search", "Search", "Buscar indicadores y temas")
    return render_template("search.html", **ctx)


@ui_bp.route("/copilot_chat")
def copilot_chat_page() -> str:
    """Render the Copilot chat interface page."""
    # Check if Copilot is available
    try:
        from copilot_agent import MisesCopilotAgent
        copilot_available = True
    except ImportError:
        copilot_available = False
    
    ctx = base_context(
        "copilot_chat", "Copilot Chat", "Chat with AI powered by GitHub Copilot SDK"
    )
    ctx["copilot_available"] = copilot_available
    return render_template("copilot_chat.html", **ctx)


@ui_bp.route("/visualizepg")
def visualizepg_page() -> str:
    """Render the PyGWalker visualization view."""
    ctx = base_context("visualizepg", "Visualizacion", "Explorar con PyGWalker")
    dataset_id = request.args.get("dataset_id", type=int)
    ctx["dataset_id"] = dataset_id
    ctx["pygwalker_error"] = ""
    ctx["selected_dataset"] = None
    ctx["large_dataset_threshold_bytes"] = 50 * 1024 * 1024
    ctx["iframe_src"] = ""
    ctx["chart_intent"] = request.args.get("chart_intent", "")

    if dataset_id:
        try:
            config = Config()
            catalog = DatasetCatalog(config)
            dataset = catalog.get_dataset(dataset_id)
            if not dataset:
                ctx["pygwalker_error"] = "Dataset not found."
            else:
                ctx["selected_dataset"] = {
                    "id": dataset_id,
                    "name": dataset.get("indicator_name") or dataset.get("file_name"),
                    "row_count": dataset.get("row_count"),
                    "file_size_bytes": dataset.get("file_size_bytes"),
                    "source": dataset.get("source"),
                }
                iframe_params = {"dataset_id": dataset_id}
                if ctx["chart_intent"]:
                    iframe_params["chart_intent"] = ctx["chart_intent"]
                ctx["iframe_src"] = url_for("ui.visualizepg_frame", **iframe_params)
        except Exception as exc:
            ctx["pygwalker_error"] = f"Error loading dataset metadata: {exc}"

    return render_template("visualization_pygwalker.html", **ctx)


@ui_bp.route("/visualizepg/frame")
def visualizepg_frame() -> str:
    """Render the PyGWalker iframe content."""
    dataset_id = request.args.get("dataset_id", type=int)
    chart_intent_raw = request.args.get("chart_intent", "")
    ctx = {
        "dataset_id": dataset_id,
        "pygwalker_html": "",
        "pygwalker_error": "",
    }

    if dataset_id:
        try:
            import pandas as pd
            from pygwalker.api.pygwalker import PygWalker

            config = Config()
            catalog = DatasetCatalog(config)
            dataset = catalog.get_dataset(dataset_id)
            if not dataset:
                ctx["pygwalker_error"] = "Dataset not found."
            else:
                file_path = Path(dataset["file_path"])
                if not file_path.exists():
                    ctx["pygwalker_error"] = "Dataset file not found."
                else:
                    df = pd.read_csv(file_path)
                    spec: Any = ""
                    if chart_intent_raw:
                        try:
                            intent = json.loads(chart_intent_raw)
                            spec = _build_chart_spec(intent) or ""
                        except json.JSONDecodeError:
                            spec = ""
                    walker = PygWalker(
                        gid=None,
                        dataset=df,
                        field_specs=[],
                        spec=spec,
                        source_invoke_code="pyg.walk(df, spec='____pyg_walker_spec_params____')",
                        theme_key="g2",
                        appearance="light",
                        show_cloud_tool=True,
                        use_preview=True,
                        kernel_computation=False,
                        cloud_computation=False,
                        use_save_tool=True,
                        is_export_dataframe=True,
                        kanaries_api_key="",
                        default_tab="vis",
                        gw_mode="explore",
                    )
                    ctx["pygwalker_html"] = walker.to_html_without_iframe()
        except Exception as exc:
            ctx["pygwalker_error"] = f"Error loading PyGWalker: {exc}"

    if ctx["pygwalker_html"]:
        return Response(ctx["pygwalker_html"], mimetype="text/html")
    return render_template("visualization_pygwalker_frame.html", **ctx)


@ui_bp.route("/help")
def help_page() -> str:
    """Render the help page."""
    ctx = base_context("help", "Help", "Atajos y guia")
    return render_template("help.html", **ctx)

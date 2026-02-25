"""
UI Routes for the Mises Data Curator Flask application.

This module contains only UI routes (HTML rendering).
All API routes have been migrated to src/web/api/*.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path
import json

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    request,
    Response,
    current_app,
)
from flask_login import login_required, current_user
from flask_babel import gettext as _

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
@login_required
def index():
    """Redirect root to search page."""
    return redirect(url_for('ui.search'))

@ui_bp.route("/status")
@login_required
def status() -> str:
    """Render the status/home page."""
    ctx = base_context("status", _("Status"), _("Project Status"))

    catalog = DatasetCatalog(Config())
    accessible_datasets = catalog.list_accessible_datasets(
        current_user.username,
        include_public=True,
        limit=5000,
    )

    sources = {ds.get("source") for ds in accessible_datasets if ds.get("source")}
    completeness_scores = []
    for ds in accessible_datasets:
        score = ds.get("completeness_score")
        if score is None:
            continue
        try:
            completeness_scores.append(float(score))
        except (TypeError, ValueError):
            continue

    avg_completeness = (
        sum(completeness_scores) / len(completeness_scores)
        if completeness_scores
        else 0
    )

    ctx["stats"] = {
        "local_datasets": len(accessible_datasets),
        "recent_downloads": len(accessible_datasets),
        "sources_count": len(sources),
        "completeness": avg_completeness,
    }

    def _parse_dataset_timestamp(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str) and value:
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return datetime.min
        return datetime.min

    def _sort_key(dataset: Dict[str, Any]) -> datetime:
        indexed_at = _parse_dataset_timestamp(dataset.get("indexed_at"))
        if indexed_at != datetime.min:
            return indexed_at
        created_at = _parse_dataset_timestamp(dataset.get("created_at"))
        if created_at != datetime.min:
            return created_at
        return _parse_dataset_timestamp(dataset.get("modified_at"))

    recent_sorted = sorted(accessible_datasets, key=_sort_key, reverse=True)
    recent_activity = []
    for dataset in recent_sorted[:5]:
        timestamp = _sort_key(dataset)
        recent_activity.append(
            {
                "name": dataset.get("indicator_name") or dataset.get("file_name") or "Unknown Dataset",
                "date": timestamp.isoformat() if timestamp != datetime.min else "",
                "source": dataset.get("source") or "unknown",
            }
        )
    ctx["recent_activity"] = recent_activity
    
    return render_template("status.html", **ctx)


@ui_bp.route("/browse/local")
@ui_bp.route("/browse_local")
@login_required
def browse_local() -> str:
    """Render the local datasets browser page."""
    ctx = base_context(
        "browse_local", _("Browse Local"), _("Locally Available Datasets")
    )
    return render_template("browse_local.html", **ctx)


@ui_bp.route("/browse/available")
@ui_bp.route("/browse_available")
@login_required
def browse_available():
    """Redirect to search view (consolidated view)."""
    return redirect(url_for("ui.search"))


@ui_bp.route("/edit")
@login_required
def edit_page() -> str:
    """Render the dataset editor page."""
    ctx = base_context("edit", _("Edit"), _("Edit Datasets"))
    ctx["dataset_id"] = request.args.get("dataset_id", type=int)
    return render_template("visualization_canvas.html", **ctx)


@ui_bp.route("/search")
@login_required
def search() -> str:
    """Render the search page."""
    ctx = base_context("search", _("Search"), _("Search Indicators and Topics"))
    return render_template("search.html", **ctx)


@ui_bp.route("/copilot_chat")
@login_required
def copilot_chat_page() -> str:
    """Render the Copilot chat interface page."""
    # Check if Copilot is available
    try:
        from copilot_agent import MisesCopilotAgent
        copilot_available = True
    except ImportError:
        copilot_available = False
    
    ctx = base_context(
        "copilot_chat", _("Copilot Chat"), _("Chat with AI powered by GitHub Copilot SDK")
    )
    ctx["copilot_available"] = copilot_available
    return render_template("copilot_chat.html", **ctx)


@ui_bp.route("/visualizepg")
@login_required
def visualizepg_page() -> str:
    """Render the PyGWalker visualization view."""
    ctx = base_context("visualizepg", _("Visualization"), _("Explore with PyGWalker"))
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
@login_required
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
@login_required
def help_page() -> str:
    """Render the help page."""
    ctx = base_context("help", _("Help"), _("Shortcuts and Guide"))
    return render_template("help.html", **ctx)


@ui_bp.route("/notebooks")
@login_required
def notebooks_page() -> str:
    """Render embedded Jupyter notebooks page."""
    ctx = base_context("notebooks", _("Notebooks"), _("Interactive notebooks"))
    manager = current_app.extensions.get("jupyter_manager")
    ctx["jupyter_enabled"] = bool(manager and manager.enabled)
    ctx["jupyter_url"] = url_for("jupyter_proxy.proxy", path="lab")
    return render_template("notebooks.html", **ctx)

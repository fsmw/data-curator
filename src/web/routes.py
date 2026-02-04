"""
UI Routes for the Mises Data Curator Flask application.

This module contains only UI routes (HTML rendering).
All API routes have been migrated to src/web/api/*.
"""

from __future__ import annotations

from typing import Any, Dict, List
from pathlib import Path

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
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


@ui_bp.route("/search")
def search() -> str:
    """Render the search page."""
    ctx = base_context("search", "Search", "Buscar indicadores y temas")
    return render_template("search.html", **ctx)


@ui_bp.route("/compare")
def compare() -> str:
    """Render the comparison page."""
    ctx = base_context("compare", "Compare Datasets", "Correlaciones y Comparaciones")
    return render_template("compare.html", **ctx)


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


@ui_bp.route("/help")
def help_page() -> str:
    """Render the help page."""
    ctx = base_context("help", "Help", "Atajos y guia")
    return render_template("help.html", **ctx)

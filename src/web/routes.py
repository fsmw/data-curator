from __future__ import annotations

import json
import time
from typing import Any, Dict, List

from flask import Blueprint, Response, render_template, stream_with_context, request, jsonify

ui_bp = Blueprint(
    "ui",
    __name__,
    template_folder="templates",
    static_folder="static",
)

NAV_ITEMS: List[Dict[str, str]] = [
    {"slug": "status", "label": "Status", "icon": "Home"},
    {"slug": "browse_local", "label": "Browse Local", "icon": "Folder"},
    {"slug": "browse_available", "label": "Browse Available", "icon": "CloudDownload"},
    {"slug": "search", "label": "Search", "icon": "Search"},
    {"slug": "download", "label": "Download", "icon": "Download"},
    {"slug": "progress", "label": "Progress", "icon": "LineChart"},
    {"slug": "help", "label": "Help", "icon": "Help"},
]


def base_context(active: str, title: str, subtitle: str = "") -> Dict[str, Any]:
    return {
        "nav_items": NAV_ITEMS,
        "active": active,
        "title": title,
        "subtitle": subtitle,
    }


@ui_bp.route("/")
@ui_bp.route("/status")
def status() -> str:
    ctx = base_context("status", "Status", "Estado del proyecto")
    return render_template("status.html", **ctx)


@ui_bp.route("/browse/local")
def browse_local() -> str:
    ctx = base_context("browse_local", "Browse Local", "Datasets disponibles localmente")
    return render_template("browse_local.html", **ctx)


@ui_bp.route("/browse/available")
def browse_available() -> str:
    ctx = base_context("browse_available", "Browse Available", "Indicadores disponibles por fuente")
    return render_template("browse_available.html", **ctx)


@ui_bp.route("/search")
def search() -> str:
    ctx = base_context("search", "Search", "Buscar indicadores y temas")
    return render_template("search.html", **ctx)


@ui_bp.route("/download")
def download() -> str:
    ctx = base_context("download", "Download", "Configurar descargas y cola")
    return render_template("download.html", **ctx)


@ui_bp.route("/progress")
def progress() -> str:
    ctx = base_context("progress", "Progress", "Monitorear progreso y logs")
    return render_template("progress.html", **ctx)


@ui_bp.route("/help")
def help_page() -> str:
    ctx = base_context("help", "Help", "Atajos y guia")
    return render_template("help.html", **ctx)


@ui_bp.route("/api/progress/stream")
def progress_stream() -> Response:
    """SSE demo stream; replace with real coordinator events later."""

    def event_stream():
        sample = [
            {"step": "ingest", "status": "running", "percent": 25},
            {"step": "clean", "status": "running", "percent": 55},
            {"step": "document", "status": "running", "percent": 80},
            {"step": "done", "status": "complete", "percent": 100},
        ]
        for payload in sample:
            yield f"data: {json.dumps(payload)}\n\n"
            time.sleep(0.8)

    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")


@ui_bp.route("/api/progress/poll")
def progress_poll() -> Response:
    """Polling fallback delivering a single snapshot."""
    payload = {
        "step": "document",
        "status": "running",
        "percent": 72,
    }
    return Response(json.dumps(payload), mimetype="application/json")


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
    """Search API endpoint."""
    query = request.args.get("q", "").lower().strip()
    source = request.args.get("source", "").lower().strip()
    topic = request.args.get("topic", "").lower().strip()

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
        if source and source != ind["source"].lower():
            continue
        
        # Match by topic
        if topic and topic != ind["topic"].lower():
            continue
        
        results.append(ind)

    return jsonify({"results": results})

"""
Report Generation Agent for Mises Data Curator.

Generates narrative reports and insights from economic data analysis.
Creates structured reports with executive summaries, findings, and conclusions.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
import numpy as np

from .base import BaseAgent, AgentResponse, TableContext
from .prompts import REPORT_GEN_AGENT_SYSTEM_PROMPT_ES, REPORT_GEN_AGENT_SYSTEM_PROMPT_EN
from .client import MisesLLMClient
from .utils import generate_data_summary, extract_json_objects, detect_economic_columns

logger = logging.getLogger(__name__)


# =============================================================================
# Report Data Structures
# =============================================================================

@dataclass
class Finding:
    """A single finding/insight from the data."""
    titulo: str
    descripcion: str
    evidencia: str
    importancia: str = "media"  # alta, media, baja
    categoria: Optional[str] = None  # tendencia, comparacion, anomalia, etc.


@dataclass
class EconomicReport:
    """Complete economic analysis report."""
    titulo: str
    fecha: str
    resumen_ejecutivo: str
    contexto: str
    hallazgos: List[Finding] = field(default_factory=list)
    tendencias: List[str] = field(default_factory=list)
    comparaciones: List[str] = field(default_factory=list)
    conclusiones: str = ""
    recomendaciones: List[str] = field(default_factory=list)
    fuentes_datos: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "titulo": self.titulo,
            "fecha": self.fecha,
            "resumen_ejecutivo": self.resumen_ejecutivo,
            "contexto": self.contexto,
            "hallazgos": [
                {
                    "titulo": h.titulo,
                    "descripcion": h.descripcion,
                    "evidencia": h.evidencia,
                    "importancia": h.importancia,
                    "categoria": h.categoria
                }
                for h in self.hallazgos
            ],
            "tendencias": self.tendencias,
            "comparaciones": self.comparaciones,
            "conclusiones": self.conclusiones,
            "recomendaciones": self.recomendaciones,
            "fuentes_datos": self.fuentes_datos
        }
    
    def to_markdown(self) -> str:
        """Generate markdown version of the report."""
        lines = [
            f"# {self.titulo}",
            f"*Fecha: {self.fecha}*",
            "",
            "## Resumen Ejecutivo",
            self.resumen_ejecutivo,
            "",
            "## Contexto",
            self.contexto,
            "",
            "## Hallazgos Principales",
        ]
        
        for i, h in enumerate(self.hallazgos, 1):
            lines.append(f"### {i}. {h.titulo}")
            lines.append(h.descripcion)
            lines.append(f"*Evidencia: {h.evidencia}*")
            lines.append("")
        
        if self.tendencias:
            lines.append("## Tendencias Observadas")
            for t in self.tendencias:
                lines.append(f"- {t}")
            lines.append("")
        
        if self.comparaciones:
            lines.append("## Comparaciones Clave")
            for c in self.comparaciones:
                lines.append(f"- {c}")
            lines.append("")
        
        lines.append("## Conclusiones")
        lines.append(self.conclusiones)
        
        if self.recomendaciones:
            lines.append("")
            lines.append("## Recomendaciones")
            for r in self.recomendaciones:
                lines.append(f"- {r}")
        
        if self.fuentes_datos:
            lines.append("")
            lines.append("---")
            lines.append("*Fuentes: " + ", ".join(self.fuentes_datos) + "*")
        
        return "\n".join(lines)


# =============================================================================
# Report Generation Agent
# =============================================================================

class ReportGenAgent(BaseAgent):
    """
    Agent specialized in generating narrative economic reports.
    
    Capabilities:
    - Generate executive summaries
    - Identify and describe key findings
    - Analyze trends over time
    - Create comparisons between entities
    - Synthesize conclusions and recommendations
    """

    def __init__(
        self,
        client: Optional[MisesLLMClient] = None,
        language: str = "es",
        **kwargs
    ):
        super().__init__(
            client=client,
            name="ReportGenAgent",
            language=language,
            **kwargs
        )

    def _get_system_prompt(self) -> str:
        if self.language == "es":
            return REPORT_GEN_AGENT_SYSTEM_PROMPT_ES
        return REPORT_GEN_AGENT_SYSTEM_PROMPT_EN

    # =========================================================================
    # Report Generation
    # =========================================================================

    def generate_report(
        self,
        tables: List[TableContext],
        topic: Optional[str] = None,
        focus_areas: Optional[List[str]] = None
    ) -> AgentResponse:
        """
        Generate a full report using LLM.
        
        Args:
            tables: Data tables to analyze
            topic: Specific topic to focus on
            focus_areas: Specific areas to emphasize
            
        Returns:
            AgentResponse with report content
        """
        # Build goal
        if self.language == "es":
            goal = f"""Genera un reporte de análisis económico basado en los datos proporcionados.

"""
            if topic:
                goal += f"**Tema principal:** {topic}\n\n"
            
            if focus_areas:
                goal += f"**Áreas de enfoque:** {', '.join(focus_areas)}\n\n"
            
            goal += """El reporte debe incluir:
1. Resumen ejecutivo (2-3 oraciones)
2. Contexto de los datos
3. 3-5 hallazgos principales con evidencia
4. Tendencias observadas
5. Conclusiones

Responde con un JSON estructurado."""

        else:
            goal = f"""Generate an economic analysis report based on the provided data.

"""
            if topic:
                goal += f"**Main topic:** {topic}\n\n"
            
            if focus_areas:
                goal += f"**Focus areas:** {', '.join(focus_areas)}\n\n"
            
            goal += """The report should include:
1. Executive summary (2-3 sentences)
2. Data context
3. 3-5 main findings with evidence
4. Observed trends
5. Conclusions

Respond with structured JSON."""

        return self.run(goal, tables, execute_code=False)

    # =========================================================================
    # Automated Analysis (No LLM)
    # =========================================================================

    def generate_quick_report(
        self,
        df: pd.DataFrame,
        table_name: str = "datos",
        topic: str = "Análisis de Datos"
    ) -> EconomicReport:
        """
        Generate a quick automated report without LLM.
        
        Args:
            df: DataFrame to analyze
            table_name: Name of the data table
            topic: Report topic
            
        Returns:
            EconomicReport with automated insights
        """
        fecha = datetime.now().strftime("%Y-%m-%d")
        hallazgos = []
        tendencias = []
        comparaciones = []
        
        # Detect economic columns
        econ_cols = detect_economic_columns(df)
        
        # Basic statistics
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        # Generate findings from numeric columns
        for col in numeric_cols[:5]:  # Limit to 5
            stats = df[col].describe()
            
            # Check for high variance
            if stats['std'] / stats['mean'] > 0.5 if stats['mean'] != 0 else False:
                hallazgos.append(Finding(
                    titulo=f"Alta variabilidad en {col}",
                    descripcion=f"La columna {col} muestra alta dispersión en los valores.",
                    evidencia=f"Coef. variación: {(stats['std']/stats['mean']*100):.1f}%",
                    importancia="media",
                    categoria="estadistica"
                ))
        
        # Time-based trends (if year column exists)
        year_cols = econ_cols.get("year", [])
        if year_cols and numeric_cols:
            year_col = year_cols[0]
            for num_col in numeric_cols[:3]:
                try:
                    yearly = df.groupby(year_col)[num_col].mean()
                    if len(yearly) >= 3:
                        trend = "creciente" if yearly.iloc[-1] > yearly.iloc[0] else "decreciente"
                        change = ((yearly.iloc[-1] - yearly.iloc[0]) / yearly.iloc[0] * 100)
                        tendencias.append(
                            f"{num_col}: tendencia {trend} ({change:+.1f}% desde {yearly.index[0]} hasta {yearly.index[-1]})"
                        )
                except:
                    pass
        
        # Country comparisons (if country column exists)
        country_cols = econ_cols.get("country", [])
        if country_cols and numeric_cols:
            country_col = country_cols[0]
            for num_col in numeric_cols[:2]:
                try:
                    by_country = df.groupby(country_col)[num_col].mean().sort_values(ascending=False)
                    if len(by_country) >= 2:
                        top = by_country.index[0]
                        bottom = by_country.index[-1]
                        ratio = by_country.iloc[0] / by_country.iloc[-1] if by_country.iloc[-1] != 0 else 0
                        comparaciones.append(
                            f"{num_col}: {top} lidera con {ratio:.1f}x sobre {bottom}"
                        )
                except:
                    pass
        
        # Build context
        contexto = f"Análisis basado en {len(df):,} registros con {len(df.columns)} variables."
        if econ_cols:
            detected = [f"{k}: {v[0]}" for k, v in econ_cols.items() if v]
            contexto += f" Variables económicas detectadas: {', '.join(detected)}."
        
        # Build summary
        if hallazgos:
            resumen = f"Se identificaron {len(hallazgos)} hallazgos principales. "
        else:
            resumen = "Análisis exploratorio de los datos. "
        
        if tendencias:
            resumen += f"Se observan {len(tendencias)} tendencias temporales."
        
        # Build conclusions
        if tendencias or comparaciones:
            conclusiones = "Los datos revelan patrones significativos en las variables económicas analizadas. "
            if tendencias:
                conclusiones += "Las tendencias temporales sugieren cambios estructurales. "
            if comparaciones:
                conclusiones += "Existen diferencias notables entre las entidades comparadas."
        else:
            conclusiones = "Se requiere análisis adicional para extraer conclusiones definitivas."
        
        return EconomicReport(
            titulo=topic,
            fecha=fecha,
            resumen_ejecutivo=resumen,
            contexto=contexto,
            hallazgos=hallazgos,
            tendencias=tendencias,
            comparaciones=comparaciones,
            conclusiones=conclusiones,
            fuentes_datos=[table_name]
        )

    # =========================================================================
    # Specialized Report Types
    # =========================================================================

    def generate_comparison_report(
        self,
        tables: List[TableContext],
        entities: List[str],
        metrics: List[str]
    ) -> AgentResponse:
        """
        Generate a comparative analysis report.
        
        Args:
            tables: Data tables
            entities: Entities to compare (countries, years, etc.)
            metrics: Metrics to compare
            
        Returns:
            AgentResponse with comparison report
        """
        if self.language == "es":
            goal = f"""Genera un reporte comparativo entre: {', '.join(entities)}

Métricas a comparar: {', '.join(metrics)}

Estructura del reporte:
1. Resumen de la comparación
2. Análisis por métrica
3. Ranking de entidades
4. Conclusiones

Responde con JSON estructurado."""
        else:
            goal = f"""Generate a comparative report between: {', '.join(entities)}

Metrics to compare: {', '.join(metrics)}

Report structure:
1. Comparison summary
2. Analysis by metric
3. Entity ranking
4. Conclusions

Respond with structured JSON."""

        return self.run(goal, tables, execute_code=False)

    def generate_trend_report(
        self,
        tables: List[TableContext],
        time_column: str,
        metrics: List[str]
    ) -> AgentResponse:
        """
        Generate a trend analysis report.
        
        Args:
            tables: Data tables
            time_column: Column with time dimension
            metrics: Metrics to analyze over time
            
        Returns:
            AgentResponse with trend report
        """
        if self.language == "es":
            goal = f"""Genera un reporte de análisis de tendencias.

Dimensión temporal: {time_column}
Métricas a analizar: {', '.join(metrics)}

Estructura:
1. Resumen de tendencias principales
2. Análisis por métrica
3. Puntos de inflexión importantes
4. Proyecciones (si es posible)
5. Conclusiones

Responde con JSON estructurado."""
        else:
            goal = f"""Generate a trend analysis report.

Time dimension: {time_column}
Metrics to analyze: {', '.join(metrics)}

Structure:
1. Main trends summary
2. Analysis by metric
3. Important inflection points
4. Projections (if possible)
5. Conclusions

Respond with structured JSON."""

        return self.run(goal, tables, execute_code=False)


# =============================================================================
# Convenience Functions
# =============================================================================

def quick_report(df: pd.DataFrame, topic: str = "Análisis Económico") -> str:
    """
    Generate a quick markdown report from a DataFrame.
    
    Args:
        df: DataFrame to analyze
        topic: Report topic
        
    Returns:
        Markdown formatted report
    """
    agent = ReportGenAgent()
    report = agent.generate_quick_report(df, topic=topic)
    return report.to_markdown()

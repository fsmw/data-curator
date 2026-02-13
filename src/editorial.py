"""
Freedom Data Editorial Module
============================

This module handles the 'last mile' of data curation: transforming
statistical evidence into communicable content (Dato de la Semana).

Capabilities:
- Automated identification of interesting trends
- Microlearning content generation
- Formatting for institutional channels

Author: Freedom Data Team
Date: 2026-02-02
"""

from typing import Dict, List, Any, Optional
import pandas as pd
from pathlib import Path



try:
    from .metadata import MetadataGenerator
except ImportError:
    # Handle testing environment
    MetadataGenerator = None

class DataHighlightSelector:
    """Identifies potential 'Data of the Week' based on statistical anomalies or trends."""
    
    def __init__(self, data: pd.DataFrame):
        self.data = data
        
    def find_spikes(self, value_col: str, threshold: float = 2.0) -> List[Dict]:
        """
        Find periods with unusual variance (Z-score > threshold).
        
        Args:
            value_col: Column to analyze (e.g., 'value', 'salary')
            threshold: Z-score threshold for anomaly detection
        """
        if value_col not in self.data.columns:
            return []
            
        series = self.data[value_col].dropna()
        if len(series) < 5:
            return []
            
        # Calculate Z-scores
        mean = series.mean()
        std = series.std()
        if std == 0:
            return []
            
        z_scores = (series - mean) / std
        anomalies = self.data.loc[z_scores.abs() > threshold].copy()
        
        results = []
        for idx, row in anomalies.iterrows():
            results.append({
                "type": "spike",
                "date": row.get('year', row.get('date')),
                "value": row[value_col],
                "z_score": z_scores[idx],
                "description": f"Value {row[value_col]:.2f} deviates significantly (Z={z_scores[idx]:.1f}) from mean"
            })
            
        return results
        
    def find_records(self, value_col: str) -> List[Dict]:
        """Find historical maximums or minimums."""
        if value_col not in self.data.columns:
            return []
            
        series = self.data[value_col].dropna()
        if series.empty:
            return []
            
        max_val = series.max()
        min_val = series.min()
        
        max_row = self.data.loc[self.data[value_col] == max_val].iloc[0]
        min_row = self.data.loc[self.data[value_col] == min_val].iloc[0]
        
        return [
            {
                "type": "record_high",
                "date": max_row.get('year', max_row.get('date')),
                "value": max_val,
                "description": f"Historical maximum reached: {max_val:.2f}"
            },
            {
                "type": "record_low",
                "date": min_row.get('year', min_row.get('date')),
                "value": min_val,
                "description": f"Historical minimum reached: {min_val:.2f}"
            }
        ]


class MicrolearningGenerator:
    """Generates text and structures for educational content."""
    
    def __init__(self, config=None):
        self.config = config
        
    def generate_draft(self, highlight: Dict, topic: str, context: Optional[str] = None) -> str:
        """
        Generate a draft post using templates.
        
        Args:
            highlight: Dictionary containing the data insight
            topic: Context topic (e.g. 'inflation')
            context: Additional context
            
        Returns:
            Markdown content for the post
        """
        template = """
# 📊 Dato de la Semana: {topic}

**{headline}**

_{description}_

El dato destacado de hoy nos muestra un evento clave en {date}:
el valor alcanzó **{value}**, lo que representa un {type_desc}.

## 💡 ¿Por qué es importante?
{context}

---
*Fuente: Mises Data Curator*
"""
        type_map = {
            "spike": "desvío significativo de la tendencia histórica",
            "record_high": "máximo histórico registrado",
            "record_low": "mínimo histórico registrado"
        }
        
        type_desc = type_map.get(highlight.get('type'), "evento interesante")
        headline = f"Récord en {topic}" if "record" in highlight.get('type', '') else f"Anomalía en {topic}"
        
        return template.format(
            topic=topic.replace('_', ' ').title(),
            headline=headline,
            description=highlight.get('description'),
            date=highlight.get('date'),
            value=f"{highlight.get('value'):.2f}",
            type_desc=type_desc,
            context=context or "Este indicador es fundamental para comprender la coyuntura actual."
        )


def create_weekly_pack(
    data_path: str,
    value_col: str = "value",
    topic: str = "economy"
) -> Dict[str, Any]:
    """
    Orchestrate creation of the Weekly Data Pack.
    """
    path = Path(data_path)
    if path.suffix == '.parquet':
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path)
        
    selector = DataHighlightSelector(df)
    
    # 1. Find insights
    spikes = selector.find_spikes(value_col)
    records = selector.find_records(value_col)
    highlights = spikes + records
    
    if not highlights:
        return {"status": "no_highlights_found"}
        
    # Pick the most significant highlight (max absolute z-score or record)
    # Simple heuristic: prefer records, then spikes
    best_highlight = highlights[0]
    
    # 2. Generate content
    generator = MicrolearningGenerator()
    draft = generator.generate_draft(best_highlight, topic)
    
    return {
        "highlight": best_highlight,
        "draft_content": draft,
        "all_insights": highlights
    }

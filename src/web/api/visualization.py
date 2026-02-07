"""
Visualization API endpoints.

Provides chart generation and field derivation capabilities:
- Chart templates with Vega-Lite specs (23+ templates)
- AI-powered field derivation
- Chart generation from encodings
- Semantic type metadata and NL instruction handling
- Performance optimization for large datasets
"""

from flask import request, jsonify
import pandas as pd
import numpy as np
import json
import hashlib
from functools import lru_cache
import re

from . import api_bp


# =============================================================================
# Semantic Type and Metadata
# =============================================================================

SEMANTIC_TYPES = {
    "geographic": {
        "patterns": ["lat", "long", "longitude", "latitude", "país", "country", "state", "provincia", "región"],
        "description": "Geographic coordinate or region"
    },
    "temporal": {
        "patterns": ["año", "year", "fecha", "date", "month", "mes", "day", "día", "time", "hora", "quarter", "trim"],
        "description": "Time or date field"
    },
    "currency": {
        "patterns": ["precio", "price", "cost", "costo", "salary", "salario", "gdp", "pib", "ingreso", "income", "revenue"],
        "description": "Monetary value"
    },
    "percentage": {
        "patterns": ["pct", "percent", "%", "rate", "tasa", "porcentaje", "ratio"],
        "description": "Percentage or proportion"
    },
    "categorical": {
        "patterns": ["id", "code", "código", "category", "type", "tipo"],
        "description": "Category or grouping field"
    }
}


def clean_dataframe_for_json(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean DataFrame to make it JSON-serializable.
    Replaces NaN and inf values with None.
    """
    result = df.copy()
    
    # Handle each column based on its dtype
    for col in result.columns:
        if pd.api.types.is_numeric_dtype(result[col]):
            # For numeric columns: use mask to check for NaN or inf, set to None
            mask = pd.isna(result[col]) | np.isinf(result[col])
            result[col] = result[col].astype('object')  # Convert to object to hold None
            result.loc[mask, col] = None
        else:
            # For non-numeric columns: just replace NaN with None
            mask = pd.isna(result[col])
            result[col] = result[col].astype('object')  # Convert to object to hold None
            result.loc[mask, col] = None
    
    return result


def dataframe_to_json_records(df: pd.DataFrame) -> list:
    """
    Safely convert DataFrame to JSON-serializable list of records.
    Handles NaN, inf, and datetime values.
    """
    df_clean = clean_dataframe_for_json(df)
    return df_clean.to_dict(orient="records")


def auto_detect_encodings(df: pd.DataFrame, template_id: str = None) -> dict:
    """
    Auto-detect optimal encodings based on data types and field names.
    Returns dict with suggested x, y, color, size encodings.
    """
    encodings = {}
    
    # Get field metadata
    temporal_fields = []
    numeric_fields = []
    categorical_fields = []
    
    for col in df.columns:
        stype = detect_semantic_type(col, df)
        data_type = infer_field_type(df, col)
        
        if stype == "temporal" or data_type == "temporal":
            temporal_fields.append(col)
        elif data_type == "quantitative":
            numeric_fields.append(col)
        else:
            categorical_fields.append(col)
    
    # Pie chart: prefer a low-cardinality category + numeric measure
    if template_id == "pie":
        preferred_category = None
        if categorical_fields:
            category_scores = []
            for col in categorical_fields:
                try:
                    category_scores.append((df[col].nunique(dropna=True), col))
                except Exception:
                    category_scores.append((float("inf"), col))
            category_scores.sort(key=lambda x: x[0])
            preferred_category = category_scores[0][1] if category_scores else None

        if numeric_fields and preferred_category:
            encodings["theta"] = {"field": numeric_fields[0], "type": "quantitative"}
            encodings["color"] = {"field": preferred_category, "type": "nominal"}
        elif preferred_category:
            encodings["theta"] = {"field": preferred_category, "type": "quantitative", "aggregate": "count"}
            encodings["color"] = {"field": preferred_category, "type": "nominal"}
        return encodings

    # Suggest X axis (prefer temporal, then categorical)
    if temporal_fields:
        encodings["x"] = {"field": temporal_fields[0], "type": "temporal"}
    elif categorical_fields:
        encodings["x"] = {"field": categorical_fields[0], "type": "nominal"}
    elif numeric_fields:
        encodings["x"] = {"field": numeric_fields[0], "type": "quantitative"}
    
    # Suggest Y axis (prefer numeric, then categorical if X is temporal)
    if numeric_fields and encodings.get("x", {}).get("field") != numeric_fields[0]:
        encodings["y"] = {"field": numeric_fields[0], "type": "quantitative"}
    elif numeric_fields and "y" not in encodings:
        encodings["y"] = {"field": numeric_fields[0], "type": "quantitative"}
    elif categorical_fields and encodings.get("x", {}).get("field") != categorical_fields[0]:
        encodings["y"] = {"field": categorical_fields[0], "type": "nominal"}
    
    # Suggest color (use first categorical field not used as X)
    for col in categorical_fields:
        if col != encodings.get("x", {}).get("field"):
            encodings["color"] = {"field": col, "type": "nominal"}
            break
    
    # Suggest encoding based on template
    if template_id == "scatter":
        if len(numeric_fields) >= 2:
            encodings["x"] = {"field": numeric_fields[0], "type": "quantitative"}
            encodings["y"] = {"field": numeric_fields[1], "type": "quantitative"}
            encodings["color"] = {"field": categorical_fields[0], "type": "nominal"} if categorical_fields else None
    elif template_id == "heatmap":
        if len(categorical_fields) >= 2 and numeric_fields:
            encodings["x"] = {"field": categorical_fields[0], "type": "nominal"}
            encodings["y"] = {"field": categorical_fields[1], "type": "nominal"}
            encodings["color"] = {"field": numeric_fields[0], "type": "quantitative"}
    
    return encodings


CHART_TEMPLATES = {
    "line": {
        "id": "line",
        "name": "Line",
        "icon": "bi-graph-up",
        "description": "Series temporales y tendencias",
        "required_encodings": ["x", "y"],
        "optional_encodings": ["color", "opacity", "column", "row"],
        "spec_template": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "mark": {"type": "line"},
            "encoding": {}
        }
    },
    "line_dotted": {
        "id": "line_dotted",
        "name": "Dotted Line",
        "icon": "bi-graph-up",
        "description": "Lineas con puntos",
        "required_encodings": ["x", "y"],
        "optional_encodings": ["color", "opacity", "column", "row"],
        "spec_template": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "mark": {"type": "line", "point": True},
            "encoding": {}
        }
    },
    "bar": {
        "id": "bar",
        "name": "Bar",
        "icon": "bi-bar-chart",
        "description": "Comparaciones categoricas",
        "required_encodings": ["x", "y"],
        "optional_encodings": ["color", "opacity", "column", "row"],
        "spec_template": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "mark": "bar",
            "encoding": {}
        }
    },
    "bar_grouped": {
        "id": "bar_grouped",
        "name": "Grouped Bar",
        "icon": "bi-bar-chart-steps",
        "description": "Comparaciones agrupadas",
        "required_encodings": ["x", "y", "color"],
        "optional_encodings": ["column", "row"],
        "spec_template": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "mark": "bar",
            "encoding": {}
        },
        "post_processor": "grouped_bar"
    },
    "bar_stacked": {
        "id": "bar_stacked",
        "name": "Stacked Bar",
        "icon": "bi-bar-chart",
        "description": "Comparaciones apiladas",
        "required_encodings": ["x", "y", "color"],
        "optional_encodings": ["column", "row"],
        "spec_template": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "mark": "bar",
            "encoding": {}
        }
    },
    "histogram": {
        "id": "histogram",
        "name": "Histogram",
        "icon": "bi-bar-chart",
        "description": "Distribucion de frecuencias",
        "required_encodings": ["x"],
        "optional_encodings": ["color", "column", "row"],
        "spec_template": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "mark": "bar",
            "encoding": {}
        },
        "post_processor": "histogram"
    },
    "scatter": {
        "id": "scatter",
        "name": "Scatter",
        "icon": "bi-bullseye",
        "description": "Correlaciones entre variables",
        "required_encodings": ["x", "y"],
        "optional_encodings": ["color", "size", "shape", "column", "row"],
        "spec_template": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "mark": {"type": "point", "filled": True, "opacity": 0.7},
            "encoding": {}
        }
    },
    "heatmap": {
        "id": "heatmap",
        "name": "Heatmap",
        "icon": "bi-grid-3x3",
        "description": "Matrices y distribuciones 2D",
        "required_encodings": ["x", "y", "color"],
        "optional_encodings": ["column", "row"],
        "spec_template": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "mark": "rect",
            "encoding": {}
        },
        "post_processor": "heatmap_nominal"
    },
    "boxplot": {
        "id": "boxplot",
        "name": "Box Plot",
        "icon": "bi-box",
        "description": "Distribucion y outliers",
        "required_encodings": ["x", "y"],
        "optional_encodings": ["color", "column", "row"],
        "spec_template": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "mark": "boxplot",
            "encoding": {}
        },
        "post_processor": "boxplot_nominal"
    },
    "area": {
        "id": "area",
        "name": "Area",
        "icon": "bi-graph-down",
        "description": "Tendencias acumulativas",
        "required_encodings": ["x", "y"],
        "optional_encodings": ["color", "column", "row"],
        "spec_template": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "mark": {"type": "area", "opacity": 0.7},
            "encoding": {}
        }
    },
    "pie": {
        "id": "pie",
        "name": "Pie Chart",
        "icon": "bi-pie-chart",
        "description": "Proporciones y partes del todo",
        "required_encodings": ["theta", "color"],
        "optional_encodings": ["column", "row"],
        "spec_template": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "mark": "arc",
            "encoding": {}
        },
        "post_processor": "pie"
    },
    "us_map": {
        "id": "us_map",
        "name": "US Map",
        "icon": "bi-map",
        "description": "Mapa geográfico de USA",
        "required_encodings": ["latitude", "longitude", "color"],
        "optional_encodings": ["size"],
        "spec_template": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "width": 500,
            "height": 300,
            "layer": [
                {
                    "data": {
                        "url": "https://vega.github.io/vega-lite/data/us-10m.json",
                        "format": {
                            "type": "topojson",
                            "feature": "states"
                        }
                    },
                    "projection": {
                        "type": "albersUsa"
                    },
                    "mark": {
                        "type": "geoshape",
                        "fill": "lightgray",
                        "stroke": "white"
                    }
                },
                {
                    "projection": {
                        "type": "albersUsa"
                    },
                    "mark": "circle",
                    "encoding": {
                        "longitude": {},
                        "latitude": {},
                        "size": {},
                        "color": {}
                    }
                }
            ]
        },
        "post_processor": "us_map"
    },
    "world_map": {
        "id": "world_map",
        "name": "World Map",
        "icon": "bi-globe",
        "description": "Mapa geográfico mundial",
        "required_encodings": ["latitude", "longitude", "color"],
        "optional_encodings": ["size"],
        "spec_template": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "width": 600,
            "height": 350,
            "layer": [
                {
                    "data": {
                        "url": "https://vega.github.io/vega-lite/data/world-110m.json",
                        "format": {
                            "type": "topojson",
                            "feature": "countries"
                        }
                    },
                    "projection": {
                        "type": "equalEarth"
                    },
                    "mark": {
                        "type": "geoshape",
                        "fill": "lightgray",
                        "stroke": "white"
                    }
                },
                {
                    "projection": {
                        "type": "equalEarth"
                    },
                    "mark": "circle",
                    "encoding": {
                        "longitude": {},
                        "latitude": {},
                        "size": {},
                        "color": {}
                    }
                }
            ]
        },
        "post_processor": "world_map"
    },
    "linear_regression": {
        "id": "linear_regression",
        "name": "Linear Regression",
        "icon": "bi-graph-up",
        "description": "Regresión lineal y tendencia",
        "required_encodings": ["x", "y"],
        "optional_encodings": ["color", "size", "column"],
        "spec_template": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "layer": [
                {
                    "mark": "circle",
                    "encoding": {
                        "x": {},
                        "y": {},
                        "color": {},
                        "size": {}
                    }
                },
                {
                    "mark": {
                        "type": "line",
                        "color": "red"
                    },
                    "transform": [
                        {
                            "regression": "field1",
                            "on": "field2"
                        }
                    ],
                    "encoding": {
                        "x": {},
                        "y": {}
                    }
                }
            ]
        },
        "post_processor": "linear_regression"
    },
    "ranged_dot_plot": {
        "id": "ranged_dot_plot",
        "name": "Ranged Dot Plot",
        "icon": "bi-dash-lg",
        "description": "Rango de valores",
        "required_encodings": ["x", "y"],
        "optional_encodings": ["color"],
        "spec_template": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "encoding": {},
            "layer": [
                {
                    "mark": "line",
                    "encoding": {
                        "detail": {}
                    }
                },
                {
                    "mark": {
                        "type": "point",
                        "filled": True
                    },
                    "encoding": {
                        "color": {}
                    }
                }
            ]
        },
        "post_processor": "ranged_dot_plot"
    },
    "pyramid": {
        "id": "pyramid",
        "name": "Pyramid Chart",
        "icon": "bi-triangle",
        "description": "Estructura piramidal",
        "required_encodings": ["x", "y", "color"],
        "optional_encodings": ["column", "row"],
        "spec_template": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "spacing": 0,
            "resolve": {"scale": {"y": "shared"}},
            "hconcat": [
                {
                    "mark": "bar",
                    "encoding": {
                        "y": {},
                        "x": {"scale": {"reverse": True}, "stack": None},
                        "color": {"legend": None},
                        "opacity": {"value": 0.9}
                    }
                },
                {
                    "mark": "bar",
                    "encoding": {
                        "y": {"axis": None},
                        "x": {"stack": None},
                        "color": {"legend": None},
                        "opacity": {"value": 0.9}
                    }
                }
            ],
            "config": {
                "view": {"stroke": None},
                "axis": {"grid": False}
            }
        },
        "post_processor": "pyramid"
    },
    "custom_point": {
        "id": "custom_point",
        "name": "Custom Point",
        "icon": "bi-circle",
        "description": "Puntos con atributos personalizados",
        "required_encodings": ["x", "y"],
        "optional_encodings": ["color", "opacity", "size", "shape", "column", "row"],
        "spec_template": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "mark": "point",
            "encoding": {}
        }
    },
    "custom_line": {
        "id": "custom_line",
        "name": "Custom Line",
        "icon": "bi-slash-lg",
        "description": "Líneas con atributos personalizados",
        "required_encodings": ["x", "y"],
        "optional_encodings": ["color", "opacity", "detail", "column", "row"],
        "spec_template": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "mark": "line",
            "encoding": {}
        }
    },
    "custom_bar": {
        "id": "custom_bar",
        "name": "Custom Bar",
        "icon": "bi-bar-chart",
        "description": "Barras con atributos personalizados",
        "required_encodings": ["x", "y"],
        "optional_encodings": ["color", "opacity", "size", "shape", "column", "row"],
        "spec_template": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "mark": "bar",
            "encoding": {}
        }
    },
    "custom_rect": {
        "id": "custom_rect",
        "name": "Custom Rect",
        "icon": "bi-square",
        "description": "Rectángulos con rango X-Y",
        "required_encodings": ["x", "y"],
        "optional_encodings": ["x2", "y2", "color", "opacity", "column", "row"],
        "spec_template": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "mark": "rect",
            "encoding": {}
        }
    },
    "custom_area": {
        "id": "custom_area",
        "name": "Custom Area",
        "icon": "bi-triangle",
        "description": "Áreas con atributos personalizados",
        "required_encodings": ["x", "y"],
        "optional_encodings": ["x2", "y2", "color", "column", "row"],
        "spec_template": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "mark": "area",
            "encoding": {}
        }
    },
    "table": {
        "id": "table",
        "name": "Table",
        "icon": "bi-table",
        "description": "Vista tabulada de datos",
        "required_encodings": [],
        "optional_encodings": ["field1", "field2", "field3", "field4", "field5", "field6"],
        "spec_template": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "mark": "table",
            "encoding": {}
        }
    },
    "auto": {
        "id": "auto",
        "name": "Auto-Detect",
        "icon": "bi-magic",
        "description": "Detectar automaticamente el mejor tipo de gráfico",
        "required_encodings": [],
        "optional_encodings": ["x", "y", "color", "size"],
        "spec_template": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "mark": "line",
            "encoding": {}
        },
        "post_processor": "auto"
    }
}


# =============================================================================
# Helper Functions for Field Metadata and Semantic Types
# =============================================================================

def detect_semantic_type(field_name: str, df: pd.DataFrame = None, field_values: list = None) -> str:
    """
    Detect semantic type of a field based on name and content.
    Returns one of: geographic, temporal, currency, percentage, quantitative, categorical
    """
    field_lower = field_name.lower()
    
    # Check by name patterns first
    for stype, config in SEMANTIC_TYPES.items():
        if any(pattern in field_lower for pattern in config["patterns"]):
            return stype
    
    # Check by sample values if provided
    if df is not None and field_name in df.columns:
        try:
            sample = df[field_name].dropna().head(100)
            
            # Temporal detection
            if pd.api.types.is_datetime64_any_dtype(df[field_name]):
                return "temporal"
            
            # Check if values look like years
            if all(isinstance(v, (int, float)) and 1900 <= v <= 2100 for v in sample):
                return "temporal"
            
            # Percentage detection
            if all(isinstance(v, (int, float)) and 0 <= v <= 100 for v in sample):
                if any('%' in str(v) for v in df[field_name].astype(str)):
                    return "percentage"
            
            # Currency detection (if all values are > 100 and divisible)
            if all(isinstance(v, (int, float)) for v in sample) and len(sample) > 0:
                mean_val = sample.mean()
                if mean_val > 100:
                    return "currency"
        except:
            pass
    
    # Default based on cardinality
    if df is not None and field_name in df.columns:
        cardinality = df[field_name].nunique()
        if cardinality < 20:
            return "categorical"
    
    return "quantitative"


def get_semantic_hints(df: pd.DataFrame) -> dict:
    """
    Generate semantic type hints for all fields in a DataFrame.
    Returns dict mapping field -> {type, category}
    """
    hints = {}
    for col in df.columns:
        hints[col] = {
            "semantic_type": detect_semantic_type(col, df),
            "cardinality": df[col].nunique(),
            "dtype": str(df[col].dtype)
        }
    return hints


# =============================================================================
# Natural Language Instruction Processing
# =============================================================================

def process_nl_instruction(instruction: str, df: pd.DataFrame, spec: dict, encodings: dict) -> tuple:
    """
    Process natural language instructions to modify data and spec.
    Returns (modified_df, modified_spec, applied_transforms: list)
    
    Supported instructions:
    - "show/sort by descending/ascending" -> sort
    - "top N / bottom N" -> filter
    - "filter by X > N" -> filter
    - "only {field} in {values}" -> filter
    - "group by X" -> aggregate
    - "make it {color}" -> update color
    - "add title {text}" -> update title
    """
    result_df = df.copy()
    modified_spec = json.loads(json.dumps(spec))  # Deep copy
    applied = []
    
    instr_lower = instruction.lower()
    
    # Parse numeric values in instruction
    numbers = re.findall(r'\d+', instruction)
    
    # Sorting
    if 'descending' in instr_lower or 'descendente' in instr_lower:
        # Sort by Y field descending
        y_field = encodings.get('y', {}).get('field')
        if y_field and y_field in result_df.columns:
            result_df = result_df.sort_values(y_field, ascending=False)
            applied.append(f"Sorted by {y_field} descending")
    elif 'ascending' in instr_lower or 'ascendente' in instr_lower:
        y_field = encodings.get('y', {}).get('field')
        if y_field and y_field in result_df.columns:
            result_df = result_df.sort_values(y_field, ascending=True)
            applied.append(f"Sorted by {y_field} ascending")
    
    # Top N / Bottom N
    if ('top' in instr_lower or 'top' in instr_lower) and numbers:
        n = int(numbers[0])
        result_df = result_df.head(n)
        applied.append(f"Filtered to top {n} rows")
    elif ('bottom' in instr_lower or 'últim' in instr_lower) and numbers:
        n = int(numbers[0])
        result_df = result_df.tail(n)
        applied.append(f"Filtered to bottom {n} rows")
    
    # Color instructions
    color_map = {
        'rojo': '#d62728', 'red': '#d62728',
        'azul': '#1f77b4', 'blue': '#1f77b4',
        'verde': '#2ca02c', 'green': '#2ca02c',
        'amarillo': '#ff7f0e', 'orange': '#ff7f0e',
        'púrpura': '#9467bd', 'purple': '#9467bd',
        'gris': '#7f7f7f', 'gray': '#7f7f7f'
    }
    
    for color_name, color_hex in color_map.items():
        if color_name in instr_lower:
            if 'encoding' in modified_spec:
                # Update color encoding to fixed value
                modified_spec['encoding']['color'] = {'value': color_hex}
                applied.append(f"Changed color to {color_name}")
            break
    
    # Title instruction
    if 'title' in instr_lower:
        title_match = re.search(r'title["\s:]*([^".,\n]+)', instruction, re.IGNORECASE)
        if title_match:
            new_title = title_match.group(1).strip().strip('"\'')
            modified_spec['title'] = new_title
            applied.append(f"Updated title")
    
    return result_df, modified_spec, applied


# =============================================================================
# Performance Optimization
# =============================================================================

def should_sample_data(df: pd.DataFrame, threshold: int = 10000) -> bool:
    """Determine if data should be sampled for performance."""
    return len(df) > threshold


def compute_adaptive_sample_size(df: pd.DataFrame, encodings: dict, method: str = "auto") -> int:
    """
    Compute adaptive sample size based on data characteristics.
    
    Strategy:
    - For categorical X: min(rows, 500) to show all categories
    - For continuous X: min(rows, 1000) for line/scatter
    - For aggregated: min(rows, 5000) since aggregation reduces size
    - Default: min(rows, 2000)
    """
    if method == "auto":
        x_field = encodings.get('x', {}).get('field')
        y_field = encodings.get('y', {}).get('field')
        
        if x_field and x_field in df.columns:
            x_cardinality = df[x_field].nunique()
            # Low cardinality = categorical, keep most rows to preserve categories
            if x_cardinality < 100:
                return min(len(df), 1000)
        
        # High cardinality = continuous, can sample more
        return min(len(df), 2000)
    
    return min(len(df), 1000)


@lru_cache(maxsize=16)
def _hash_cache_key(data_hash: str, template: str, encodings_json: str) -> str:
    """Create cache key for chart specs."""
    return hashlib.md5(f"{data_hash}_{template}_{encodings_json}".encode()).hexdigest()


def adaptive_data_optimization(df: pd.DataFrame, encodings: dict, 
                               force_sampling: bool = False, sample_method: str = "auto") -> pd.DataFrame:
    """
    Apply adaptive optimization for large datasets.
    
    - Automatic sampling if > 10K rows
    - Stratified sampling for categorical fields
    - Temporal aggregation for time series
    """
    if not should_sample_data(df) and not force_sampling:
        return df
    
    result = df.copy()
    
    # For aggregated views, use aggregation instead of sampling
    color_field = encodings.get('color', {}).get('field')
    if color_field and color_field in df.columns:
        cardinality = df[color_field].nunique()
        if cardinality < 20:
            # Aggregate by color field
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                agg_dict = {col: 'sum' for col in numeric_cols}
                result = df.groupby(color_field, as_index=False).agg(agg_dict)
                return result
    
    # Standard sampling
    sample_size = compute_adaptive_sample_size(df, encodings, sample_method)
    if sample_method == "stratified":
        try:
            # Stratify by the most categorical field
            cat_field = None
            for col in [encodings.get('color', {}).get('field'), 
                       encodings.get('x', {}).get('field')]:
                if col and col in df.columns:
                    cardinality = df[col].nunique()
                    if cardinality < 100:
                        cat_field = col
                        break
            
            if cat_field:
                result = df.groupby(cat_field, group_keys=False).apply(
                    lambda x: x.sample(n=min(sample_size // max(df[cat_field].nunique(), 1), len(x)), random_state=42)
                ).head(sample_size)
            else:
                result = result.sample(n=sample_size, random_state=42)
        except:
            result = result.sample(n=sample_size, random_state=42)
    else:
        result = result.sample(n=sample_size, random_state=42)
    
    return result


def ensure_nominal_axis(spec: dict, data: list, default_to_x: bool = True) -> str | None:
    encoding = spec.get("encoding", {})
    if encoding.get("x", {}).get("type") == "nominal":
        return "x"
    if encoding.get("y", {}).get("type") == "nominal":
        return "y"

    x_field = encoding.get("x", {}).get("field")
    y_field = encoding.get("y", {}).get("field")

    if data and x_field and y_field:
        x_values = {row.get(x_field) for row in data}
        y_values = {row.get(y_field) for row in data}
        if len(x_values) <= len(y_values):
            encoding.setdefault("x", {})["type"] = "nominal"
            return "x"
        encoding.setdefault("y", {})["type"] = "nominal"
        return "y"

    if x_field:
        encoding.setdefault("x", {})["type"] = "nominal"
        return "x"
    if y_field:
        encoding.setdefault("y", {})["type"] = "nominal"
        return "y"

    if default_to_x:
        encoding.setdefault("x", {})["type"] = "nominal"
        return "x"
    encoding.setdefault("y", {})["type"] = "nominal"
    return "y"


def infer_field_type(df: pd.DataFrame, field: str) -> str:
    """Infer Vega-Lite field type from pandas dtype."""
    if field not in df.columns:
        return "nominal"
    
    dtype = df[field].dtype
    
    if pd.api.types.is_numeric_dtype(dtype):
        return "quantitative"
    elif pd.api.types.is_datetime64_any_dtype(dtype):
        return "temporal"
    elif field.lower() in ['year', 'año', 'fecha', 'date', 'month', 'mes']:
        # Common temporal field names
        return "temporal"
    else:
        # Check if numeric-like
        try:
            pd.to_numeric(df[field], errors='raise')
            return "quantitative"
        except:
            pass
        
        # Low cardinality = ordinal/nominal
        if df[field].nunique() < 20:
            return "nominal"
        return "nominal"


def build_vega_spec(template_id: str, encodings: dict, data: list = None,
                    title: str = None, width: int = 500, height: int = 300) -> dict:
    """
    Build a complete Vega-Lite spec from template and encodings.
    
    Args:
        template_id: One of the CHART_TEMPLATES keys
        encodings: Dict mapping channel -> {field, type, ...}
        data: Optional inline data
        title: Optional chart title
        width: Chart width
        height: Chart height
    
    Returns:
        Complete Vega-Lite specification
    """
    if template_id not in CHART_TEMPLATES:
        raise ValueError(f"Unknown template: {template_id}")
    
    template = CHART_TEMPLATES[template_id]
    spec = json.loads(json.dumps(template["spec_template"]))  # Deep copy
    
    # Add dimensions
    spec["width"] = width
    spec["height"] = height
    
    if title:
        spec["title"] = title
    
    # Add data if provided
    if data:
        spec["data"] = {"values": data}
    
    # Build encodings
    spec_encodings = {}
    
    for channel, enc_config in encodings.items():
        if not enc_config or not enc_config.get("field"):
            continue
        
        field = enc_config["field"]
        field_type = enc_config.get("type", "nominal")
        
        channel_spec = {
            "field": field,
            "type": field_type
        }
        
        # Add aggregation if specified
        if enc_config.get("aggregate"):
            channel_spec["aggregate"] = enc_config["aggregate"]
        
        # Add title if different from field name
        if enc_config.get("title"):
            channel_spec["title"] = enc_config["title"]
        
        # Add scale config
        if enc_config.get("scale"):
            channel_spec["scale"] = enc_config["scale"]
        
        # For temporal X axis, format nicely
        if channel == "x" and field_type == "temporal":
            channel_spec["axis"] = {"format": "%Y"}
        
        # For quantitative Y, format with commas
        if channel == "y" and field_type == "quantitative":
            channel_spec["axis"] = {"format": ",.2s"}
        
        spec_encodings[channel] = channel_spec
    
    spec["encoding"] = spec_encodings
    
    return spec


def apply_sampling_and_aggregation(df: pd.DataFrame, sample_method: str = None, 
                                   sample_size: int = None, aggregate_fields: list = None,
                                   aggregate_agg: str = "sum") -> pd.DataFrame:
    """
    Apply sampling and/or aggregation to a DataFrame.
    
    Args:
        df: Input DataFrame
        sample_method: "random", "head", "tail", or None (no sampling)
        sample_size: Number of rows to sample (if sample_method is set)
        aggregate_fields: List of fields to group by for aggregation
        aggregate_agg: Aggregation method ("sum", "mean", "count", "min", "max")
    
    Returns:
        Sampled and/or aggregated DataFrame
    """
    result = df.copy()
    
    # First apply aggregation if specified
    if aggregate_fields and len(aggregate_fields) > 0:
        valid_agg_fields = [f for f in aggregate_fields if f in result.columns]
        if valid_agg_fields:
            # Get numeric columns for aggregation
            numeric_cols = result.select_dtypes(include=['number']).columns.tolist()
            if numeric_cols:
                agg_dict = {col: aggregate_agg for col in numeric_cols}
                result = result.groupby(valid_agg_fields).agg(agg_dict).reset_index()
    
    # Then apply sampling if specified
    if sample_method and sample_size and len(result) > sample_size:
        if sample_method == "random":
            result = result.sample(n=min(sample_size, len(result)), random_state=42)
        elif sample_method == "head":
            result = result.head(sample_size)
        elif sample_method == "tail":
            result = result.tail(sample_size)
        elif sample_method == "stratified":
            # Simple stratified sampling: sample proportionally from groups
            # This is useful for categorical data
            try:
                # Try to stratify by the first nominal field
                for col in result.columns:
                    if result[col].dtype == 'object' or result[col].dtype.name == 'category':
                        n_samples = min(sample_size // result[col].nunique(), 1)
                        if n_samples > 0:
                            result = result.groupby(col, group_keys=False).apply(
                                lambda x: x.sample(n=min(n_samples, len(x)), random_state=42)
                            ).head(sample_size)
                            break
            except:
                # Fall back to random sampling
                result = result.sample(n=min(sample_size, len(result)), random_state=42)
    
    return result


def apply_post_processor(template_id: str, spec: dict, data: list) -> dict:
    """
    Apply template-specific post-processing to the Vega-Lite spec.
    
    Different chart types need special handling:
    - grouped_bar: Add xOffset/yOffset for color encoding
    - histogram: Ensure bin transform on X, add count to Y
    - heatmap_nominal: Force both axes to nominal
    - boxplot_nominal: Ensure one nominal axis
    - pie: Add theta aggregation
    - linear_regression: Setup regression layer
    - ranged_dot_plot: Add detail to line layer
    - pyramid: Filter and configure dual-sided bars
    - us_map/world_map: Configure layer encoding
    """
    template = CHART_TEMPLATES.get(template_id, {})
    processor = template.get("post_processor")

    if processor == "grouped_bar":
        if spec.get("encoding", {}).get("color", {}).get("field"):
            nominal_channel = ensure_nominal_axis(spec, data, True)
            offset_channel = "xOffset" if nominal_channel == "x" else "yOffset" if nominal_channel == "y" else None
            if offset_channel:
                spec["encoding"].setdefault(offset_channel, {})
                spec["encoding"][offset_channel]["field"] = spec["encoding"]["color"]["field"]
                spec["encoding"][offset_channel]["type"] = "nominal"
        return spec

    if processor == "histogram":
        if spec.get("encoding", {}).get("x"):
            spec["encoding"]["x"].setdefault("bin", True)
        if "y" not in spec.get("encoding", {}) or not spec["encoding"]["y"].get("field"):
            spec["encoding"].setdefault("y", {})
            spec["encoding"]["y"].update({"aggregate": "count", "type": "quantitative"})
        return spec

    if processor == "heatmap_nominal":
        if spec.get("encoding", {}).get("x"):
            spec["encoding"]["x"]["type"] = "nominal"
        if spec.get("encoding", {}).get("y"):
            spec["encoding"]["y"]["type"] = "nominal"
        return spec

    if processor == "boxplot_nominal":
        ensure_nominal_axis(spec, data, True)
        return spec

    if processor == "pie":
        # Pie chart: keep only theta/color and aggregate to reduce clutter
        encoding = spec.get("encoding", {})
        theta_field = encoding.get("theta", {}).get("field")
        color_field = encoding.get("color", {}).get("field")

        # Remove non-pie encodings that can distort arcs
        for channel in list(encoding.keys()):
            if channel not in ["theta", "color", "tooltip"]:
                encoding.pop(channel, None)

        if theta_field:
            encoding["theta"].setdefault("aggregate", "sum")
            encoding["theta"].setdefault("type", "quantitative")

        if color_field:
            encoding["color"].setdefault("type", "nominal")

        # Aggregate + limit to top categories to avoid unreadable pies
        if theta_field and color_field:
            spec.setdefault("transform", [])
            spec["transform"].extend([
                {
                    "aggregate": [{"op": "sum", "field": theta_field, "as": "__pie_value"}],
                    "groupby": [color_field]
                },
                {
                    "window": [{"op": "rank", "as": "__pie_rank"}],
                    "sort": [{"field": "__pie_value", "order": "descending"}]
                },
                {"filter": "datum.__pie_rank <= 10"}
            ])
            encoding["theta"]["field"] = "__pie_value"
        return spec

    if processor == "linear_regression":
        # Update regression layer with actual field names
        if spec.get("layer"):
            y_field = spec.get("encoding", {}).get("y", {}).get("field")
            x_field = spec.get("encoding", {}).get("x", {}).get("field")
            
            if len(spec["layer"]) > 1 and y_field and x_field:
                # Update regression transform
                if "transform" in spec["layer"][1]:
                    spec["layer"][1]["transform"][0]["regression"] = y_field
                    spec["layer"][1]["transform"][0]["on"] = x_field
        return spec

    if processor == "ranged_dot_plot":
        # For ranged dot plot, copy y encoding to detail channel in line layer
        if spec.get("encoding", {}).get("y", {}).get("field"):
            if spec.get("layer"):
                y_field = spec["encoding"]["y"]["field"]
                if len(spec["layer"]) > 0:
                    spec["layer"][0]["encoding"]["detail"] = {
                        "field": y_field,
                        "type": spec["encoding"]["y"].get("type", "nominal")
                    }
        return spec

    if processor == "pyramid":
        # Pyramid: Configure split bars
        if spec.get("hconcat") and data and len(data) > 0:
            color_field = spec.get("encoding", {}).get("color", {}).get("field")
            x_field = spec.get("encoding", {}).get("x", {}).get("field")
            
            if color_field:
                color_values = sorted(list({row.get(color_field) for row in data if color_field in row}))
                if len(color_values) >= 2:
                    # Left side: first color value
                    spec["hconcat"][0]["transform"] = [
                        {"filter": f'datum["{color_field}"] == "{color_values[0]}"'}
                    ]
                    spec["hconcat"][0]["title"] = str(color_values[0])
                    spec["hconcat"][0]["encoding"]["color"]["legend"] = None
                    
                    # Right side: second color value
                    spec["hconcat"][1]["transform"] = [
                        {"filter": f'datum["{color_field}"] == "{color_values[1]}"'}
                    ]
                    spec["hconcat"][1]["title"] = str(color_values[1])
                    spec["hconcat"][1]["encoding"]["color"]["legend"] = None
        return spec

    if processor == "us_map":
        # US Map: Configure layer 1 (points) with lat/long encoding
        if spec.get("layer") and len(spec["layer"]) > 1:
            layer_1_enc = spec["layer"][1].get("encoding", {})
            # Clone encodings from main spec to layer 1
            for channel in ["longitude", "latitude", "size", "color"]:
                if channel in spec.get("encoding", {}):
                    layer_1_enc[channel] = spec["encoding"][channel]
            # Remove from main spec encoding
            for channel in ["longitude", "latitude", "size", "color"]:
                spec["encoding"].pop(channel, None)
        return spec

    if processor == "world_map":
        # World Map: Configure layer 1 (points) with lat/long encoding
        if spec.get("layer") and len(spec["layer"]) > 1:
            layer_1_enc = spec["layer"][1].get("encoding", {})
            # Clone encodings from main spec to layer 1
            for channel in ["longitude", "latitude", "size", "color"]:
                if channel in spec.get("encoding", {}):
                    layer_1_enc[channel] = spec["encoding"][channel]
            # Remove from main spec encoding
            for channel in ["longitude", "latitude", "size", "color"]:
                spec["encoding"].pop(channel, None)
        return spec

    if processor == "auto":
        # Auto-detect best template based on encodings and data
        # For now, default to line chart but could be enhanced with ML detection
        spec["mark"] = "line"
        return spec

    return spec


# =============================================================================
# API Endpoints
# =============================================================================

@api_bp.route('/viz/templates', methods=['GET'])
def get_chart_templates():
    """
    List available chart templates.
    
    Returns:
        List of template metadata (id, name, icon, description, required/optional encodings)
    """
    templates = []
    for tid, t in CHART_TEMPLATES.items():
        templates.append({
            "id": t["id"],
            "name": t["name"],
            "icon": t["icon"],
            "description": t["description"],
            "required_encodings": t["required_encodings"],
            "optional_encodings": t["optional_encodings"]
        })
    
    return jsonify({
        "status": "ok",
        "templates": templates
    })


@api_bp.route('/viz/generate-chart', methods=['POST'])
def generate_chart():
    """
    Generate a Vega-Lite chart specification.
    
    Expected JSON:
    {
        "template": "line",
        "encodings": {
            "x": {"field": "year", "type": "temporal"},
            "y": {"field": "gdp", "type": "quantitative"},
            "color": {"field": "country", "type": "nominal"}
        },
        "data": [{"year": 2020, "gdp": 500, "country": "Argentina"}, ...],
        "title": "PIB por País",
        "width": 600,
        "height": 400,
        "sample_method": "random",  // Optional: "random", "head", "tail", "stratified", "auto"
        "sample_size": 500,         // Optional: max rows to keep
        "aggregate_fields": [],     // Optional: fields to group by
        "aggregate_agg": "sum",     // Optional: aggregation method
        "nl_instruction": "mostrar solo top 5 países"  // Optional NL refinement
    }
    
    Returns:
        Vega-Lite specification with semantic hints and applied transforms
    """
    try:
        data = request.get_json()
        
        template_id = data.get("template", "line")
        encodings = data.get("encodings", {})
        chart_data = data.get("data")
        title = data.get("title")
        width = data.get("width", 500)
        height = data.get("height", 300)
        nl_instruction = data.get("nl_instruction", "")
        
        # Sampling and aggregation parameters
        sample_method = data.get("sample_method")
        sample_size = data.get("sample_size")
        aggregate_fields = data.get("aggregate_fields", [])
        aggregate_agg = data.get("aggregate_agg", "sum")
        
        applied_transforms = []
        
        # If data provided as DataFrame-like, apply optimization and infer types
        if chart_data and isinstance(chart_data, list) and len(chart_data) > 0:
            df = pd.DataFrame(chart_data)
            semantic_hints = get_semantic_hints(df)
            
            # Performance optimization: Adaptive sampling for large datasets
            if should_sample_data(df):
                sample_method_to_use = sample_method or "auto"
                df = adaptive_data_optimization(df, encodings, force_sampling=False, sample_method=sample_method_to_use)
                applied_transforms.append(f"Applied adaptive sampling ({len(df)} rows)")
            
            # Apply sampling and aggregation from user parameters
            if sample_method or aggregate_fields:
                df = apply_sampling_and_aggregation(
                    df, 
                    sample_method=sample_method,
                    sample_size=sample_size,
                    aggregate_fields=aggregate_fields,
                    aggregate_agg=aggregate_agg
                )
            
            # Auto-detect encodings if not provided
            if not encodings or (len(encodings) == 0 or not any(enc and enc.get("field") for enc in encodings.values())):
                auto_enc = auto_detect_encodings(df, template_id)
                encodings.update(auto_enc)
                applied_transforms.append(f"Auto-detected encodings: {', '.join(encodings.keys())}")
            
            # Convert back to list for Vega (cleaned)
            chart_data = dataframe_to_json_records(df)
            
            # Auto-infer types for encodings without explicit type
            for channel, enc in encodings.items():
                if enc and enc.get("field") and not enc.get("type"):
                    enc["type"] = infer_field_type(df, enc["field"])

        # Validate required encodings after auto-detection
        if template_id in CHART_TEMPLATES:
            required = CHART_TEMPLATES[template_id]["required_encodings"]
            missing = [r for r in required if r not in encodings or not encodings[r].get("field")]
            if missing:
                return jsonify({
                    "status": "error",
                    "message": f"Missing required encodings: {', '.join(missing)}"
                }), 400
        
        # Build the spec
        spec = build_vega_spec(
            template_id=template_id,
            encodings=encodings,
            data=chart_data,
            title=title,
            width=width,
            height=height
        )

        spec = apply_post_processor(template_id, spec, chart_data or [])
        
        # Process NL instructions to refine data/spec
        if nl_instruction and nl_instruction.strip():
            modified_df = pd.DataFrame(chart_data) if chart_data else pd.DataFrame()
            if len(modified_df) > 0:
                modified_df, spec, nl_transforms = process_nl_instruction(
                    nl_instruction, modified_df, spec, encodings
                )
                applied_transforms.extend(nl_transforms)
                # Update spec data with modified dataframe
                if len(modified_df) > 0:
                    spec["data"]["values"] = dataframe_to_json_records(modified_df)
        
        response = {
            "status": "ok",
            "spec": spec,
            "template": template_id,
            "encodings": encodings,
            "applied_transforms": applied_transforms
        }
        
        # Include semantic hints if available
        if chart_data and isinstance(chart_data, list) and len(chart_data) > 0:
            df = pd.DataFrame(chart_data)
            response["semantic_hints"] = get_semantic_hints(df)
        
        return jsonify(response)
        
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route('/viz/derive-field', methods=['POST'])
def derive_field():
    """
    Derive a new field using natural language description.
    
    Expected JSON:
    {
        "rows": [...],
        "field_name": "growth_rate",
        "source_fields": ["year", "gdp"],
        "description": "Calcular tasa de crecimiento anual del PIB",
        "preview_only": true  // If true, only return preview, don't persist
    }
    
    Returns:
        Generated code, preview of new column values
    """
    try:
        data = request.get_json()
        
        rows = data.get("rows")
        field_name = data.get("field_name", "derived_field")
        source_fields = data.get("source_fields", [])
        description = data.get("description", "")
        preview_only = data.get("preview_only", True)
        
        if not rows:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400
        
        if not description:
            return jsonify({
                "status": "error",
                "message": "Description is required"
            }), 400
        
        df = pd.DataFrame(rows)
        
        # For now, implement common derivations without AI
        # In future, use LLM to generate pandas code
        
        code = None
        result_df = df.copy()
        error = None
        
        # Simple pattern matching for common operations
        desc_lower = description.lower()
        
        try:
            if any(w in desc_lower for w in ['crecimiento', 'growth', 'cambio porcentual', 'pct_change']):
                # Percentage change
                if source_fields:
                    target_col = source_fields[0]
                    if target_col in df.columns:
                        result_df[field_name] = df[target_col].pct_change() * 100
                        code = f"df['{field_name}'] = df['{target_col}'].pct_change() * 100"
            
            elif any(w in desc_lower for w in ['ranking', 'rank', 'posición']):
                # Ranking
                if source_fields:
                    target_col = source_fields[0]
                    if target_col in df.columns:
                        ascending = 'menor' in desc_lower or 'ascending' in desc_lower
                        # Handle NaN values by using method='first' and keeping NaN
                        result_df[field_name] = df[target_col].rank(ascending=ascending, na_option='keep')
                        code = f"df['{field_name}'] = df['{target_col}'].rank(ascending={ascending}, na_option='keep')"
            
            elif any(w in desc_lower for w in ['media móvil', 'moving average', 'promedio móvil', 'rolling']):
                # Rolling average
                window = 3
                for w in [3, 5, 7, 10]:
                    if str(w) in description:
                        window = w
                        break
                
                if source_fields:
                    target_col = source_fields[0]
                    if target_col in df.columns:
                        result_df[field_name] = df[target_col].rolling(window=window).mean()
                        code = f"df['{field_name}'] = df['{target_col}'].rolling(window={window}).mean()"
            
            elif any(w in desc_lower for w in ['suma', 'sum', 'total']):
                # Sum of fields
                if len(source_fields) >= 2:
                    cols_in_df = [c for c in source_fields if c in df.columns]
                    if cols_in_df:
                        result_df[field_name] = df[cols_in_df].sum(axis=1)
                        code = f"df['{field_name}'] = df[{cols_in_df}].sum(axis=1)"
            
            elif any(w in desc_lower for w in ['diferencia', 'difference', 'resta']):
                # Difference between two fields
                if len(source_fields) >= 2:
                    if source_fields[0] in df.columns and source_fields[1] in df.columns:
                        result_df[field_name] = df[source_fields[0]] - df[source_fields[1]]
                        code = f"df['{field_name}'] = df['{source_fields[0]}'] - df['{source_fields[1]}']"
            
            elif any(w in desc_lower for w in ['ratio', 'proporción', 'dividir', 'porcentaje de']):
                # Ratio/division
                if len(source_fields) >= 2:
                    if source_fields[0] in df.columns and source_fields[1] in df.columns:
                        result_df[field_name] = (df[source_fields[0]] / df[source_fields[1]]) * 100
                        code = f"df['{field_name}'] = (df['{source_fields[0]}'] / df['{source_fields[1]}']) * 100"
            
            elif any(w in desc_lower for w in ['log', 'logaritmo']):
                # Log transform
                import numpy as np
                if source_fields:
                    target_col = source_fields[0]
                    if target_col in df.columns:
                        result_df[field_name] = np.log(df[target_col].replace(0, np.nan))
                        code = f"df['{field_name}'] = np.log(df['{target_col}'].replace(0, np.nan))"
            
            else:
                # Fallback: Try to use AI agent for transform
                from src.agents import DataTransformAgent, create_table_context
                
                agent = DataTransformAgent(language="es")
                table_ctx = create_table_context(df, "data", "")
                
                goal = f"Crear una nueva columna llamada '{field_name}' que: {description}"
                response = agent.transform(goal, [table_ctx], execute=True)
                
                if response.status == "ok" and response.result_data is not None:
                    result_df = response.result_data
                    code = response.code
                elif response.code:
                    code = response.code
                    error = response.error or "Could not execute code"
                else:
                    error = "Could not generate transformation code"
        
        except Exception as e:
            error = str(e)
        
        # Prepare preview (first 5 rows with new field)
        if field_name in result_df.columns:
            preview_cols = source_fields + [field_name] if source_fields else [field_name]
            preview_cols = [c for c in preview_cols if c in result_df.columns]
            # Replace NaN with None for JSON compatibility
            preview_df = result_df[preview_cols].head(5).fillna(value='null')
            preview_df = result_df[preview_cols].head(5)
            preview = preview_df.where(pd.notna(preview_df), None).to_dict(orient="records")
        else:
            preview = []
        
        response = {
            "status": "ok" if code and not error else "error",
            "field_name": field_name,
            "code": code,
            "preview": preview,
        }
        
        if error:
            response["error"] = error
        
        if not preview_only and field_name in result_df.columns:
            # Replace NaN for JSON compatibility
            result_clean = result_df.where(pd.notna(result_df), None)
            response["result"] = result_clean.to_dict(orient="records")
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route('/viz/infer-types', methods=['POST'])
def infer_field_types():
    """
    Infer Vega-Lite types for fields in a dataset.
    
    Expected JSON:
    {
        "rows": [...],
        "fields": ["year", "gdp", "country"]  // Optional, defaults to all columns
    }
    
    Returns:
        Mapping of field -> inferred type
    """
    try:
        data = request.get_json()
        
        rows = data.get("rows")
        fields = data.get("fields")
        
        if not rows:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400
        
        df = pd.DataFrame(rows)
        
        if not fields:
            fields = list(df.columns)
        
        type_map = {}
        for field in fields:
            if field in df.columns:
                type_map[field] = infer_field_type(df, field)
        
        return jsonify({
            "status": "ok",
            "types": type_map
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route('/viz/semantic-hints', methods=['POST'])
def get_semantic_hints_endpoint():
    """
    Get semantic type hints for fields in a dataset.
    This provides more detailed metadata than simple type inference.
    
    Expected JSON:
    {
        "rows": [...]
    }
    
    Returns:
        Field metadata including semantic types, cardinality, and pandas dtype
    """
    try:
        data = request.get_json()
        rows = data.get("rows")
        
        if not rows:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400
        
        df = pd.DataFrame(rows)
        hints = get_semantic_hints(df)
        
        return jsonify({
            "status": "ok",
            "semantic_hints": hints
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route('/viz/semantic-types', methods=['GET'])
def get_semantic_types():
    """
    Get available semantic types and their patterns.
    Useful for UI hints and field classification.
    
    Returns:
        Dictionary of semantic type -> {patterns, description}
    """
    return jsonify({
        "status": "ok",
        "semantic_types": SEMANTIC_TYPES
    })

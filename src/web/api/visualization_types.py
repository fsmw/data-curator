"""Semantic typing and encoding helpers for visualization endpoints."""

import pandas as pd


SEMANTIC_TYPES = {
    "geographic": {
        "patterns": [
            "lat",
            "long",
            "longitude",
            "latitude",
            "country",
            "state",
            "province",
            "region",
        ],
        "description": "Geographic coordinate or region",
    },
    "temporal": {
        "patterns": ["year", "date", "month", "day", "time", "quarter", "trim"],
        "description": "Time or date field",
    },
    "currency": {
        "patterns": ["price", "cost", "salary", "gdp", "income", "revenue"],
        "description": "Monetary value",
    },
    "percentage": {
        "patterns": ["pct", "percent", "%", "rate", "ratio"],
        "description": "Percentage or proportion",
    },
    "categorical": {
        "patterns": ["id", "code", "category", "type"],
        "description": "Category or grouping field",
    },
}


def detect_semantic_type(
    field_name: str, df: pd.DataFrame | None = None, field_values: list | None = None
) -> str:
    """Detect semantic type by field name and sample values."""
    field_lower = field_name.lower()

    for stype, config in SEMANTIC_TYPES.items():
        if any(pattern in field_lower for pattern in config["patterns"]):
            return stype

    if df is not None and field_name in df.columns:
        try:
            sample = df[field_name].dropna().head(100)

            if pd.api.types.is_datetime64_any_dtype(df[field_name]):
                return "temporal"

            if all(isinstance(v, (int, float)) and 1900 <= v <= 2100 for v in sample):
                return "temporal"

            if all(isinstance(v, (int, float)) and 0 <= v <= 100 for v in sample):
                if any("%" in str(v) for v in df[field_name].astype(str)):
                    return "percentage"

            if all(isinstance(v, (int, float)) for v in sample) and len(sample) > 0:
                if sample.mean() > 100:
                    return "currency"
        except (TypeError, ValueError):
            pass

    if df is not None and field_name in df.columns:
        if df[field_name].nunique() < 20:
            return "categorical"

    return "quantitative"


def get_semantic_hints(df: pd.DataFrame) -> dict:
    """Generate semantic metadata hints for all DataFrame fields."""
    hints = {}
    for col in df.columns:
        hints[col] = {
            "semantic_type": detect_semantic_type(col, df),
            "cardinality": df[col].nunique(),
            "dtype": str(df[col].dtype),
        }
    return hints


def infer_field_type(df: pd.DataFrame, field: str) -> str:
    """Infer Vega-Lite field type from pandas dtype."""
    if field not in df.columns:
        return "nominal"

    dtype = df[field].dtype
    if pd.api.types.is_numeric_dtype(dtype):
        return "quantitative"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "temporal"
    if field.lower() in ["year", "año", "fecha", "date", "month", "mes"]:
        return "temporal"

    try:
        pd.to_numeric(df[field], errors="raise")
        return "quantitative"
    except (ValueError, TypeError):
        pass

    return "nominal"


def auto_detect_encodings(df: pd.DataFrame, template_id: str | None = None) -> dict:
    """Auto-detect x/y/color/theta encodings from field semantics and dtypes."""
    encodings = {}
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

    if template_id == "pie":
        preferred_category = None
        if categorical_fields:
            category_scores = []
            for col in categorical_fields:
                try:
                    category_scores.append((df[col].nunique(dropna=True), col))
                except (TypeError, ValueError):
                    category_scores.append((float("inf"), col))
            category_scores.sort(key=lambda x: x[0])
            preferred_category = category_scores[0][1] if category_scores else None

        if numeric_fields and preferred_category:
            encodings["theta"] = {"field": numeric_fields[0], "type": "quantitative"}
            encodings["color"] = {"field": preferred_category, "type": "nominal"}
        elif preferred_category:
            encodings["theta"] = {
                "field": preferred_category,
                "type": "quantitative",
                "aggregate": "count",
            }
            encodings["color"] = {"field": preferred_category, "type": "nominal"}
        return encodings

    if temporal_fields:
        encodings["x"] = {"field": temporal_fields[0], "type": "temporal"}
    elif categorical_fields:
        encodings["x"] = {"field": categorical_fields[0], "type": "nominal"}
    elif numeric_fields:
        encodings["x"] = {"field": numeric_fields[0], "type": "quantitative"}

    if numeric_fields and encodings.get("x", {}).get("field") != numeric_fields[0]:
        encodings["y"] = {"field": numeric_fields[0], "type": "quantitative"}
    elif numeric_fields and "y" not in encodings:
        encodings["y"] = {"field": numeric_fields[0], "type": "quantitative"}
    elif categorical_fields and encodings.get("x", {}).get("field") != categorical_fields[0]:
        encodings["y"] = {"field": categorical_fields[0], "type": "nominal"}

    for col in categorical_fields:
        if col != encodings.get("x", {}).get("field"):
            encodings["color"] = {"field": col, "type": "nominal"}
            break

    if template_id == "scatter" and len(numeric_fields) >= 2:
        encodings["x"] = {"field": numeric_fields[0], "type": "quantitative"}
        encodings["y"] = {"field": numeric_fields[1], "type": "quantitative"}
        if categorical_fields:
            encodings["color"] = {"field": categorical_fields[0], "type": "nominal"}
    elif template_id == "heatmap" and len(categorical_fields) >= 2 and numeric_fields:
        encodings["x"] = {"field": categorical_fields[0], "type": "nominal"}
        encodings["y"] = {"field": categorical_fields[1], "type": "nominal"}
        encodings["color"] = {"field": numeric_fields[0], "type": "quantitative"}

    return encodings

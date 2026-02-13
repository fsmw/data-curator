"""
Agent Utilities for Mises Data Curator.

Provides shared utility functions for all agents, inspired by 
Data Formulator's agent_utils.py patterns.

Key functions:
- generate_data_summary: Create structured summaries for LLM context
- extract_code_from_response: Parse code blocks from LLM responses
- extract_json_objects: Parse JSON from LLM responses
- get_field_summary: Summarize a single data column
"""

import json
import re
import keyword
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# Variable Name Utilities
# =============================================================================

def string_to_py_varname(var_str: str) -> str:
    """
    Convert a string to a valid Python variable name.
    
    Args:
        var_str: Input string (e.g., "My Column Name")
        
    Returns:
        Valid Python variable name (e.g., "my_column_name")
    """
    var_name = re.sub(r'\W|^(?=\d)', '_', var_str)
    if keyword.iskeyword(var_name):
        var_name = f"__{var_name}"
    return var_name.lower()


def field_name_to_variable(field_name: str) -> str:
    """
    Convert a field name to a camelCase variable name.
    
    Args:
        field_name: Column/field name
        
    Returns:
        CamelCase variable name
    """
    if field_name.strip() == "":
        return "inp"
    clean_name = re.sub('[^A-Za-z0-9]+', ' ', field_name)
    clean_name = re.sub(' +', ' ', clean_name)
    var_name = ''.join(x for x in clean_name.title() if not x.isspace())
    if var_name:
        var_name = var_name[0].lower() + var_name[1:]
    return var_name


# =============================================================================
# Response Parsing Utilities
# =============================================================================

def extract_code_from_response(response: str, language: str = "python") -> List[str]:
    """
    Extract code blocks from LLM response.
    
    Searches for code blocks wrapped in ```language ... ``` markers.
    
    Args:
        response: Raw LLM response text
        language: Programming language to extract (python, sql, etc.)
        
    Returns:
        List of code strings found
    """
    # Find positions of opening markers
    prefix_pattern = re.compile(f"```{language}", re.IGNORECASE)
    prefix_positions = [m.span()[0] for m in prefix_pattern.finditer(response)]
    
    # Find all ``` markers
    all_markers = [m.span() for m in re.compile("```").finditer(response)]
    
    results = []
    for i in range(len(all_markers) - 1):
        # Check if this is an opening marker for our language
        if all_markers[i][0] in prefix_positions:
            # Check if next marker is a closing one (not another opening)
            if all_markers[i+1][0] not in prefix_positions:
                start = all_markers[i][1]  # End of opening marker
                end = all_markers[i+1][0]  # Start of closing marker
                
                code = response[start:end]
                # Remove the language identifier line if present
                if code.startswith(language):
                    code = code[len(language):]
                code = code.strip()
                
                if code:
                    results.append(code)
    
    return results


def find_matching_bracket(text: str, start_index: int, bracket_type: str = 'curly') -> int:
    """
    Find the matching closing bracket for JSON parsing.
    
    Args:
        text: Text to search in
        start_index: Position of opening bracket
        bracket_type: 'curly' for {} or 'square' for []
        
    Returns:
        Index of matching closing bracket, or -1 if not found
    """
    if bracket_type == 'curly':
        open_bracket, close_bracket = '{', '}'
    elif bracket_type == 'square':
        open_bracket, close_bracket = '[', ']'
    else:
        raise ValueError("bracket_type must be 'curly' or 'square'")
    
    stack = []
    in_string = False
    escape_next = False
    
    for index in range(start_index, len(text)):
        char = text[index]
        
        if escape_next:
            escape_next = False
            continue
        
        if char == '\\':
            escape_next = True
            continue
        
        if char == '"':
            in_string = not in_string
            continue
        
        if in_string:
            continue
        
        if char == open_bracket:
            stack.append(char)
        elif char == close_bracket:
            if not stack:
                return -1
            stack.pop()
            if not stack:
                return index
    
    return -1


def extract_json_objects(text: str) -> List[Dict]:
    """
    Extract JSON objects and arrays from text.
    
    Robust parser that handles JSON embedded in natural language.
    
    Args:
        text: Text containing JSON objects
        
    Returns:
        List of parsed JSON objects/arrays
    """
    json_objects = []
    start_index = 0
    
    while True:
        # Find next JSON start
        object_start = text.find('{', start_index)
        array_start = text.find('[', start_index)
        
        if object_start == -1 and array_start == -1:
            break
        
        # Determine which comes first
        if object_start == -1:
            start_index = array_start
            bracket_type = 'square'
        elif array_start == -1:
            start_index = object_start
            bracket_type = 'curly'
        else:
            if object_start < array_start:
                start_index = object_start
                bracket_type = 'curly'
            else:
                start_index = array_start
                bracket_type = 'square'
        
        # Find matching end
        end_index = find_matching_bracket(text, start_index, bracket_type)
        
        if end_index == -1:
            start_index += 1
            continue
        
        json_str = text[start_index:end_index + 1]
        
        try:
            json_obj = json.loads(json_str)
            json_objects.append(json_obj)
        except json.JSONDecodeError:
            pass
        
        start_index = end_index + 1
    
    return json_objects


# =============================================================================
# Data Summary Utilities
# =============================================================================

def get_field_summary(
    field_name: str, 
    df: pd.DataFrame, 
    sample_size: int = 7,
    max_val_chars: int = 100
) -> str:
    """
    Generate a summary string for a single field/column.
    
    Args:
        field_name: Column name
        df: DataFrame containing the column
        sample_size: Number of sample values to show
        max_val_chars: Maximum characters per value
        
    Returns:
        Summary string like "country -- type: object, values: Argentina, Brasil, ..."
    """
    if field_name not in df.columns:
        return f"{field_name} -- (not found in data)"
    
    dtype = df[field_name].dtype
    
    # For numeric types, show range
    if pd.api.types.is_numeric_dtype(dtype):
        non_null = df[field_name].dropna()
        if len(non_null) > 0:
            min_val = non_null.min()
            max_val = non_null.max()
            return f"{field_name} -- tipo: {dtype}, rango: [{min_val}, {max_val}]"
        else:
            return f"{field_name} -- tipo: {dtype}, valores: (todos nulos)"
    
    # For other types, show sample values
    try:
        # Get unique values, handling unhashable types
        def make_hashable(val):
            if val is None or pd.isna(val):
                return None
            if isinstance(val, (list, dict)):
                return str(val)
            return val
        
        unique_vals = df[field_name].dropna().apply(make_hashable).unique()
        
        # Sort if possible
        try:
            unique_vals = sorted([v for v in unique_vals if v is not None])
        except TypeError:
            unique_vals = [v for v in unique_vals if v is not None]
        
    except Exception:
        unique_vals = []
    
    # Format sample values
    if len(unique_vals) == 0:
        val_str = "(sin valores)"
    elif len(unique_vals) <= sample_size:
        val_str = ", ".join(_truncate_value(str(v), max_val_chars) for v in unique_vals)
    else:
        # Show first and last values with ellipsis
        half = sample_size // 2
        first_vals = unique_vals[:half]
        last_vals = unique_vals[-(sample_size - half):]
        val_str = ", ".join(_truncate_value(str(v), max_val_chars) for v in first_vals)
        val_str += ", ..., "
        val_str += ", ".join(_truncate_value(str(v), max_val_chars) for v in last_vals)
    
    return f"{field_name} -- tipo: {dtype}, valores: {val_str}"


def _truncate_value(val: str, max_chars: int) -> str:
    """Truncate a value string and escape if needed."""
    if len(val) > max_chars:
        val = val[:max_chars] + "..."
    if ',' in val:
        val = f'"{val}"'
    return val


def generate_data_summary(
    input_tables: List[Dict[str, Any]],
    include_samples: bool = True,
    sample_size: int = 5,
    field_sample_size: int = 7,
    max_val_chars: int = 100,
    language: str = "es"
) -> str:
    """
    Generate a comprehensive summary of input tables for LLM context.
    
    This is the main function used by agents to describe data to the LLM.
    
    Args:
        input_tables: List of table dicts with 'name' and 'rows' keys
        include_samples: Whether to include sample data rows
        sample_size: Number of sample rows to show
        field_sample_size: Number of sample values per field
        max_val_chars: Max characters per sample value
        language: 'es' for Spanish labels, 'en' for English
        
    Returns:
        Markdown-formatted summary string
        
    Example input:
        [{"name": "pib_latam", "rows": [{"country": "Argentina", "year": 2020, ...}, ...]}]
    """
    if language == "es":
        labels = {
            "table": "Tabla",
            "rows": "filas",
            "columns": "columnas",
            "description": "Descripción",
            "schema": "Esquema",
            "fields": "campos",
            "sample": "Datos de Muestra",
            "first": "primeras"
        }
    else:
        labels = {
            "table": "Table",
            "rows": "rows",
            "columns": "columns",
            "description": "Description",
            "schema": "Schema",
            "fields": "fields",
            "sample": "Sample Data",
            "first": "first"
        }
    
    summaries = []
    
    for idx, table in enumerate(input_tables):
        name = table.get("name", f"tabla_{idx + 1}")
        rows = table.get("rows", [])
        description = table.get("description", table.get("attached_metadata", ""))
        
        # Create DataFrame
        df = pd.DataFrame(rows) if rows else pd.DataFrame()
        num_rows = len(df)
        num_cols = len(df.columns) if not df.empty else 0
        
        sections = []
        
        # Header
        header = f"## {labels['table']} {idx + 1}: {name}"
        if num_rows > 0:
            header += f" ({num_rows:,} {labels['rows']} × {num_cols} {labels['columns']})"
        sections.append(header)
        sections.append("")
        
        # Description
        if description:
            sections.append(f"### {labels['description']}\n{description}\n")
        
        # Schema
        if not df.empty:
            field_summaries = []
            for col in df.columns:
                summary = get_field_summary(col, df, field_sample_size, max_val_chars)
                field_summaries.append(f"  - {summary}")
            
            sections.append(f"### {labels['schema']} ({num_cols} {labels['fields']})")
            sections.append("\n".join(field_summaries))
            sections.append("")
        
        # Sample data
        if include_samples and not df.empty:
            sample_df = df.head(sample_size)
            sections.append(f"### {labels['sample']} ({labels['first']} {min(sample_size, num_rows)} {labels['rows']})")
            sections.append(f"```\n{sample_df.to_string()}\n```")
            sections.append("")
        
        summaries.append("\n".join(sections))
    
    # Join with separator
    separator = "\n" + "─" * 60 + "\n\n"
    return separator.join(summaries)


def generate_sql_compatible_summary(
    input_tables: List[Dict[str, Any]],
    language: str = "es"
) -> str:
    """
    Generate a summary optimized for SQL-based agents.
    
    Similar to generate_data_summary but with SQL-specific formatting.
    
    Args:
        input_tables: List of table dicts
        language: 'es' or 'en'
        
    Returns:
        Summary string for SQL context
    """
    return generate_data_summary(
        input_tables,
        include_samples=True,
        sample_size=5,
        field_sample_size=7,
        language=language
    )


# =============================================================================
# Type Inference Utilities
# =============================================================================

def infer_column_type(df: pd.DataFrame, col_name: str) -> str:
    """
    Infer the semantic type of a column.
    
    Args:
        df: DataFrame
        col_name: Column name
        
    Returns:
        Type string: 'numeric', 'categorical', 'datetime', 'text', 'boolean'
    """
    if col_name not in df.columns:
        return "unknown"
    
    dtype = df[col_name].dtype
    
    if pd.api.types.is_bool_dtype(dtype):
        return "boolean"
    
    if pd.api.types.is_numeric_dtype(dtype):
        return "numeric"
    
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "datetime"
    
    # Check for potential datetime strings
    if dtype == object:
        sample = df[col_name].dropna().head(10)
        if len(sample) > 0:
            try:
                pd.to_datetime(sample)
                return "datetime"
            except:
                pass
    
    # Check cardinality for categorical
    if dtype == object:
        unique_ratio = df[col_name].nunique() / len(df) if len(df) > 0 else 0
        if unique_ratio < 0.1:  # Less than 10% unique values
            return "categorical"
        elif unique_ratio < 0.5:
            return "categorical"  # Could be categorical
        else:
            return "text"
    
    return "unknown"


def detect_economic_columns(df: pd.DataFrame) -> Dict[str, List[str]]:
    """
    Detect common economic data columns.
    
    Args:
        df: DataFrame to analyze
        
    Returns:
        Dict mapping column types to column names
    """
    economic_patterns = {
        "country": ["country", "pais", "nation", "nacion", "code", "iso"],
        "year": ["year", "ano", "año", "fecha", "date", "period", "periodo"],
        "gdp": ["gdp", "pib", "producto"],
        "inflation": ["inflation", "inflacion", "cpi", "ipc"],
        "unemployment": ["unemployment", "desempleo", "empleo"],
        "wage": ["wage", "salario", "salary", "sueldo", "ingreso"],
        "population": ["population", "poblacion", "habitantes"],
        "trade": ["export", "import", "trade", "comercio", "balanza"],
    }
    
    detected = {k: [] for k in economic_patterns}
    
    for col in df.columns:
        col_lower = col.lower()
        for category, patterns in economic_patterns.items():
            if any(p in col_lower for p in patterns):
                detected[category].append(col)
    
    return {k: v for k, v in detected.items() if v}


# =============================================================================
# Value Handling Utilities
# =============================================================================

def normalize_value(val: Any) -> Any:
    """
    Normalize a value for comparison/hashing.
    
    Args:
        val: Input value
        
    Returns:
        Normalized value
    """
    if isinstance(val, (int,)):
        return val
    
    try:
        val = float(val)
        val = np.round(val, 5)
        return val
    except (ValueError, TypeError):
        pass
    
    if isinstance(val, (list,)):
        return str(val)
    
    return val


def compute_table_hash(table_rows: List[Dict]) -> int:
    """
    Compute a hash for a table (for caching/comparison).
    
    Args:
        table_rows: List of row dictionaries
        
    Returns:
        Hash integer
    """
    if not table_rows:
        return hash(())
    
    schema = sorted(list(table_rows[0].keys()))
    
    frozen_table = tuple(
        sorted([
            tuple([hash(normalize_value(r.get(key))) for key in schema])
            for r in table_rows
        ])
    )
    
    return hash(frozen_table)


# =============================================================================
# Test Function
# =============================================================================

def test_utils():
    """Test utility functions."""
    print("🧪 Testing Agent Utilities")
    print("=" * 50)
    
    # Test data summary
    test_data = [
        {
            "name": "pib_latam",
            "rows": [
                {"pais": "Argentina", "año": 2020, "pib_usd": 389000000000},
                {"pais": "Brasil", "año": 2020, "pib_usd": 1450000000000},
                {"pais": "Chile", "año": 2020, "pib_usd": 252000000000},
            ]
        }
    ]
    
    summary = generate_data_summary(test_data)
    print("📊 Data Summary:")
    print(summary[:500] + "...\n")
    
    # Test code extraction
    response = '''
    Here's the transformation code:
    
    ```python
    def transform_data(df):
        result = df.groupby('pais')['pib_usd'].sum()
        return result.reset_index()
    ```
    
    This will aggregate GDP by country.
    '''
    
    codes = extract_code_from_response(response, "python")
    print(f"📝 Extracted code blocks: {len(codes)}")
    if codes:
        print(f"   First block:\n{codes[0][:100]}...")
    
    # Test JSON extraction
    json_response = '''
    Based on my analysis:
    {"plan": "Aggregate by year", "columns": ["year", "total"]}
    The result shows trends.
    '''
    
    jsons = extract_json_objects(json_response)
    print(f"\n📋 Extracted JSON objects: {len(jsons)}")
    if jsons:
        print(f"   First: {jsons[0]}")
    
    print("\n✅ Utility tests completed!")


if __name__ == "__main__":
    test_utils()

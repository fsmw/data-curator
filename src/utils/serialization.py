"""
Serialization utilities for JSON/API responses.

This module provides helper functions for preparing data structures
for JSON serialization, particularly handling NaN values and other
edge cases that can break JSON encoding.
"""

import math
from typing import Any, Dict, List, Union


def clean_nan_recursive(obj: Any) -> Any:
    """
    Recursively replace NaN values with None (null in JSON).
    
    This is essential for JSON serialization since NaN is not a valid JSON value.
    
    Args:
        obj: Any Python object (dict, list, float, etc.)
    
    Returns:
        The same object structure with NaN replaced by None
    
    Example:
        >>> data = {"value": float('nan'), "nested": [1, float('nan'), 3]}
        >>> clean_nan_recursive(data)
        {'value': None, 'nested': [1, None, 3]}
    """
    if isinstance(obj, dict):
        return {k: clean_nan_recursive(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan_recursive(item) for item in obj]
    elif isinstance(obj, float) and math.isnan(obj):
        return None
    return obj


def clean_dataset_for_json(dataset: Dict[str, Any], numeric_fields: List[str]) -> Dict[str, Any]:
    """
    Clean a dataset dictionary for JSON serialization.
    
    Handles:
    - NaN values in specified numeric fields
    - None values
    - Nested structures
    
    Args:
        dataset: Dataset dictionary
        numeric_fields: List of field names that may contain NaN
    
    Returns:
        Cleaned dataset dictionary
    """
    cleaned = dict(dataset)
    
    # Replace None/NaN with 0 for numeric fields
    for key in numeric_fields:
        if key in cleaned and (
            cleaned[key] is None
            or (isinstance(cleaned[key], float) and math.isnan(cleaned[key]))
        ):
            cleaned[key] = 0
    
    return cleaned

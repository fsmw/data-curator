#!/usr/bin/env python3
"""
Direct test of the clean_dataframe_for_json function
without needing the server to respond.
"""

import sys
sys.path.insert(0, '/home/fsmw/dev/mises/data-curator')

import pandas as pd
import numpy as np
import json
from src.web.api.visualization import clean_dataframe_for_json, dataframe_to_json_records

print("\n" + "="*70)
print("DIRECT TEST: JSON Serialization Fix")
print("="*70)

# Test 1: DataFrame with NaN values
print("\nTest 1: DataFrame with NaN (missing data)")
print("-" * 70)

df = pd.DataFrame({
    "year": [2020, 2021, 2022],
    "country": ["Argentina", "Brazil", "Argentina"],
    "gdp": [371000.0, 1917000.0, np.nan],
    "inflation": [10.5, 6.3, np.inf]  # inf for demonstration
})

print("Original DataFrame:")
print(df)
print("\nDF dtypes:")
print(df.dtypes)

# Clean the dataframe
df_clean = clean_dataframe_for_json(df)

print("\nCleaned DataFrame:")
print(df_clean)

# Convert to JSON records
json_records = dataframe_to_json_records(df)
print("\nJSON Records (from cleaned DF):")
for record in json_records:
    print(f"  {record}")

# Verify it can be serialized to JSON string
try:
    json_str = json.dumps(json_records)
    print("\n✓ Successfully serialized to JSON string")
    print(f"✓ JSON length: {len(json_str)} characters")
    
    # Check for NaN literals
    if "NaN" in json_str:
        print("✗ ERROR: NaN literal found in JSON!")
        sys.exit(1)
    else:
        print("✓ No NaN literals (values are proper null or numbers)")
    
    # Verify null values are present
    if "null" in json_str:
        print("✓ null values properly represented")
    
    print("\n✓ TEST 1 PASSED")
    
except json.JSONDecodeError as e:
    print(f"✗ JSON serialization failed: {e}")
    sys.exit(1)

# Test 2: Mixed types
print("\n\nTest 2: Mixed data types with None/NaN")
print("-" * 70)

df2 = pd.DataFrame({
    "id": [1, 2, 3],
    "name": ["Alice", None, "Charlie"],
    "score": [95.5, np.nan, 87.3],
    "active": [True, False, True]
})

print("Original DataFrame:")
print(df2)

df2_clean = clean_dataframe_for_json(df2)
json_records2 = dataframe_to_json_records(df2)

print("\nJSON Records:")
for record in json_records2:
    print(f"  {record}")

try:
    json_str2 = json.dumps(json_records2)
    print("\n✓ Successfully serialized to JSON string")
    
    if "NaN" in json_str2:
        print("✗ ERROR: NaN literal found!")
        sys.exit(1)
    else:
        print("✓ All values properly serialized")
    
    print("\n✓ TEST 2 PASSED")
    
except json.JSONDecodeError as e:
    print(f"✗ JSON serialization failed: {e}")
    sys.exit(1)

print("\n" + "="*70)
print("✓ ALL TESTS PASSED")
print("="*70)
print("\nSummary of fixes:")
print("  1. clean_dataframe_for_json() handles numeric & non-numeric columns separately")
print("  2. NaN values are converted to None (JSON null)")  
print("  3. inf values are also converted to None for numeric columns")
print("  4. String/object columns handle None values correctly")
print("\nThis fixes the 'Unexpected token N' JSON error from the chart generation")

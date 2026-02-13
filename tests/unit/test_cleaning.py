import pytest
import pandas as pd
import numpy as np
from src.cleaning import DataCleaner

class MockConfig:
    def __init__(self):
        self.config = {
            "cleaning": {
                "drop_empty_rows": True,
                "drop_empty_columns": True,
                "standardize_country_codes": True,
                "normalize_dates": True,
            }
        }
    def get_directory(self, name):
        from pathlib import Path
        return Path("/tmp/data-curator/test")

@pytest.fixture
def cleaner():
    config = MockConfig()
    return DataCleaner(config)

def test_drop_empty(cleaner):
    data = pd.DataFrame({
        "A": [1, np.nan, 3],
        "B": [np.nan, np.nan, np.nan],
        "C": [1, np.nan, 3]
    })
    # Add an empty row
    data = pd.concat([data, pd.DataFrame({"A": [np.nan], "B": [np.nan], "C": [np.nan]})], ignore_index=True)
    
    cleaned = cleaner.clean_dataset(data)
    
    # Empty column B should be gone
    assert "B" not in cleaned.columns
    # Empty row should be gone
    assert len(cleaned) == 2  # Original 4 rows, 1 empty, 1 with mostly nan but not all (row 1 is [nan, nan, nan] but we drop ALL empty, maybe my test is wrong)
    # Actually row 1 is [nan, nan, nan] because of B, but A and C have 1, nan, 3.
    # Let's check row by row.
    # Row 0: 1, nan, 1 -> Keep
    # Row 1: nan, nan, nan -> Drop
    # Row 2: 3, nan, 3 -> Keep
    # Row 3: nan, nan, nan -> Drop
    assert len(cleaned) == 2

def test_standardize_countries(cleaner):
    data = pd.DataFrame({
        "country": ["Argentina", "United States", "Germany", "Unknown"],
        "value": [10, 20, 30, 40]
    })
    
    cleaned = cleaner.clean_dataset(data)
    
    assert cleaned.iloc[0]["country"] == "ARG"
    assert cleaned.iloc[1]["country"] == "USA"
    assert cleaned.iloc[2]["country"] == "DEU"
    assert cleaned.iloc[3]["country"] == "Unknown"

def test_normalize_dates(cleaner):
    data = pd.DataFrame({
        "year": ["2020", 2021, "2022.0"],
        "value": [1, 2, 3]
    })
    
    cleaned = cleaner.clean_dataset(data)
    
    # Should be Int64 according to implementation
    assert cleaned["year"].dtype.name == "Int64"
    assert cleaned.iloc[0]["year"] == 2020

def test_get_data_summary(cleaner):
    data = pd.DataFrame({
        "year": [2020, 2021],
        "country": ["ARG", "BRA"],
        "value": [10.5, 11.2]
    })
    
    summary = cleaner.get_data_summary(data)
    
    assert summary["rows"] == 2
    assert summary["columns"] == 3
    assert "year" in summary["column_names"]
    assert "value" in summary["numeric_columns"]
    assert summary["year_range"] == [2020, 2021]

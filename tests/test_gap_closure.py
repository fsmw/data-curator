"""
Verification script for Freedom Data Gap Closure.
"""
import sys
import os
import pytest
import pandas as pd
import shutil
from pathlib import Path

# ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from cleaning import DataCleaner
from config import Config
from visualization_web import VegaLiteChartBuilder

@pytest.fixture
def mock_config(tmp_path):
    class MockConfig:
        def __init__(self):
            self.config = {"cleaning": {"validate_schema": True}}
        def get_directory(self, name):
            d = tmp_path / name
            d.mkdir()
            return d
    return MockConfig()

def test_parquet_storage(mock_config):
    cleaner = DataCleaner(mock_config)
    df = pd.DataFrame({'year': [2020, 2021], 'value': [10, 20]})
    
    path = cleaner.save_clean_dataset(
        df, 'test_topic', 'test_source', 
        identifier='parquet-test', format='parquet'
    )
    
    assert str(path).endswith('.parquet')
    assert path.exists()
    
    # Reload to verify
    loaded = pd.read_parquet(path)
    assert len(loaded) == 2

def test_pandera_validation(mock_config):
    # This should pass without error
    cleaner = DataCleaner(mock_config)
    df = pd.DataFrame({'year': [2020], 'value': [10.5]})
    
    # Logic is internal, but we can check it doesn't crash
    result = cleaner.clean_dataset(df)
    assert len(result) == 1

def test_visualization_theme():
    # Force reload colors?
    VegaLiteChartBuilder._load_brand_colors()
    
    colors = VegaLiteChartBuilder.PROFESSIONAL_COLORS
    # Check for primary color from our palette
    assert "#002b36" in colors
    assert "#b58900" in colors
    
    # Check chart usage
    df = pd.DataFrame({'year': [2020], 'val': [10], 'country': ['ARG']})
    spec = VegaLiteChartBuilder.build_time_series(df)
    
    assert spec['encoding']['color']['scale']['range'] == colors

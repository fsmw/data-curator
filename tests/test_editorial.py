"""
Tests for the Editorial Module.
"""
import sys
import os
import pytest
import pandas as pd
import numpy as np

# ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from editorial import DataHighlightSelector, MicrolearningGenerator, create_weekly_pack

@pytest.fixture
def editorial_data():
    """Create a sample dataset with anomalies."""
    np.random.seed(42)
    dates = pd.date_range(start='2020-01-01', periods=20, freq='Y')
    values = np.random.normal(100, 5, 20)
    # Add a spike
    values[10] = 150
    # Add a record low
    values[5] = 50
    
    df = pd.DataFrame({
        'year': dates.year,
        'value': values
    })
    return df

def test_highlight_selector_spikes(editorial_data):
    selector = DataHighlightSelector(editorial_data)
    spikes = selector.find_spikes('value', threshold=2.0)
    
    # Value 150 (idx 10) and 50 (idx 5) should be spikes
    assert len(spikes) >= 1
    assert any(s['value'] >= 149 for s in spikes)
    assert spikes[0]['type'] == 'spike'

def test_highlight_selector_records(editorial_data):
    selector = DataHighlightSelector(editorial_data)
    records = selector.find_records('value')
    
    assert len(records) == 2  # high and low
    types = [r['type'] for r in records]
    assert 'record_high' in types
    assert 'record_low' in types
    
    high = next(r for r in records if r['type'] == 'record_high')
    assert high['value'] >= 149

def test_microlearning_generator():
    generator = MicrolearningGenerator()
    highlight = {
        'type': 'record_high',
        'value': 123.45,
        'date': 2024,
        'description': 'Test description'
    }
    draft = generator.generate_draft(highlight, 'Test Context')
    
    assert '# 📊 Dato de la Semana' in draft
    assert '123.45' in draft
    assert 'máximo histórico' in draft

import sys
import os
import pytest
import pandas as pd
import numpy as np

# ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from analysis import StatisticalAnalyzer, RegressionBuilder, PanelDataAnalyzer

@pytest.fixture
def sample_data():
    """Create a sample dataset for testing."""
    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        'salary': np.random.normal(50000, 10000, n),
        'experience': np.random.normal(5, 2, n),
        'education': np.random.randint(12, 20, n),
        'group': np.random.choice(['A', 'B'], n)
    })
    # Add some correlation
    df['salary'] += df['experience'] * 2000 + df['education'] * 1000
    return df

@pytest.fixture
def panel_data():
    """Create a sample panel dataset."""
    countries = ['ARG', 'BRA', 'CHL']
    years = range(2000, 2011)
    data = []
    for c in countries:
        for y in years:
            data.append({
                'country': c,
                'year': y,
                'gdp_growth': np.random.normal(3, 2),
                'inflation': np.random.normal(5, 3),
                'investment': np.random.normal(20, 5)
            })
    return pd.DataFrame(data)

def test_statistical_analyzer_summarize(sample_data):
    analyzer = StatisticalAnalyzer(sample_data)
    summary = analyzer.summarize()
    
    assert 'count' in summary.columns
    assert 'mean' in summary.columns
    assert summary.loc['salary', 'count'] == 100

def test_compare_groups(sample_data):
    analyzer = StatisticalAnalyzer(sample_data)
    result = analyzer.compare_groups('group', 'salary')
    
    assert 'test' in result
    assert 'p_value' in result
    assert result['test'] == 'T-test'

def test_regression_builder(sample_data):
    builder = RegressionBuilder(sample_data)
    result = builder.run_ols("salary ~ experience + education")
    
    assert 'params' in result
    assert 'r_squared' in result
    assert result['r_squared'] > 0
    assert 'experience' in result['params']

def test_panel_analyzer(panel_data):
    analyzer = PanelDataAnalyzer(panel_data, 'country', 'year')
    result = analyzer.run_fixed_effects("gdp_growth ~ investment")
    
    # linearmodels might not be installed in all test environments
    if "error" not in result:
        assert 'params' in result
        assert 'investment' in result['params']
    else:
        # If linearmodels missing, it should handle gracefully
        assert result['error'] == "linearmodels not installed"

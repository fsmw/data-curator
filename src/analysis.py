"""
Freedom Data Analysis Module
===========================

This module provides statistical and econometric capabilities to the curation tool.
It wraps statsmodels and linearmodels to provide a standardized interface for
economic analysis.

Capabilities:
- Descriptive Statistics
- OLS Regressions
- Panel Data Models
- Hypothesis Testing

Author: Freedom Data Team
Date: 2026-02-02
"""

from typing import Optional, Dict, List, Union, Any
from pathlib import Path
import pandas as pd
import numpy as np


try:
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    from linearmodels import PanelOLS
    from scipy import stats
except ImportError:
    # Fallback for environments where dependencies aren't installed yet
    sm = None
    smf = None
    PanelOLS = None
    stats = None


class StatisticalAnalyzer:
    """Provides descriptive statistics and basic hypothesis testing."""
    
    def __init__(self, data: pd.DataFrame):
        self.data = data
        
    def summarize(self) -> pd.DataFrame:
        """
        Generate comprehensive summary statistics.
        Includes count, mean, std, min, max, and quantiles.
        """
        return self.data.describe(include='all').T
        
    def correlation_matrix(self, method: str = 'pearson') -> pd.DataFrame:
        """Calculate correlation matrix for numeric columns."""
        return self.data.corr(method=method)

    def compare_groups(self, group_col: str, value_col: str) -> Dict[str, Any]:
        """
        Compare means between groups (t-test or ANOVA).
        Returns test statistic and p-value.
        """
        if stats is None:
            return {"error": "scipy not installed"}
            
        groups = self.data.groupby(group_col)[value_col].apply(list)
        
        if len(groups) == 2:
            # T-test
            stat, pval = stats.ttest_ind(groups[0], groups[1], nan_policy='omit')
            test_name = "T-test"
        else:
            # ANOVA
            stat, pval = stats.f_oneway(*groups)
            test_name = "ANOVA"
            
        return {
            "test": test_name,
            "statistic": stat,
            "p_value": pval,
            "significant_05": pval < 0.05
        }


class RegressionBuilder:
    """Wrapper for cross-sectional regression models (OLS)."""
    
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.model = None
        self.results = None
        
    def run_ols(self, formula: str, robust_cov: str = 'HC1') -> Dict[str, Any]:
        """
        Run Ordinary Least Squares regression.
        
        Args:
            formula: R-style formula (e.g. 'y ~ x1 + x2')
            robust_cov: Covariance type (default HC1 for robust standard errors)
        """
        if smf is None:
            return {"error": "statsmodels not installed"}
            
        try:
            self.model = smf.ols(formula=formula, data=self.data)
            self.results = self.model.fit(cov_type=robust_cov)
            
            return {
                "params": self.results.params.to_dict(),
                "r_squared": self.results.rsquared,
                "adj_r_squared": self.results.rsquared_adj,
                "p_values": self.results.pvalues.to_dict(),
                "summary": self.results.summary().as_text()
            }
        except Exception as e:
            return {"error": str(e)}


class PanelDataAnalyzer:
    """Wrapper for panel data models (Fixed Effects)."""
    
    def __init__(self, data: pd.DataFrame, entity_col: str, time_col: str):
        self.data = data.copy()
        self.entity_col = entity_col
        self.time_col = time_col
        
        # Prepare valid panel index
        if entity_col in self.data.columns and time_col in self.data.columns:
            self.data = self.data.set_index([entity_col, time_col])
        
    def run_fixed_effects(self, formula: str) -> Dict[str, Any]:
        """
        Run Fixed Effects model using LinearModels.
        
        Args:
            formula: Formula string (e.g. 'y ~ 1 + x1 + x2 + EntityEffects')
        """
        if PanelOLS is None:
            return {"error": "linearmodels not installed"}
            
        try:
            # Auto-add EntityEffects if not present but implied by class usage
            if 'EntityEffects' not in formula:
                formula += ' + EntityEffects'
                
            mod = PanelOLS.from_formula(formula, self.data)
            res = mod.fit(cov_type='clustered', cluster_entity=True)
            
            return {
                "params": res.params.to_dict(),
                "r_squared": res.rsquared,
                "summary": str(res)
            }
        except Exception as e:
            return {"error": str(e)}


def analyze_dataset(
    filepath: Union[str, Path], 
    analysis_type: str = "descriptive",
    **kwargs
) -> Dict[str, Any]:
    """
    Main entry point for analysis.
    
    Args:
        filepath: Path to dataset (CSV/Parquet)
        analysis_type: 'descriptive', 'regression', or 'panel'
        **kwargs: 
            - formula (for regression/panel)
            - entity_col/time_col (for panel)
            - group_col/value_col (for compare)
    """
    path = Path(filepath)
    if path.suffix == '.parquet':
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path)
        
    if analysis_type == "descriptive":
        analyzer = StatisticalAnalyzer(df)
        return {"summary": analyzer.summarize().to_dict()}
        
    elif analysis_type == "compare":
        analyzer = StatisticalAnalyzer(df)
        return analyzer.compare_groups(
            kwargs.get('group_col'), 
            kwargs.get('value_col')
        )
        
    elif analysis_type == "regression":
        builder = RegressionBuilder(df)
        return builder.run_ols(kwargs.get('formula'))
        
    elif analysis_type == "panel":
        analyzer = PanelDataAnalyzer(
            df, 
            kwargs.get('entity_col', 'country'), 
            kwargs.get('time_col', 'year')
        )
        return analyzer.run_fixed_effects(kwargs.get('formula'))
        
    return {"error": f"Unknown analysis type: {analysis_type}"}

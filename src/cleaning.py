"""Data cleaning and standardization pipeline."""

from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd
import re
from datetime import datetime


class DataCleaner:
    """Handles data cleaning and standardization operations."""
    
    # ISO 3166-1 alpha-3 country code mappings (sample - extend as needed)
    COUNTRY_CODES = {
        'Argentina': 'ARG',
        'Brasil': 'BRA', 'Brazil': 'BRA',
        'Chile': 'CHL',
        'Colombia': 'COL',
        'México': 'MEX', 'Mexico': 'MEX',
        'Perú': 'PER', 'Peru': 'PER',
        'Uruguay': 'URY',
        'Venezuela': 'VEN',
        'España': 'ESP', 'Spain': 'ESP',
        'Estados Unidos': 'USA', 'United States': 'USA', 'USA': 'USA',
        'Alemania': 'DEU', 'Germany': 'DEU',
        'Francia': 'FRA', 'France': 'FRA',
        'Reino Unido': 'GBR', 'United Kingdom': 'GBR',
        'China': 'CHN',
        'Japón': 'JPN', 'Japan': 'JPN',
    }
    
    def __init__(self, config):
        """
        Initialize data cleaner.
        
        Args:
            config: Config object
        """
        self.config = config
        self.clean_dir = config.get_directory('clean')
        self.transformations = []
    
    def clean_dataset(self, data: pd.DataFrame, rules: Optional[Dict] = None) -> pd.DataFrame:
        """
        Apply cleaning rules to dataset.
        
        Args:
            data: Input DataFrame
            rules: Optional custom cleaning rules (uses config defaults if None)
            
        Returns:
            Cleaned DataFrame
        """
        if rules is None:
            rules = self.config.config.get('cleaning', {})
        
        df = data.copy()
        self.transformations = []
        
        # Drop empty rows
        if rules.get('drop_empty_rows', True):
            original_len = len(df)
            df = df.dropna(how='all')
            if len(df) < original_len:
                self.transformations.append(f"Removed {original_len - len(df)} empty rows")
        
        # Drop empty columns
        if rules.get('drop_empty_columns', True):
            original_cols = len(df.columns)
            df = df.dropna(axis=1, how='all')
            if len(df.columns) < original_cols:
                self.transformations.append(f"Removed {original_cols - len(df.columns)} empty columns")
        
        # Standardize country codes
        if rules.get('standardize_country_codes', True):
            df = self._standardize_countries(df)
        
        # Normalize dates
        if rules.get('normalize_dates', True):
            df = self._normalize_dates(df)
        
        return df
    
    def _standardize_countries(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize country names to ISO 3166-1 alpha-3 codes.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with standardized country codes
        """
        # Try to find country column
        country_cols = [col for col in df.columns if 'country' in col.lower() or 'pais' in col.lower()]
        
        if not country_cols:
            return df
        
        country_col = country_cols[0]
        
        # Map country names to codes
        def map_country(name):
            if pd.isna(name):
                return name
            # Try exact match
            if name in self.COUNTRY_CODES:
                return self.COUNTRY_CODES[name]
            # Try case-insensitive match
            for key, value in self.COUNTRY_CODES.items():
                if str(name).lower() == key.lower():
                    return value
            # Return original if no match
            return name
        
        df[country_col] = df[country_col].apply(map_country)
        self.transformations.append(f"Standardized country codes in column '{country_col}'")
        
        return df
    
    def _normalize_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize date columns to consistent format.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with normalized dates
        """
        date_cols = [col for col in df.columns if any(keyword in col.lower() 
                     for keyword in ['date', 'year', 'fecha', 'año', 'ano'])]
        
        for col in date_cols:
            try:
                # If column contains only years
                if df[col].dtype in ['int64', 'float64'] and df[col].notna().any():
                    if df[col].max() < 3000 and df[col].min() > 1900:
                        # Already in year format, ensure integer
                        df[col] = df[col].astype('Int64')
                        continue
                
                # Try to parse as datetime
                df[col] = pd.to_datetime(df[col], errors='coerce')
                self.transformations.append(f"Normalized dates in column '{col}'")
            except Exception as e:
                # Skip if conversion fails
                pass
        
        return df
    
    def save_clean_dataset(
        self, 
        data: pd.DataFrame, 
        topic: str,
        source: str,
        coverage: str = "global",
        start_year: Optional[int] = None,
        end_year: Optional[int] = None
    ) -> Path:
        """
        Save cleaned dataset following naming convention.
        
        Args:
            data: Cleaned DataFrame
            topic: Topic name (e.g., 'salarios_reales')
            source: Source name (e.g., 'owid', 'ilostat')
            coverage: Geographic coverage (e.g., 'latam', 'global')
            start_year: Starting year of data
            end_year: Ending year of data
            
        Returns:
            Path to saved file
        """
        # Auto-detect years if not provided
        if start_year is None or end_year is None:
            year_cols = [col for col in data.columns if 'year' in col.lower() or 'año' in col.lower()]
            if year_cols:
                year_col = year_cols[0]
                years = data[year_col].dropna()
                if len(years) > 0:
                    start_year = start_year or int(years.min())
                    end_year = end_year or int(years.max())
        
        # Construct filename following convention
        filename_parts = [
            topic.lower(),
            source.lower(),
            coverage.lower(),
            str(start_year) if start_year else "na",
            str(end_year) if end_year else "na"
        ]
        filename = "_".join(filename_parts) + ".csv"
        
        # Save to appropriate topic subdirectory
        topic_dir = self.clean_dir / topic
        topic_dir.mkdir(parents=True, exist_ok=True)
        filepath = topic_dir / filename
        
        data.to_csv(filepath, index=False, encoding='utf-8')
        print(f"✓ Saved cleaned dataset to {filepath}")
        
        return filepath
    
    def get_transformations(self) -> list:
        """Get list of transformations applied to the data."""
        return self.transformations
    
    def get_data_summary(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate summary statistics for a dataset.
        
        Args:
            data: DataFrame to summarize
            
        Returns:
            Dictionary with summary information
        """
        summary = {
            'rows': len(data),
            'columns': len(data.columns),
            'column_names': list(data.columns),
            'dtypes': {col: str(dtype) for col, dtype in data.dtypes.items()},
            'missing_values': {col: int(data[col].isna().sum()) for col in data.columns},
            'numeric_columns': list(data.select_dtypes(include=['number']).columns),
            'date_columns': list(data.select_dtypes(include=['datetime']).columns),
        }
        
        # Add year range if available
        year_cols = [col for col in data.columns if 'year' in col.lower()]
        if year_cols:
            years = data[year_cols[0]].dropna()
            if len(years) > 0:
                summary['year_range'] = [int(years.min()), int(years.max())]
        
        return summary

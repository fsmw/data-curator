"""Data cleaning and standardization pipeline."""

from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd
import re
from datetime import datetime
try:
    import pandera as pa
    from pandera.typing import DataFrame, Series
except ImportError:
    pa = None

try:
    import pyarrow
except ImportError:
    pyarrow = None


class DataCleaner:
    """Handles data cleaning and standardization operations."""

    # ISO 3166-1 alpha-3 country code mappings (sample - extend as needed)
    COUNTRY_CODES = {
        "Argentina": "ARG",
        "Brasil": "BRA",
        "Brazil": "BRA",
        "Chile": "CHL",
        "Colombia": "COL",
        "México": "MEX",
        "Mexico": "MEX",
        "Perú": "PER",
        "Peru": "PER",
        "Uruguay": "URY",
        "Venezuela": "VEN",
        "España": "ESP",
        "Spain": "ESP",
        "Estados Unidos": "USA",
        "United States": "USA",
        "USA": "USA",
        "Alemania": "DEU",
        "Germany": "DEU",
        "Francia": "FRA",
        "France": "FRA",
        "Reino Unido": "GBR",
        "United Kingdom": "GBR",
        "China": "CHN",
        "Japón": "JPN",
        "Japan": "JPN",
    }

    def __init__(self, config):
        """
        Initialize data cleaner.

        Args:
            config: Config object
        """
        self.config = config
        self.clean_dir = config.get_directory("clean")
        self.transformations = []

    def clean_dataset(
        self, data: pd.DataFrame, rules: Optional[Dict] = None
    ) -> pd.DataFrame:
        """
        Apply cleaning rules to dataset.

        Args:
            data: Input DataFrame
            rules: Optional custom cleaning rules (uses config defaults if None)

        Returns:
            Cleaned DataFrame
        """
        if rules is None:
            rules = self.config.config.get("cleaning", {})

        df = data.copy()
        self.transformations = []

        # Drop empty rows
        if rules.get("drop_empty_rows", True):
            original_len = len(df)
            df = df.dropna(how="all")
            if len(df) < original_len:
                self.transformations.append(
                    f"Removed {original_len - len(df)} empty rows"
                )

        # Drop empty columns
        if rules.get("drop_empty_columns", True):
            original_cols = len(df.columns)
            df = df.dropna(axis=1, how="all")
            if len(df.columns) < original_cols:
                self.transformations.append(
                    f"Removed {original_cols - len(df.columns)} empty columns"
                )

        # Standardize country codes
        if rules.get("standardize_country_codes", True):
            df = self._standardize_countries(df)

        # Normalize dates
        if rules.get("normalize_dates", True):

            df = self._normalize_dates(df)
            
        # Validation (Phase 6)
        if rules.get("validate_schema", True) and pa is not None:
            df = self._validate_schema(df)

        return df

    def _validate_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate dataframe against economic data schema."""
        try:
            # Dynamic schema based on columns
            columns = {}
            for col in df.columns:
                if "year" in col or "date" in col:
                     columns[col] = pa.Column(coerce=True, nullable=True)
                elif pd.api.types.is_numeric_dtype(df[col]):
                     columns[col] = pa.Column(float, nullable=True)
                else:
                     columns[col] = pa.Column(str, nullable=True)
            
            schema = pa.DataFrameSchema(columns=columns)
            return schema.validate(df)
        except Exception as e:
            print(f"Schema validation warning: {e}")
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
        country_cols = [
            col
            for col in df.columns
            if "country" in col.lower() or "pais" in col.lower()
        ]

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
        self.transformations.append(
            f"Standardized country codes in column '{country_col}'"
        )

        return df

    def _normalize_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize date columns to consistent format.

        Args:
            df: Input DataFrame

        Returns:
            DataFrame with normalized dates
        """
        date_cols = [
            col
            for col in df.columns
            if any(
                keyword in col.lower()
                for keyword in ["date", "year", "fecha", "año", "ano"]
            )
        ]

        for col in date_cols:
            try:
                # If column contains only years (numeric), keep as integer year
                if (
                    pd.api.types.is_integer_dtype(df[col])
                    or pd.api.types.is_float_dtype(df[col])
                ) and df[col].notna().any():
                    try:
                        maxv = pd.to_numeric(df[col], errors="coerce").max()
                        minv = pd.to_numeric(df[col], errors="coerce").min()
                        if (
                            pd.notna(maxv)
                            and pd.notna(minv)
                            and maxv < 3000
                            and minv > 1900
                        ):
                            df[col] = pd.to_numeric(df[col], errors="coerce").astype(
                                "Int64"
                            )
                            continue
                    except Exception:
                        pass

                # Try to parse as datetime
                df[col] = pd.to_datetime(df[col], errors="coerce")
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
        end_year: Optional[int] = None,
        identifier: Optional[str] = None,
        format: str = "csv"
    ) -> Path:
        """
        Save cleaned dataset. Supports CSV and Parquet.
        identifier (slug or id) and a timestamp to avoid collisions.

        Args:
            data: Cleaned DataFrame
            topic: Topic name (e.g., 'salarios_reales')
            source: Source name (e.g., 'owid', 'ilostat')
            coverage: Geographic coverage (e.g., 'latam', 'global')
            start_year: Starting year of data
            end_year: Ending year of data
            identifier: Optional indicator slug or id to include in filename

        Returns:
            Path to saved file
        """
        # Auto-detect years if not provided
        if start_year is None or end_year is None:
            year_cols = [
                col
                for col in data.columns
                if "year" in col.lower() or "año" in col.lower()
            ]
            if year_cols:
                year_col = year_cols[0]
                years_series = data[year_col].dropna()
                if len(years_series) > 0:
                    # If datetime-like, extract year; otherwise try numeric conversion
                    try:
                        if pd.api.types.is_datetime64_any_dtype(years_series) or (
                            pd.api.types.is_object_dtype(years_series)
                            and isinstance(years_series.iloc[0], pd.Timestamp)
                        ):
                            years = (
                                pd.to_datetime(years_series, errors="coerce")
                                .dt.year.dropna()
                                .astype(int)
                            )
                        else:
                            years = (
                                pd.to_numeric(years_series, errors="coerce")
                                .dropna()
                                .astype(int)
                            )
                        if len(years) > 0:
                            start_year = start_year or int(years.min())
                            end_year = end_year or int(years.max())
                    except Exception:
                        pass

        # Sanitize optional identifier for filename use
        id_part = None
        if identifier:
            # lower-case, replace non-alphanumeric with hyphens, strip hyphens
            id_part = re.sub(r"[^a-z0-9\-]+", "-", str(identifier).lower())
            id_part = re.sub(r"[-]+", "-", id_part).strip("-")

        # Add timestamp to ensure uniqueness
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")

        # Construct filename following convention
        filename_parts = [
            topic.lower(),
            source.lower(),
            coverage.lower(),
            str(start_year) if start_year else "na",
            str(end_year) if end_year else "na",
        ]
        if id_part:
            filename_parts.insert(2, id_part)  # place identifier before coverage
        filename_parts.append(timestamp)

        filename = "_".join(filename_parts) + ".csv"

        # Save to appropriate topic subdirectory
        topic_dir = self.clean_dir / topic
        topic_dir.mkdir(parents=True, exist_ok=True)
        filepath = topic_dir / filename
        
        if format == "parquet":
            filepath = filepath.with_suffix(".parquet")
            data.to_parquet(filepath, index=False)
        else:
            data.to_csv(filepath, index=False, encoding="utf-8")
            
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
            "rows": len(data),
            "columns": len(data.columns),
            "column_names": list(data.columns),
            "dtypes": {col: str(dtype) for col, dtype in data.dtypes.items()},
            "missing_values": {
                col: int(data[col].isna().sum()) for col in data.columns
            },
            "numeric_columns": list(data.select_dtypes(include=["number"]).columns),
            "date_columns": list(data.select_dtypes(include=["datetime"]).columns),
        }

        # Add year range if available
        year_cols = [col for col in data.columns if "year" in col.lower()]
        if year_cols:
            years_series = data[year_cols[0]].dropna()
            try:
                if len(years_series) > 0:
                    if pd.api.types.is_datetime64_any_dtype(years_series) or (
                        pd.api.types.is_object_dtype(years_series)
                        and isinstance(years_series.iloc[0], pd.Timestamp)
                    ):
                        yr = (
                            pd.to_datetime(years_series, errors="coerce")
                            .dt.year.dropna()
                            .astype(int)
                        )
                    else:
                        yr = (
                            pd.to_numeric(years_series, errors="coerce")
                            .dropna()
                            .astype(int)
                        )
                    if len(yr) > 0:
                        summary["year_range"] = [int(yr.min()), int(yr.max())]
            except Exception:
                pass

        return summary

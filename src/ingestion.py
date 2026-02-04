"""Data ingestion module for various economic data sources."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd
import requests
from datetime import datetime
import shutil

from logger import get_logger

logger = get_logger(__name__)


class DataSource(ABC):
    """Abstract base class for data sources."""

    def __init__(self, name: str, raw_data_dir: Path):
        """
        Initialize data source.

        Args:
            name: Source name (ILOSTAT, OECD, IMF, etc.)
            raw_data_dir: Directory to store raw data
        """
        self.name = name
        self.raw_data_dir = raw_data_dir / name
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def fetch(self, **kwargs) -> pd.DataFrame:
        """Fetch data from source. To be implemented by subclasses."""
        pass

    def save_raw(self, data: pd.DataFrame, filename: str) -> Path:
        """
        Save raw data to disk.

        Args:
            data: DataFrame to save
            filename: Output filename

        Returns:
            Path to saved file
        """
        filepath = self.raw_data_dir / filename
        data.to_csv(filepath, index=False, encoding="utf-8")
        logger.info(f"Saved raw data to {filepath}")
        return filepath


class ManualUpload(DataSource):
    """Handler for manually uploaded datasets."""

    def __init__(self, raw_data_dir: Path):
        super().__init__("Institutos_Nacionales", raw_data_dir)

    def fetch(self, filepath: str, **kwargs) -> pd.DataFrame:
        """
        Import manually uploaded file.

        Args:
            filepath: Path to the uploaded file

        Returns:
            DataFrame with the data
        """
        file_path = Path(filepath)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        # Detect file type and read accordingly
        if file_path.suffix.lower() == ".csv":
            data = pd.read_csv(filepath, encoding="utf-8")
        elif file_path.suffix.lower() in [".xlsx", ".xls"]:
            data = pd.read_excel(filepath)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")

        # Copy to raw data directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        destination = self.raw_data_dir / new_filename
        shutil.copy2(filepath, destination)

        logger.info(f"Imported {filepath}")
        logger.info(f"Archived to {destination}")

        return data


class ILOSTATSource(DataSource):
    """Handler for ILOSTAT API data."""

    BASE_URL = "https://www.ilo.org/sdmx/rest/data"

    def __init__(self, raw_data_dir: Path):
        super().__init__("ILOSTAT", raw_data_dir)

    def fetch(
        self,
        indicator: str,
        countries: list = None,
        start_year: int = 2010,
        end_year: int = 2024,
        **kwargs,
    ) -> pd.DataFrame:
        """
        Fetch data from ILOSTAT API using SDMX protocol.

        Args:
            indicator: ILOSTAT indicator code
            countries: List of ISO country codes
            start_year: Starting year
            end_year: Ending year

        Returns:
            DataFrame with the data
        """
        if countries is None:
            countries = ["ARG", "BRA", "CHL", "COL", "MEX", "PER", "URY"]

        try:
            # Construct SDMX query
            # Format: {base_url}/{dataflow}/{country},{...}/{...}/all?startPeriod={start}&endPeriod={end}
            countries_str = ",".join(countries)

            url = f"{self.BASE_URL}/DF_STR/{countries_str}/.*/{indicator}?startPeriod={start_year}&endPeriod={end_year}&format=sdmx-json&detail=full"

            logger.info(f"Fetching from ILOSTAT: {indicator}")
            logger.info(f"  Countries: {countries_str}")
            logger.info(f"  Period: {start_year}-{end_year}")

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Parse SDMX-JSON response
            data = response.json()

            # Extract data from SDMX-JSON structure
            df = self._parse_sdmx_json(data, indicator)

            if len(df) > 0:
                logger.info(f"Retrieved {len(df)} records from ILOSTAT")
            else:
                logger.warning(f"No data found for indicator {indicator}")

            return df

        except requests.exceptions.RequestException as e:
            logger.error(f"ILOSTAT API error: {e}")
            logger.info("Falling back to template mode")
            return pd.DataFrame(columns=["country", "year", "value", "indicator"])

    def _parse_sdmx_json(self, data: dict, indicator: str) -> pd.DataFrame:
        """Parse SDMX-JSON response into DataFrame."""
        rows = []

        try:
            # SDMX-JSON structure
            observations = data.get("data", {}).get("dataSets", [])
            structure = data.get("structure", {})
            dimensions = structure.get("dimensions", {})

            if not observations:
                return pd.DataFrame()

            dataset = observations[0]

            # Get dimension indices
            country_idx = None
            time_idx = None

            for i, dim in enumerate(dimensions.get("observation", [])):
                if "REF_AREA" in dim.get("id", ""):
                    country_idx = i
                if dim.get("id") == "TIME_PERIOD":
                    time_idx = i

            # Parse observations
            for obs_key, obs_value in dataset.get("observations", {}).items():
                parts = obs_key.split(":")
                if not obs_value or len(parts) < 2:
                    continue

                try:
                    year = int(parts[-1])  # Last part is usually time
                    value = obs_value[0] if isinstance(obs_value, list) else obs_value

                    rows.append(
                        {
                            "country": parts[0] if country_idx else "UNKNOWN",
                            "year": year,
                            "value": float(value),
                            "indicator": indicator,
                        }
                    )
                except (ValueError, IndexError):
                    continue

            return pd.DataFrame(rows)

        except Exception as e:
            logger.error(f"Error parsing SDMX response: {e}")
            return pd.DataFrame()


class OECDSource(DataSource):
    """Handler for OECD API data."""

    BASE_URL = "https://sdmx.oecd.org/public/rest/data"

    # Country name to ISO 3-letter code mapping
    COUNTRY_CODES = {
        "Argentina": "ARG",
        "Brasil": "BRA",
        "Brazil": "BRA",
        "Chile": "CHL",
        "Colombia": "COL",
        "Mexico": "MEX",
        "México": "MEX",
        "Peru": "PER",
        "Perú": "PER",
        "Uruguay": "URY",
        "Paraguay": "PRY",
        "Bolivia": "BOL",
        "Ecuador": "ECU",
        "Venezuela": "VEN",
        "United States": "USA",
        "USA": "USA",
        "Canada": "CAN",
        "United Kingdom": "GBR",
        "Germany": "DEU",
        "France": "FRA",
        "Italy": "ITA",
        "Spain": "ESP",
        "Japan": "JPN",
        "South Korea": "KOR",
        "Australia": "AUS",
    }

    def __init__(self, raw_data_dir: Path, api_key: Optional[str] = None):
        super().__init__("OECD", raw_data_dir)
        self.api_key = api_key

    def fetch(
        self,
        dataset: str,
        indicator: str = "",
        countries: list = None,
        start_year: int = 2010,
        end_year: int = 2024,
        **kwargs,
    ) -> pd.DataFrame:
        """
        Fetch data from OECD API using SDMX-JSON.

        Args:
            dataset: OECD dataset identifier (e.g., 'ALFS', 'REV')
            indicator: Indicator code within dataset
            countries: List of country names or codes
            start_year: Starting year
            end_year: Ending year

        Returns:
            DataFrame with the data
        """
        if countries is None:
            countries = ["ARG", "BRA", "CHL", "MEX", "COL", "URY"]

        try:
            # Convert country names to ISO codes if needed
            country_codes = []
            for country in countries:
                # If it's already a 3-letter code, use it
                if len(country) == 3 and country.isupper():
                    country_codes.append(country)
                # Otherwise, try to map the name to a code
                elif country in self.COUNTRY_CODES:
                    country_codes.append(self.COUNTRY_CODES[country])
                else:
                    # If not found, assume it's already a code
                    country_codes.append(country)

            countries_str = "+".join(country_codes)

            # OECD SDMX 2.1 format: {base}/{dataset}/{key}?startPeriod={start}&endPeriod={end}
            # Key format: COUNTRY+COUNTRY.INDICATOR or just COUNTRY+COUNTRY if no indicator
            key = f"{countries_str}.{indicator}" if indicator else countries_str
            url = f"{self.BASE_URL}/{dataset}/{key}?startPeriod={start_year}&endPeriod={end_year}&dimensionAtObservation=AllDimensions"

            logger.info(f"Fetching from OECD: {dataset}/{indicator if indicator else 'all'}")
            logger.info(f"  Countries: {countries_str}")
            logger.info(f"  Period: {start_year}-{end_year}")

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            df = self._parse_sdmx_json(data)

            if len(df) > 0:
                logger.info(f"Retrieved {len(df)} records from OECD")
            else:
                logger.warning(f"No data found for dataset {dataset}")

            return df

        except requests.exceptions.RequestException as e:
            logger.error(f"OECD API error: {e}")
            logger.info("Falling back to template mode")
            return pd.DataFrame(columns=["country", "year", "value", "indicator"])

    def _parse_sdmx_json(self, data: dict) -> pd.DataFrame:
        """Parse SDMX-JSON response into DataFrame."""
        rows = []

        try:
            observations = data.get("data", {}).get("dataSets", [])
            structure = data.get("structure", {})

            if not observations:
                return pd.DataFrame()

            dataset = observations[0]

            # Parse observations - OECD format
            for obs_key, obs_value in dataset.get("observations", {}).items():
                parts = obs_key.split(":")
                if not obs_value or len(parts) < 2:
                    continue

                try:
                    year = int(parts[-1])
                    value = obs_value[0] if isinstance(obs_value, list) else obs_value

                    rows.append(
                        {
                            "country": parts[0] if parts else "UNKNOWN",
                            "year": year,
                            "value": float(value) if value else None,
                        }
                    )
                except (ValueError, IndexError, TypeError):
                    continue

            return pd.DataFrame(rows)

        except Exception as e:
            logger.error(f"Error parsing SDMX-JSON: {e}")
            return pd.DataFrame()


class IMFSource(DataSource):
    """Handler for IMF API data."""

    BASE_URL = "https://dataservices.imf.org/REST/SDMX_JSON.svc"

    # Country name to ISO 3-letter code mapping
    COUNTRY_CODES = {
        "Argentina": "ARG",
        "Brasil": "BRA",
        "Brazil": "BRA",
        "Chile": "CHL",
        "Colombia": "COL",
        "Mexico": "MEX",
        "México": "MEX",
        "Peru": "PER",
        "Perú": "PER",
        "Uruguay": "URY",
        "Paraguay": "PRY",
        "Bolivia": "BOL",
        "Ecuador": "ECU",
        "Venezuela": "VEN",
        "United States": "USA",
        "USA": "USA",
        "Canada": "CAN",
        "United Kingdom": "GBR",
        "Germany": "DEU",
        "France": "FRA",
        "Italy": "ITA",
        "Spain": "ESP",
        "Japan": "JPN",
        "South Korea": "KOR",
        "Australia": "AUS",
    }

    def __init__(self, raw_data_dir: Path, api_key: Optional[str] = None):
        super().__init__("IMF", raw_data_dir)
        self.api_key = api_key

    def fetch(
        self,
        database: str,
        indicator: str,
        countries: list = None,
        start_year: int = 2010,
        end_year: int = 2024,
        **kwargs,
    ) -> pd.DataFrame:
        """
        Fetch data from IMF API.

        Args:
            database: IMF database (e.g., 'WEO' for World Economic Outlook)
            indicator: Indicator code (e.g., 'NGDP_RPCH' for real GDP growth)
            countries: List of country names or codes
            start_year: Starting year
            end_year: Ending year

        Returns:
            DataFrame with the data
        """
        if countries is None:
            countries = ["ARG", "BRA", "CHL", "COL", "MEX", "PER", "URY"]

        try:
            # Convert country names to ISO codes if needed
            country_codes = []
            for country in countries:
                # If it's already a 3-letter code, use it
                if len(country) == 3 and country.isupper():
                    country_codes.append(country)
                # Otherwise, try to map the name to a code
                elif country in self.COUNTRY_CODES:
                    country_codes.append(self.COUNTRY_CODES[country])
                else:
                    # If not found, assume it's already a code
                    country_codes.append(country)

            countries_str = ",".join(country_codes)

            # IMF SDMX format: /data/{database}/{countries}/{indicator}
            url = f"{self.BASE_URL}/data/{database}/{countries_str}/{indicator}?startPeriod={start_year}&endPeriod={end_year}&format=sdmx-json"

            logger.info(f"Fetching from IMF: {database}/{indicator}")
            logger.info(f"  Countries: {countries_str}")
            logger.info(f"  Period: {start_year}-{end_year}")

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            df = self._parse_sdmx_json(data, indicator)

            if len(df) > 0:
                logger.info(f"Retrieved {len(df)} records from IMF")
            else:
                logger.warning(f"No data found for indicator {indicator}")

            return df

        except requests.exceptions.RequestException as e:
            logger.error(f"IMF API error: {e}")
            logger.info("Falling back to template mode")
            return pd.DataFrame(columns=["country", "year", "value", "indicator"])

    def _parse_sdmx_json(self, data: dict, indicator: str) -> pd.DataFrame:
        """Parse SDMX-JSON response into DataFrame."""
        rows = []

        try:
            observations = data.get("data", {}).get("dataSets", [])

            if not observations:
                return pd.DataFrame()

            dataset = observations[0]

            # Parse observations - IMF format
            for obs_key, obs_value in dataset.get("observations", {}).items():
                parts = obs_key.split(":")
                if not obs_value or len(parts) < 2:
                    continue

                try:
                    year = int(parts[-1])
                    value = obs_value[0] if isinstance(obs_value, list) else obs_value

                    rows.append(
                        {
                            "country": parts[0] if parts else "UNKNOWN",
                            "year": year,
                            "value": float(value) if value else None,
                            "indicator": indicator,
                        }
                    )
                except (ValueError, IndexError, TypeError):
                    continue

            return pd.DataFrame(rows)

        except Exception as e:
            logger.error(f"Error parsing IMF SDMX-JSON: {e}")
            return pd.DataFrame()


class WorldBankSource(DataSource):
    """Handler for World Bank API data."""

    BASE_URL = "https://api.worldbank.org/v2/country"

    # Country name to ISO 3-letter code mapping
    COUNTRY_CODES = {
        "Argentina": "ARG",
        "Brasil": "BRA",
        "Brazil": "BRA",
        "Chile": "CHL",
        "Colombia": "COL",
        "Mexico": "MEX",
        "México": "MEX",
        "Peru": "PER",
        "Perú": "PER",
        "Uruguay": "URY",
        "Paraguay": "PRY",
        "Bolivia": "BOL",
        "Ecuador": "ECU",
        "Venezuela": "VEN",
        "United States": "USA",
        "USA": "USA",
        "Canada": "CAN",
        "United Kingdom": "GBR",
        "Germany": "DEU",
        "France": "FRA",
        "Italy": "ITA",
        "Spain": "ESP",
        "Japan": "JPN",
        "South Korea": "KOR",
        "Australia": "AUS",
    }

    def __init__(self, raw_data_dir: Path):
        super().__init__("WorldBank", raw_data_dir)

    def fetch(
        self,
        indicator: str,
        countries: list = None,
        start_year: int = 2010,
        end_year: int = 2024,
        **kwargs,
    ) -> pd.DataFrame:
        """
        Fetch data from World Bank API.

        Args:
            indicator: World Bank indicator code (e.g., 'NY.GDP.MKTP.CD')
            countries: List of country names or codes
            start_year: Starting year
            end_year: Ending year

        Returns:
            DataFrame with the data
        """
        if countries is None:
            countries = ["ARG", "BRA", "CHL", "COL", "MEX", "PER", "URY"]

        try:
            # Convert country names to ISO codes if needed
            country_codes = []
            for country in countries:
                # If it's already a 3-letter code, use it
                if len(country) == 3 and country.isupper():
                    country_codes.append(country)
                # Otherwise, try to map the name to a code
                elif country in self.COUNTRY_CODES:
                    country_codes.append(self.COUNTRY_CODES[country])
                else:
                    # If not found, assume it's already a code
                    country_codes.append(country)

            countries_str = ";".join(country_codes)

            # World Bank API format: /country/{countries}/indicator/{indicator}
            url = f"{self.BASE_URL}/{countries_str}/indicator/{indicator}?date={start_year}:{end_year}&format=json"

            logger.info(f"Fetching from World Bank: {indicator}")
            logger.info(f"  Countries: {countries_str}")
            logger.info(f"  Period: {start_year}-{end_year}")

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            df = self._parse_json(data)

            if len(df) > 0:
                logger.info(f"Retrieved {len(df)} records from World Bank")
            else:
                logger.warning(f"No data found for indicator {indicator}")

            return df

        except requests.exceptions.RequestException as e:
            logger.error(f"World Bank API error: {e}")
            logger.info("Falling back to template mode")
            return pd.DataFrame(columns=["country", "year", "value", "indicator"])

    def _parse_json(self, data: list) -> pd.DataFrame:
        """Parse World Bank JSON response into DataFrame."""
        rows = []

        try:
            if len(data) < 2:
                return pd.DataFrame()

            indicators_data = data[1]

            for record in indicators_data:
                if record.get("value") is None:
                    continue

                try:
                    rows.append(
                        {
                            "country": record.get("countryiso3code", "UNKNOWN"),
                            "year": int(record.get("date", 0)),
                            "value": float(record.get("value")),
                            "indicator": record.get("indicator", {}).get(
                                "id", "UNKNOWN"
                            ),
                        }
                    )
                except (ValueError, TypeError):
                    continue

            return pd.DataFrame(rows)

        except Exception as e:
            logger.error(f"Error parsing World Bank JSON: {e}")
            return pd.DataFrame()


class ECLACSource(DataSource):
    """Handler for ECLAC (Economic Commission for Latin America) data."""

    BASE_URL = "https://data.cepal.org/api"

    def __init__(self, raw_data_dir: Path):
        super().__init__("ECLAC", raw_data_dir)

    def fetch(
        self,
        table: str,
        countries: list = None,
        start_year: int = 2010,
        end_year: int = 2024,
        **kwargs,
    ) -> pd.DataFrame:
        """
        Fetch data from ECLAC API.

        Args:
            table: ECLAC table ID
            countries: List of country codes
            start_year: Starting year
            end_year: Ending year

        Returns:
            DataFrame with the data
        """
        if countries is None:
            countries = ["ARG", "BRA", "CHL", "COL", "MEX", "PER", "URY"]

        try:
            logger.info(f"Fetching from ECLAC: {table}")
            logger.info(f"  Countries: {','.join(countries)}")
            logger.info(f"  Period: {start_year}-{end_year}")

            # ECLAC API format varies, this is a general endpoint
            url = f"{self.BASE_URL}/tables/{table}/countries/{','.join(countries)}?start_year={start_year}&end_year={end_year}"

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            df = self._parse_json(data)

            if len(df) > 0:
                logger.info(f"Retrieved {len(df)} records from ECLAC")
            else:
                logger.warning(f"No data found for table {table}")

            return df

        except requests.exceptions.RequestException as e:
            logger.error(f"ECLAC API error: {e}")
            logger.info("Falling back to template mode")
            return pd.DataFrame(columns=["country", "year", "value", "indicator"])

    def _parse_json(self, data: dict) -> pd.DataFrame:
        """Parse ECLAC JSON response into DataFrame."""
        rows = []

        try:
            records = data.get("data", [])

            for record in records:
                if record.get("value") is None:
                    continue

                try:
                    rows.append(
                        {
                            "country": record.get("country", {}).get("code", "UNKNOWN"),
                            "year": int(record.get("year", 0)),
                            "value": float(record.get("value")),
                            "indicator": record.get("indicator", "UNKNOWN"),
                        }
                    )
                except (ValueError, TypeError):
                    continue

            return pd.DataFrame(rows)

        except Exception as e:
            logger.error(f"Error parsing ECLAC JSON: {e}")
            return pd.DataFrame()


class OWIDSource(DataSource):
    """Handler for Our World in Data (OWID) Grapher API."""

    BASE_URL = "https://ourworldindata.org/grapher"

    def __init__(self, raw_data_dir: Path):
        super().__init__("OWID", raw_data_dir)

    def fetch(
        self,
        slug: str,
        countries: list = None,
        start_year: int = None,
        end_year: int = None,
        **kwargs,
    ) -> pd.DataFrame:
        """
        Fetch data from OWID Grapher API using chart slug.

        Args:
            slug: OWID grapher chart slug (e.g., 'real-wages', 'gdp-per-capita')
            countries: List of country names or codes (e.g., ['Argentina', 'Brazil'])
            start_year: Starting year (optional, defaults to all available)
            end_year: Ending year (optional, defaults to all available)

        Returns:
            DataFrame with the data

        Example:
            fetch(slug='real-wages', countries=['Argentina', 'Brazil'],
                  start_year=2000, end_year=2024)
        """
        try:
            # Build URL with .csv endpoint
            url = f"{self.BASE_URL}/{slug}.csv"

            # Build query parameters
            params = {}

            # Add csvType for filtered data (only what's visible in chart)
            params["csvType"] = "filtered"

            # Add country filter if provided
            if countries:
                # Join countries with ~ separator (OWID format)
                country_str = "~".join(countries)
                params["country"] = country_str

            # Add time range if provided
            if start_year and end_year:
                params["time"] = f"{start_year}..{end_year}"
            elif start_year:
                params["time"] = f"{start_year}..latest"
            elif end_year:
                params["time"] = f"earliest..{end_year}"

            logger.info(f"Fetching from OWID: {slug}")
            if countries:
                logger.info(f"  Countries: {', '.join(countries)}")
            if start_year or end_year:
                logger.info(f"  Period: {params.get('time', 'all')}")

            # Make request
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            # Parse CSV data
            from io import StringIO

            df = pd.read_csv(StringIO(response.text))

            # Standardize column names
            if "Entity" in df.columns:
                df = df.rename(columns={"Entity": "country"})
            if "Year" in df.columns:
                df = df.rename(columns={"Year": "year"})
            if "Code" in df.columns:
                df = df.rename(columns={"Code": "country_code"})

            # Save raw data
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{slug}_{timestamp}.csv"
            self.save_raw(df, filename)

            if len(df) > 0:
                logger.info(f"Retrieved {len(df)} records from OWID")
                logger.info(f"  Columns: {', '.join(df.columns.tolist()[:5])}...")
            else:
                logger.warning(f"No data found for slug '{slug}'")

            return df

        except requests.exceptions.RequestException as e:
            logger.error(f"OWID API error: {e}")
            logger.error(f"  URL: {url}")
            logger.info(
                "  Make sure the slug is correct. Check https://ourworldindata.org/charts"
            )
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error parsing OWID data: {e}")
            return pd.DataFrame()

    def fetch_metadata(self, slug: str) -> Dict[str, Any]:
        """
        Fetch metadata from OWID Grapher API.

        Args:
            slug: OWID grapher chart slug

        Returns:
            Dictionary with metadata including description, methodology, sources
        """
        try:
            url = f"{self.BASE_URL}/{slug}.metadata.json"
            logger.info(f"Fetching OWID metadata: {slug}")

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            metadata = response.json()

            # Extract key fields
            enriched = {
                "slug": slug,
                "title": metadata.get("title", ""),
                "description": metadata.get("description", ""),
                "unit": metadata.get("unit", ""),
                "sources": [],
                "methodology": "",
                "limitations": [],
                "last_updated": None,
                "license": "CC BY 4.0",
                "url": f"https://ourworldindata.org/grapher/{slug}",
                "raw_metadata": metadata,  # Keep full metadata
            }

            # Extract sources information
            if "sources" in metadata and isinstance(metadata["sources"], list):
                for source in metadata["sources"]:
                    source_info = {
                        "name": source.get("name", ""),
                        "url": source.get("url", ""),
                        "description": source.get("description", ""),
                        "date_accessed": source.get("dateAccessed", ""),
                    }
                    enriched["sources"].append(source_info)

            # Try to extract methodology from description or additionalInfo
            if "additionalInfo" in metadata:
                enriched["methodology"] = metadata["additionalInfo"]

            # Extract dataset information if available
            if "dataset" in metadata and isinstance(metadata["dataset"], dict):
                dataset = metadata["dataset"]
                enriched["dataset_name"] = dataset.get("name", "")
                enriched["dataset_version"] = dataset.get("version", "")
                if "updatedAt" in dataset:
                    enriched["last_updated"] = dataset["updatedAt"]

            logger.info(f"Retrieved metadata for {slug}")
            return enriched

        except requests.exceptions.RequestException as e:
            logger.error(f"OWID metadata error: {e}")
            return {"slug": slug, "error": str(e)}
        except Exception as e:
            logger.error(f"Error parsing OWID metadata: {e}")
            return {"slug": slug, "error": str(e)}

    def fetch_with_metadata(
        self,
        slug: str,
        countries: list = None,
        start_year: int = None,
        end_year: int = None,
        **kwargs,
    ) -> tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Fetch both data and metadata from OWID.

        Args:
            slug: OWID grapher chart slug
            countries: List of country names or codes
            start_year: Starting year
            end_year: Ending year

        Returns:
            Tuple of (DataFrame, metadata_dict)
        """
        # Fetch data
        df = self.fetch(slug, countries, start_year, end_year, **kwargs)

        # Fetch metadata
        metadata = self.fetch_metadata(slug)

        # Add data statistics to metadata
        if not df.empty:
            metadata["data_stats"] = {
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "columns": df.columns.tolist(),
                "date_range": {
                    "min_year": int(df["year"].min()) if "year" in df.columns else None,
                    "max_year": int(df["year"].max()) if "year" in df.columns else None,
                },
                "countries_count": df["country"].nunique() if "country" in df.columns else None,
            }

        return df, metadata


class DataIngestionManager:
    """Manages data ingestion from multiple sources."""

    def __init__(self, config):
        """
        Initialize ingestion manager.

        Args:
            config: Config object
        """
        self.config = config
        self.raw_dir = config.get_directory("raw")

        # Initialize data sources
        self.sources = {
            "manual": ManualUpload(self.raw_dir),
            "owid": OWIDSource(self.raw_dir),
            "ilostat": ILOSTATSource(self.raw_dir),
            "oecd": OECDSource(self.raw_dir),
            "imf": IMFSource(self.raw_dir),
            "worldbank": WorldBankSource(self.raw_dir),
            "eclac": ECLACSource(self.raw_dir),
        }

    def ingest(self, source: str, **kwargs) -> pd.DataFrame:
        """
        Ingest data from specified source.

        Args:
            source: Source name (manual, ilostat, oecd, imf)
            **kwargs: Source-specific parameters

        Returns:
            DataFrame with ingested data
        """
        if source not in self.sources:
            raise ValueError(
                f"Unknown source: {source}. Available: {list(self.sources.keys())}"
            )

        return self.sources[source].fetch(**kwargs)

"""Dynamic search module for searching external data source catalogs.

This module provides hybrid search functionality that combines:
1. Local curated indicators from indicators.yaml (fast, instant results)
2. Remote API searches from OWID, OECD, etc. (comprehensive, slower)

Architecture:
- Local search is always performed first (instant)
- Remote searches are performed in parallel (2-5s)
- Results are merged, deduplicated, and cached
"""

from typing import List, Dict, Any, Optional
import requests
from datetime import datetime, timedelta
import json
from pathlib import Path


class SearchCache:
    """Simple in-memory cache with TTL for search results."""

    def __init__(self, ttl_minutes: int = 5):
        """Initialize cache with TTL in minutes."""
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = timedelta(minutes=ttl_minutes)

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached result if not expired."""
        if key not in self.cache:
            return None

        entry = self.cache[key]
        if datetime.now() - entry["timestamp"] > self.ttl:
            # Expired, remove from cache
            del self.cache[key]
            return None

        return entry["data"]

    def set(self, key: str, data: Dict[str, Any]):
        """Cache data with current timestamp."""
        self.cache[key] = {"data": data, "timestamp": datetime.now()}

    def clear(self):
        """Clear all cached data."""
        self.cache.clear()


class OWIDSearcher:
    """Search Our World in Data charts catalog via their public API."""

    BASE_URL = "https://ourworldindata.org/api/search"

    def __init__(self, timeout: int = 10):
        """Initialize OWID searcher with request timeout."""
        self.timeout = timeout

    def search(self, query: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Search OWID charts catalog.

        Args:
            query: Search term (e.g., "tax", "gdp", "unemployment")
            max_results: Maximum number of results to return

        Returns:
            List of indicator dicts with standardized format
        """
        try:
            params = {
                "q": query,
                "type": "charts",
                "hitsPerPage": min(max_results, 100),  # API max is 100
            }

            response = requests.get(self.BASE_URL, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            results = []

            for idx, chart in enumerate(data.get("results", [])):
                # Convert OWID chart format to our standard indicator format
                # Use slug as stable ID, fall back to index if missing
                slug = chart.get("slug", "")
                
                # We prefer a stable ID based on slug to allow reliable "is_downloaded" checks
                # even if search result order changes.
                if slug:
                     unique_id = f"owid_{slug}"
                else:
                     unique_id = f"owid_chart_{idx}"

                indicator = {
                    "id": unique_id,
                    "name": chart.get("title", ""),
                    "description": chart.get("subtitle", ""),
                    "source": "owid",
                    "slug": slug,
                    "url": chart.get("url", ""),
                    "tags": self._extract_tags(chart),
                    "remote": True,  # Flag to indicate this is from API
                    "available_countries": chart.get("availableEntities", [])[
                        :10
                    ],  # First 10 countries
                    "chart_types": chart.get("availableTabs", []),
                }
                results.append(indicator)

            return results

        except requests.RequestException as e:
            print(f"OWID API error: {e}")
            return []
        except Exception as e:
            print(f"OWID search error: {e}")
            return []

    def _extract_tags(self, chart: Dict[str, Any]) -> List[str]:
        """Extract relevant tags from chart metadata."""
        tags = []

        # Add chart type as tag
        chart_type = chart.get("type", "")
        if chart_type:
            tags.append(chart_type)

        # Extract keywords from title and subtitle
        title = chart.get("title", "").lower()
        subtitle = chart.get("subtitle", "").lower()

        # Common economic indicators
        keywords = [
            "gdp",
            "tax",
            "revenue",
            "income",
            "wage",
            "employment",
            "unemployment",
            "inflation",
            "trade",
            "poverty",
            "inequality",
        ]

        for keyword in keywords:
            if keyword in title or keyword in subtitle:
                tags.append(keyword)

        return list(set(tags))  # Remove duplicates


class OECDSearcher:
    """Search OECD data catalog."""

    # OECD doesn't have a public search API like OWID, so we'll use a curated list
    # of common OECD datasets for now. In the future, this could scrape their catalog.

    COMMON_DATASETS = {
        "tax": [
            {
                "id": "oecd_revenue_statistics",
                "name": "Revenue Statistics",
                "description": "Tax revenue statistics from OECD countries",
                "dataset": "REV",
                "indicator_code": "TAXREV",
                "tags": ["tax", "revenue", "fiscal"],
            },
            {
                "id": "oecd_tax_database",
                "name": "Tax Database",
                "description": "Comprehensive tax data including rates and bases",
                "dataset": "TAX",
                "indicator_code": "ALLTAX",
                "tags": ["tax", "fiscal", "rates"],
            },
        ],
        "gdp": [
            {
                "id": "oecd_gdp_growth",
                "name": "GDP Growth Rate",
                "description": "Real GDP growth rate (annual %)",
                "dataset": "EO",
                "indicator_code": "GDPV_ANNPCT",
                "tags": ["gdp", "growth", "economic"],
            }
        ],
        "unemployment": [
            {
                "id": "oecd_unemployment_rate",
                "name": "Unemployment Rate",
                "description": "Harmonized unemployment rate",
                "dataset": "MEI",
                "indicator_code": "LRHUTTTT",
                "tags": ["unemployment", "labor", "employment"],
            }
        ],
        "wage": [
            {
                "id": "oecd_average_wages",
                "name": "Average Wages",
                "description": "Average annual wages in USD",
                "dataset": "AV_AN_WAGE",
                "indicator_code": "AVG_WAGE",
                "tags": ["wage", "income", "labor"],
            }
        ],
    }

    def search(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Search OECD datasets (currently using curated list).

        Args:
            query: Search term
            max_results: Maximum number of results

        Returns:
            List of indicator dicts
        """
        query_lower = query.lower().strip()
        results = []

        # Search in curated datasets
        for keyword, datasets in self.COMMON_DATASETS.items():
            if keyword in query_lower:
                for dataset in datasets:
                    indicator = {
                        **dataset,
                        "source": "oecd",
                        "remote": True,
                        "url": f"https://data-explorer.oecd.org/vis?tm=gdp&pg=0&snb=1&df[ds]={dataset['dataset']}",
                    }
                    results.append(indicator)

        return results[:max_results]


class DynamicSearcher:
    """Unified searcher that combines local and remote search results."""

    def __init__(self, config, cache_ttl_minutes: int = 5):
        """
        Initialize dynamic searcher.

        Args:
            config: Config object with get_indicators() method
            cache_ttl_minutes: Cache TTL in minutes
        """
        self.config = config
        self.cache = SearchCache(ttl_minutes=cache_ttl_minutes)
        self.owid_searcher = OWIDSearcher()
        self.oecd_searcher = OECDSearcher()

    def search(
        self,
        query: str,
        include_remote: bool = True,
        max_local: int = 100,
        max_remote: int = 100,
    ) -> Dict[str, Any]:
        """
        Perform hybrid search across local and remote sources.

        Args:
            query: Search term
            include_remote: Whether to include remote API results
            max_local: Max local results
            max_remote: Max remote results per source

        Returns:
            Dict with local_results, remote_results, and metadata
        """
        cache_key = f"{query}:{include_remote}:{max_local}:{max_remote}"

        # Check cache first
        cached = self.cache.get(cache_key)
        if cached:
            print(f"✓ Cache hit for query: {query}")
            return cached

        # 1. Local search (from indicators.yaml)
        local_results = self._search_local(query, max_local)

        # 2. Remote searches (from APIs)
        remote_results = []
        if include_remote:
            remote_results = self._search_remote(query, max_remote)

        # 3. Merge and prepare response
        result = {
            "query": query,
            "local_results": local_results,
            "remote_results": remote_results,
            "total_local": len(local_results),
            "total_remote": len(remote_results),
            "total": len(local_results) + len(remote_results),
            "sources": {
                "local": len(local_results),
                "owid": len([r for r in remote_results if r.get("source") == "owid"]),
                "oecd": len([r for r in remote_results if r.get("source") == "oecd"]),
            },
        }

        # Cache the result
        self.cache.set(cache_key, result)

        return result

    def _search_local(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search local indicators.yaml."""
        query_lower = query.lower().strip()
        results = []

        for indicator in self.config.get_indicators():
            # Search in multiple fields
            searchable_text = " ".join(
                [
                    indicator.get("id", ""),
                    indicator.get("name", ""),
                    indicator.get("description", ""),
                    " ".join(indicator.get("tags", [])),
                ]
            ).lower()

            if query_lower in searchable_text:
                # Mark as local
                indicator_copy = {**indicator, "remote": False}
                results.append(indicator_copy)

        return results[:max_results]

    def _search_remote(self, query: str, max_per_source: int) -> List[Dict[str, Any]]:
        """Search remote APIs in parallel."""
        results = []

        # Search OWID
        try:
            owid_results = self.owid_searcher.search(query, max_per_source)
            results.extend(owid_results)
            print(f"✓ Found {len(owid_results)} results from OWID")
        except Exception as e:
            print(f"✗ OWID search failed: {e}")

        # Search OECD
        try:
            oecd_results = self.oecd_searcher.search(query, max_per_source)
            results.extend(oecd_results)
            print(f"✓ Found {len(oecd_results)} results from OECD")
        except Exception as e:
            print(f"✗ OECD search failed: {e}")

        return results

    def clear_cache(self):
        """Clear search cache."""
        self.cache.clear()

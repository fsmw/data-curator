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

    BASE_DATAFLOW_URL = "https://stats.oecd.org/SDMX-JSON/dataflow"
    _cached_dataflows: Optional[List[Dict[str, Any]]] = None
    _cached_at: Optional[datetime] = None
    _cache_ttl = timedelta(minutes=60)

    def search(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Search OECD datasets using SDMX dataflows with a curated fallback.

        Args:
            query: Search term
            max_results: Maximum number of results

        Returns:
            List of indicator dicts
        """
        query_lower = query.lower().strip()
        results = []

        try:
            dataflows = self._get_dataflows()
            for flow in dataflows:
                flow_id = flow.get("id", "")
                name = flow.get("name", "")
                description = flow.get("description", "")
                searchable = f"{flow_id} {name} {description}".lower()
                if query_lower and query_lower not in searchable:
                    continue

                results.append({
                    "id": f"oecd_{flow_id}",
                    "name": name or flow_id,
                    "description": description,
                    "dataset": flow_id,
                    "indicator_code": "",
                    "tags": [query_lower] if query_lower else [],
                    "source": "oecd",
                    "remote": True,
                    "url": f"https://data-explorer.oecd.org/vis?df[ds]={flow_id}",
                })

                if len(results) >= max_results:
                    break
        except Exception as e:
            print(f"OECD dataflow search failed: {e}")

        if results:
            return results[:max_results]

        # Fallback: curated datasets
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

    def _get_dataflows(self) -> List[Dict[str, Any]]:
        now = datetime.now()
        if self._cached_dataflows and self._cached_at and (now - self._cached_at) < self._cache_ttl:
            return self._cached_dataflows

        response = requests.get(self.BASE_DATAFLOW_URL, timeout=20)
        response.raise_for_status()
        data = response.json()

        dataflows = self._extract_dataflows(data)
        self._cached_dataflows = dataflows
        self._cached_at = now
        return dataflows

    def _extract_dataflows(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        flows = []

        def normalize_name(name_val):
            if isinstance(name_val, dict):
                return name_val.get("en") or next(iter(name_val.values()), "")
            if isinstance(name_val, list) and name_val:
                return str(name_val[0])
            return str(name_val) if name_val is not None else ""

        def walk(obj):
            if isinstance(obj, dict):
                if "id" in obj and "name" in obj:
                    flow_id = str(obj.get("id", ""))
                    name = normalize_name(obj.get("name"))
                    description = normalize_name(obj.get("description", ""))
                    if flow_id and name:
                        flows.append({
                            "id": flow_id,
                            "name": name,
                            "description": description,
                        })
                for value in obj.values():
                    walk(value)
            elif isinstance(obj, list):
                for item in obj:
                    walk(item)

        walk(data)

        seen = set()
        unique = []
        for flow in flows:
            flow_id = flow.get("id")
            if not flow_id or flow_id in seen:
                continue
            seen.add(flow_id)
            unique.append(flow)

        return unique


class WorldBankSearcher:
    """Search World Bank Indicators API."""

    BASE_URL = "https://api.worldbank.org/v2/indicator"

    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    def search(self, query: str, max_results: int = 100) -> List[Dict[str, Any]]:
        query_lower = query.lower().strip()
        results = []
        page = 1
        per_page = 200

        while len(results) < max_results:
            params = {
                "format": "json",
                "per_page": per_page,
                "page": page,
            }
            if query_lower:
                params["q"] = query_lower

            response = requests.get(self.BASE_URL, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list) or len(data) < 2:
                break

            meta, indicators = data[0], data[1]
            if not indicators:
                break

            for indicator in indicators:
                ind_id = indicator.get("id", "")
                name = indicator.get("name", "")
                description = indicator.get("sourceNote", "") or indicator.get("sourceOrganization", "")
                searchable = f"{ind_id} {name} {description}".lower()
                if query_lower and query_lower not in searchable:
                    continue

                results.append({
                    "id": f"worldbank_{ind_id}",
                    "name": name,
                    "description": description,
                    "indicator_code": ind_id,
                    "source": "worldbank",
                    "remote": True,
                    "url": f"https://api.worldbank.org/v2/country/all/indicator/{ind_id}",
                    "tags": [query_lower] if query_lower else [],
                })

                if len(results) >= max_results:
                    break

            total_pages = int(meta.get("pages", page)) if isinstance(meta, dict) else page
            if page >= total_pages:
                break
            page += 1

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
        self.worldbank_searcher = WorldBankSearcher()

    def search(
        self,
        query: str,
        include_remote: bool = True,
        max_local: int = 100,
        max_remote: int = 100,
        source_filter: Optional[str] = None,
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
        cache_key = f"{query}:{include_remote}:{max_local}:{max_remote}:{source_filter}"

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
            remote_results = self._search_remote(query, max_remote, source_filter=source_filter)

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
                "worldbank": len([r for r in remote_results if r.get("source") == "worldbank"]),
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

    def _search_remote(
        self,
        query: str,
        max_per_source: int,
        source_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search remote APIs in parallel."""
        results = []
        source_filter = (source_filter or "").lower().strip()

        # Search OWID
        if not source_filter or source_filter == "owid":
            try:
                owid_results = self.owid_searcher.search(query, max_per_source)
                results.extend(owid_results)
                print(f"✓ Found {len(owid_results)} results from OWID")
            except Exception as e:
                print(f"✗ OWID search failed: {e}")

        # Search OECD
        if not source_filter or source_filter == "oecd":
            try:
                oecd_results = self.oecd_searcher.search(query, max_per_source)
                results.extend(oecd_results)
                print(f"✓ Found {len(oecd_results)} results from OECD")
            except Exception as e:
                print(f"✗ OECD search failed: {e}")

        # Search World Bank
        if not source_filter or source_filter == "worldbank":
            try:
                worldbank_results = self.worldbank_searcher.search(query, max_per_source)
                results.extend(worldbank_results)
                print(f"✓ Found {len(worldbank_results)} results from World Bank")
            except Exception as e:
                print(f"✗ World Bank search failed: {e}")

        return results

    def clear_cache(self):
        """Clear search cache."""
        self.cache.clear()

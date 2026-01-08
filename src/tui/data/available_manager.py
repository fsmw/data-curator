"""Available data manager for discovering indicators from configuration."""

from pathlib import Path
from typing import Dict, List, Optional
import yaml
from ..config import INDICATORS_FILE


class AvailableDataManager:
    """Manage reading available indicators from configuration files."""

    def __init__(self):
        self.indicators_file = INDICATORS_FILE
        self._indicators_cache: Optional[Dict] = None

    def load_indicators(self) -> Dict:
        """Load indicators from indicators.yaml."""
        if self._indicators_cache:
            return self._indicators_cache

        if not self.indicators_file.exists():
            return {}

        try:
            with open(self.indicators_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                self._indicators_cache = data
                return data
        except Exception:
            return {}

    def get_sources(self) -> List[str]:
        """Get list of available data sources."""
        indicators = self.load_indicators()
        sources = set()

        if "indicators" in indicators:
            for ind_data in indicators["indicators"].values():
                if "source" in ind_data:
                    sources.add(ind_data["source"])

        return sorted(list(sources))

    def get_indicators_by_source(self, source: str) -> List[Dict]:
        """Get all indicators for a specific source."""
        indicators = self.load_indicators()
        result = []

        if "indicators" not in indicators:
            return result

        for indicator_id, indicator_data in indicators["indicators"].items():
            if indicator_data.get("source") == source:
                result.append(
                    self._format_indicator(indicator_id, indicator_data)
                )

        return sorted(result, key=lambda x: x["name"])

    def get_all_indicators(self) -> List[Dict]:
        """Get all available indicators."""
        indicators = self.load_indicators()
        result = []

        if "indicators" not in indicators:
            return result

        for indicator_id, indicator_data in indicators["indicators"].items():
            result.append(self._format_indicator(indicator_id, indicator_data))

        return sorted(result, key=lambda x: x["name"])

    def get_indicator_details(self, indicator_id: str) -> Optional[Dict]:
        """Get detailed information about a specific indicator."""
        indicators = self.load_indicators()

        if "indicators" not in indicators:
            return None

        if indicator_id not in indicators["indicators"]:
            return None

        return self._format_indicator(
            indicator_id, indicators["indicators"][indicator_id]
        )

    def search_indicators(self, query: str) -> List[Dict]:
        """Search indicators by name or description."""
        indicators = self.get_all_indicators()
        query_lower = query.lower()

        results = []
        for indicator in indicators:
            if (
                query_lower in indicator["name"].lower()
                or query_lower in indicator.get("description", "").lower()
            ):
                results.append(indicator)

        return results

    def _format_indicator(self, indicator_id: str, data: Dict) -> Dict:
        """Format indicator data for display."""
        return {
            "id": indicator_id,
            "name": data.get("name", indicator_id),
            "source": data.get("source", "unknown"),
            "topic": data.get("topic", ""),
            "description": data.get("description", ""),
            "countries": data.get("countries", []),
            "years_available": data.get("years_available", ""),
            "dataset_id": data.get("dataset_id", ""),
            "indicator_code": data.get("indicator_code", ""),
        }

    def get_source_info(self, source: str) -> Dict:
        """Get information about a data source."""
        indicators = self.load_indicators()

        if "sources" in indicators and source in indicators["sources"]:
            return indicators["sources"][source]

        # Default source info
        return {
            "name": source,
            "description": f"Data source: {source}",
            "url": "",
            "type": "",
        }

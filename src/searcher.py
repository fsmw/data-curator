"""Refactored search - simple tag-based search without rigid topics."""

from typing import List, Dict, Any


class IndicatorSearcher:
    """Search indicators by tags and source - no rigid topic structure."""

    def __init__(self, config):
        """Initialize searcher with config."""
        self.config = config
        # Get flat list of indicators instead of nested dict
        self.indicators = config.get_indicators()

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search indicators by any term - searches id, name, description, and tags.

        Args:
            query: Search term (e.g., "tax", "wages", "inflation")

        Returns:
            List of matching indicators
        """
        if not query:
            return []

        query_lower = query.lower().strip()
        results = []

        for indicator in self.indicators:
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
                results.append(indicator)

        return results

    def search_by_source(self, source: str) -> List[Dict[str, Any]]:
        """
        Get all indicators from a specific source.

        Args:
            source: Source name (owid, oecd, ilostat, imf, worldbank, eclac)

        Returns:
            List of indicators from that source
        """
        source_lower = source.lower().strip()
        return [
            ind
            for ind in self.indicators
            if ind.get("source", "").lower() == source_lower
        ]

    def search_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """
        Search indicators by specific tag.

        Args:
            tag: Tag to search for (e.g., "wages", "fiscal", "inequality")

        Returns:
            List of indicators with that tag
        """
        tag_lower = tag.lower().strip()
        results = []

        for indicator in self.indicators:
            tags = [t.lower() for t in indicator.get("tags", [])]
            if tag_lower in tags:
                results.append(indicator)

        return results

    def list_sources(self) -> List[str]:
        """Get list of all available sources."""
        sources = set(ind.get("source", "unknown") for ind in self.indicators)
        return sorted(list(sources))

    def list_tags(self) -> List[str]:
        """Get list of all unique tags."""
        tags = set()
        for ind in self.indicators:
            tags.update(ind.get("tags", []))
        return sorted(list(tags))

    def get_indicator_by_id(self, indicator_id: str) -> Dict[str, Any]:
        """
        Get specific indicator by ID.

        Args:
            indicator_id: Indicator ID (e.g., "tax_revenue_owid")

        Returns:
            Indicator dict or empty dict if not found
        """
        for ind in self.indicators:
            if ind.get("id") == indicator_id:
                return ind
        return {}

    def format_results_table(
        self, results: List[Dict[str, Any]], verbose: bool = False
    ) -> str:
        """
        Format search results for CLI display.

        Args:
            results: List of indicator dicts
            verbose: Show detailed information

        Returns:
            Formatted table string
        """
        if not results:
            return "No results found."

        if verbose:
            output = []
            for r in results:
                output.append(f"\n📊 {r.get('name', 'N/A')} ({r.get('id', 'N/A')})")
                output.append(f"   Source: {r.get('source', 'N/A').upper()}")
                output.append(f"   Description: {r.get('description', 'N/A')}")
                output.append(f"   Tags: {', '.join(r.get('tags', []))}")
                if r.get("url"):
                    output.append(f"   URL: {r['url']}")
            return "\n".join(output)
        else:
            header = f"{'ID':<30} {'Name':<35} {'Source':<10}"
            separator = "=" * 80
            rows = []
            for r in results:
                rows.append(
                    f"{r.get('id', 'N/A'):<30} {r.get('name', 'N/A'):<35} {r.get('source', 'N/A').upper():<10}"
                )
            return f"{separator}\n{header}\n{separator}\n" + "\n".join(rows)

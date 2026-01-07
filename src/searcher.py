"""Search and discovery utilities for economic indicators."""

from typing import List, Dict, Any
import re


class IndicatorSearcher:
    """Search and discover available economic indicators."""
    
    def __init__(self, config):
        """
        Initialize searcher.
        
        Args:
            config: Config object with indicators loaded
        """
        self.config = config
        self.indicators = config.get_indicators()
        self.topic_indicators = config.indicators.get('topic_indicators', {})
    
    def search(self, query: str, by_topic: bool = False) -> List[Dict[str, Any]]:
        """
        Search for indicators by name or description.
        
        Args:
            query: Search term (name, description, or keyword)
            by_topic: If True, search only in topics
            
        Returns:
            List of matching indicators
        """
        query_lower = query.lower()
        results = []
        
        if by_topic and query_lower in self.topic_indicators:
            # Return all indicators for this topic
            indicator_names = self.topic_indicators[query_lower]
            for name in indicator_names:
                if name in self.indicators:
                    results.append({
                        'name': name,
                        **self.indicators[name]
                    })
            return results
        
        # Search in all indicators
        for name, indicator_info in self.indicators.items():
            # Search in name
            if query_lower in name.lower():
                results.append({
                    'name': name,
                    **indicator_info
                })
                continue
            
            # Search in description
            description = indicator_info.get('description', '').lower()
            if query_lower in description:
                results.append({
                    'name': name,
                    **indicator_info
                })
                continue
            
            # Search in source
            source = indicator_info.get('source', '').lower()
            if query_lower in source:
                results.append({
                    'name': name,
                    **indicator_info
                })
        
        return results
    
    def search_by_topic(self, topic: str) -> List[Dict[str, Any]]:
        """
        Get all indicators for a specific topic.
        
        Args:
            topic: Topic name
            
        Returns:
            List of indicators in topic
        """
        if topic not in self.topic_indicators:
            return []
        
        indicator_names = self.topic_indicators[topic]
        results = []
        
        for name in indicator_names:
            if name in self.indicators:
                results.append({
                    'name': name,
                    **self.indicators[name]
                })
        
        return results
    
    def search_by_source(self, source: str) -> List[Dict[str, Any]]:
        """
        Get all indicators from a specific source.
        
        Args:
            source: Source name (ilostat, oecd, imf)
            
        Returns:
            List of indicators from source
        """
        source_lower = source.lower()
        results = []
        
        for name, indicator_info in self.indicators.items():
            if indicator_info.get('source', '').lower() == source_lower:
                results.append({
                    'name': name,
                    **indicator_info
                })
        
        return results
    
    def list_topics(self) -> List[str]:
        """Get list of all available topics."""
        return list(self.topic_indicators.keys())
    
    def list_sources(self) -> List[str]:
        """Get list of all available sources."""
        sources = set()
        for indicator in self.indicators.values():
            sources.add(indicator.get('source', 'unknown'))
        return sorted(list(sources))
    
    def get_indicator_info(self, name: str) -> Dict[str, Any]:
        """
        Get detailed information about an indicator.
        
        Args:
            name: Indicator name
            
        Returns:
            Indicator details
        """
        return self.indicators.get(name, {})
    
    def format_search_result(self, indicator: Dict[str, Any], verbose: bool = False) -> str:
        """
        Format a search result for display.
        
        Args:
            indicator: Indicator dict
            verbose: Show detailed information
            
        Returns:
            Formatted string
        """
        name = indicator.get('name', 'N/A')
        desc = indicator.get('description', 'N/A')
        source = indicator.get('source', 'N/A').upper()
        
        if verbose:
            years = indicator.get('years', 'N/A')
            coverage = indicator.get('coverage', 'N/A')
            countries = indicator.get('countries', 'N/A')
            
            return f"""
📊 {name}
   Description: {desc}
   Source: {source}
   Years: {years}
   Coverage: {coverage}
   Countries: {countries}
"""
        else:
            return f"  • {name:<35} {desc:<50} [{source}]"
    
    def format_results_table(self, results: List[Dict[str, Any]], verbose: bool = False) -> str:
        """
        Format multiple search results as a table.
        
        Args:
            results: List of indicator dicts
            verbose: Show detailed information
            
        Returns:
            Formatted table string
        """
        if not results:
            return "No results found."
        
        if verbose:
            output = "\n".join(self.format_search_result(r, verbose=True) for r in results)
        else:
            header = f"{'Indicator':<35} {'Description':<50} {'Source'}"
            separator = "=" * 100
            rows = [self.format_search_result(r, verbose=False) for r in results]
            output = f"{separator}\n{header}\n{separator}\n" + "\n".join(rows)
        
        return output

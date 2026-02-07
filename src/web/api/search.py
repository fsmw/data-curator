"""
Search API endpoints.

Handles indicator search with hybrid local + remote capabilities.
"""

from flask import request, jsonify, Response
from config import Config
from searcher import IndicatorSearcher
from dynamic_search import DynamicSearcher
from src.logger import get_logger

from . import api_bp

logger = get_logger(__name__)


def check_indicator_downloaded(config: Config, indicator_id: str, source: str, slug: str = None, name: str = None) -> bool:
    """
    Check if an indicator has already been downloaded by querying the dataset catalog.
    Matches by ID, slug, or fuzzy name.
    """
    try:
        from dataset_catalog import DatasetCatalog
        catalog = DatasetCatalog(config)
        latest_datasets = catalog.latest_per_identifier()
        
        source = source.lower()
        
        # 1. Match by specific ID (or slug stored as ID)
        # Note: OWID IDs from search are like 'owid_slug_idx', but catalog stores 'slug' as ID.
        # So we check if catalog ID is contained in search ID or matches slug.
        for d in latest_datasets:
            if d.get("source") != source:
                continue
                
            # Normalize for comparison
            def normalize(s):
                return str(s).lower().replace("_", "-").replace(" ", "-")

            cat_id_norm = normalize(d.get("indicator_id", ""))
            cat_name_norm = normalize(d.get("indicator_name", ""))
            
            search_id_norm = normalize(indicator_id)
            slug_norm = normalize(slug) if slug else ""
            name_norm = normalize(name) if name else ""

            # Check all combinations
            if (cat_id_norm == search_id_norm or 
                (slug_norm and cat_id_norm == slug_norm) or
                (name_norm and cat_name_norm == name_norm)):
                return True
                
            # Fallback: check if slug is contained in ID (common if ID has suffix)
            if slug_norm and len(slug_norm) > 5 and slug_norm in cat_id_norm:
                return True

        return False
    except Exception as e:
        logger.error(f"Error checking downloaded status via catalog: {e}")
        return False



@api_bp.route("/search")
def search_api() -> Response:
    """
    Search API endpoint with hybrid local + remote search.

    Query params:
        q: Search query
        source: Filter by source (owid, oecd, etc.)
        topic: Filter by topic
        include_remote: Include remote API results (default: true)
    """
    query = request.args.get("q", "").strip()
    source_filter = request.args.get("source", "").lower().strip()
    topic_filter = request.args.get("topic", "").lower().strip()
    include_remote = request.args.get("include_remote", "true").lower() == "true"
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=25, type=int)
    page = max(page, 1)
    per_page = max(min(per_page, 100), 1)

    try:
        config = Config()
        all_results = []
        
        # 1. Local Search (IndicatorSearcher) - always runs if we have criteria
        local_searcher = IndicatorSearcher(config)
        if topic_filter:
            all_results.extend(local_searcher.search_by_topic(topic_filter))
        elif source_filter and not query:
            all_results.extend(local_searcher.search_by_source(source_filter))
        # If query is present, DynamicSearcher._search_local handles it usually, 
        # but let's rely on DynamicSearcher for the query part to avoid duplication
        
        # 2. Dynamic Search (Local + Remote) - runs if we have a query
        if query:
            dynamic_searcher = DynamicSearcher(config, cache_ttl_minutes=5)
            # We fetch everything (remote=True) and filter later
            dyn_results = dynamic_searcher.search(
                query,
                include_remote=include_remote,
                source_filter=source_filter or None,
            )
            
            # Map standard structure
            for r in dyn_results["local_results"] + dyn_results["remote_results"]:
                formatted = {
                    "id": r.get("id", ""),
                    "indicator": r.get("name", ""),
                    "source": r.get("source", "").lower(),
                    "description": r.get("description", ""),
                    "tags": ", ".join(r.get("tags", [])) if isinstance(r.get("tags", []), list) else r.get("tags", ""),
                    "remote": r.get("remote", False),
                    "slug": r.get("slug"),
                    "url": r.get("url"),
                    "indicator_code": r.get("indicator_code"),
                    "dataset": r.get("dataset"),
                    "code": r.get("code"),
                    "database": r.get("database"),
                    "table": r.get("table"),
                }
                all_results.append(formatted)
        else:
            # If no query but we have filters, we might have added local results above.
            # Convert them to standard format
            pass # They are dicts from local yaml, need normalization if we relied on search_by_topic

        # Normalize local results if they came from search_by_topic/source
        normalized_results = []
        seen_ids = set()
        
        for r in all_results:
            # Handle different structures (raw dict from valid vs formatted)
            r_id = r.get("id", "")
            if r_id in seen_ids:
                continue
            seen_ids.add(r_id)
            
            # Normalize fields if coming from raw local search
            if "indicator" not in r and "name" in r:
                r["indicator"] = r["name"]
            if "source" in r:
                r["source"] = r["source"].lower()
            
            normalized_results.append(r)

        # 3. Apply Filters (Source / Topic) in memory
        filtered_results = []
        for r in normalized_results:
            # Source Filter
            if source_filter and r.get("source") != source_filter:
                continue
                
            # Topic Filter (checking tags as proxy for topic)
            if topic_filter and topic_filter not in r.get("tags", "").lower():
                continue
                
            # Check downloaded status
            slug = r.get("slug")
            name = r.get("indicator", "") # indicator used as name in this dict
            
            is_downloaded = check_indicator_downloaded(
                config, 
                r["id"], 
                r.get("source", ""), 
                slug=slug, 
                name=name
            )
            r["downloaded"] = is_downloaded
            
            r["source"] = r.get("source", "").upper() # restore upper case for display
            filtered_results.append(r)

        # Calculate sources breakdown
        sources_count = {}
        for r in filtered_results:
            s = r.get("source", "UNKNOWN").lower()
            sources_count[s] = sources_count.get(s, 0) + 1

        total_results = len(filtered_results)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paged_results = filtered_results[start_idx:end_idx]
        total_pages = (total_results + per_page - 1) // per_page

        return jsonify({
            "results": paged_results,
            "total": total_results,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "query": query,
            "sources": sources_count
        })
    except Exception as e:
        logger.error(f"Search API error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

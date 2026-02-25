"""
Filter API endpoints.

Handles filter presets and filtering operations for datasets.
"""

from flask import jsonify, Response
from flask_login import login_required

from src.utils.regions import list_available_filters, FILTER_PRESETS
from . import api_bp


@api_bp.route("/filters/presets")
@login_required
def get_filter_presets() -> Response:
    """
    Get all available filter presets organized by category.
    
    Returns:
        JSON with categories and their respective filter presets,
        including country counts for each preset.
    """
    try:
        # Get the organized filter list
        available_filters = list_available_filters()
        
        # Build response with additional metadata
        categories = []
        for category_key, filters in available_filters.items():
            category_filters = []
            for filter_key, description in filters.items():
                # Parse the key to get the first/primary key
                primary_key = filter_key.split(" / ")[0] if " / " in filter_key else filter_key
                
                # Get country count for this preset
                country_codes = FILTER_PRESETS.get(primary_key, [])
                
                category_filters.append({
                    "key": primary_key,
                    "label": description,
                    "description": description,
                    "country_count": len(country_codes)
                })
            
            categories.append({
                "name": category_key.replace("_", " ").title(),
                "filters": category_filters
            })
        
        return jsonify({
            "status": "success",
            "categories": categories
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to load filter presets: {str(e)}"
        }), 500

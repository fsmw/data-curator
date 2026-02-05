"""
Compare API endpoints.

Handles dataset comparison and merging.
"""

from flask import request, jsonify, Response
import pandas as pd
from pathlib import Path

from config import Config
from dataset_catalog import DatasetCatalog
from logger import get_logger
from utils.serialization import clean_nan_recursive

from . import api_bp

logger = get_logger(__name__)


@api_bp.route("/compare/data")
def compare_data() -> Response:
    """
    Merge two datasets for comparison/scatter plot.

    Query params:
        dataset_id_x: First dataset ID
        dataset_id_y: Second dataset ID
        merge_on: Columns to merge on (comma-separated, default: country,year)
    """
    try:
        dataset_id_x = request.args.get("dataset_id_x", type=int)
        dataset_id_y = request.args.get("dataset_id_y", type=int)

        if not dataset_id_x or not dataset_id_y:
            return jsonify(
                {"status": "error", "message": "Missing dataset_id_x or dataset_id_y"}
            ), 400

        merge_on = request.args.get("merge_on", "country,year").split(",")

        config = Config()
        catalog = DatasetCatalog(config)

        # Load both datasets
        dataset_x = catalog.get_dataset(dataset_id_x)
        dataset_y = catalog.get_dataset(dataset_id_y)

        if not dataset_x or not dataset_y:
            return jsonify({"status": "error", "message": "One or both datasets not found"}), 404

        # Read CSV files
        df_x = pd.read_csv(dataset_x["file_path"])
        df_y = pd.read_csv(dataset_y["file_path"])

        # Identify value columns (assuming non-key columns)
        # Standardize column names before merge to match frontend expectations (val_x, val_y)
        
        # Helper to find the main value column (not country/year)
        def find_value_col(df):
            cols = [c for c in df.columns if c.lower() not in ['country', 'year', 'iso3', 'date', 'code']]
            return cols[0] if cols else 'value'

        val_col_x = find_value_col(df_x)
        val_col_y = find_value_col(df_y)
        
        df_x = df_x.rename(columns={val_col_x: 'val_x'})
        df_y = df_y.rename(columns={val_col_y: 'val_y'})

        # Ensure numeric types
        df_x['val_x'] = pd.to_numeric(df_x['val_x'], errors='coerce')
        df_y['val_y'] = pd.to_numeric(df_y['val_y'], errors='coerce')
        
        # Drop rows where values became NaN after cleaning
        df_x = df_x.dropna(subset=['val_x'])
        df_y = df_y.dropna(subset=['val_y'])
        
        logger.info(f"Merging X ({len(df_x)} rows, cols: {df_x.columns.tolist()}) with Y ({len(df_y)} rows, cols: {df_y.columns.tolist()}) on {merge_on}")
        
        # Merge datasets on specified columns
        merged = pd.merge(df_x, df_y, on=merge_on, how="inner")
        
        logger.info(f"Merge result: {len(merged)} rows")

        if merged.empty:
            return jsonify({
                "status": "success",
                "data": [],
                "columns": merged.columns.tolist(),
                "total_rows": 0,
                "message": "No overlapping data found for the selected datasets (check consistent country names/years).",
                "year_range": {"min": 2000, "max": 2023}
            })

        # Calculate year range safely
        try:
            min_year_val = merged['year'].min()
            max_year_val = merged['year'].max()
            
            # Handle NaN if explicitly present (safeguard)
            import numpy as np
            if pd.isna(min_year_val) or pd.isna(max_year_val):
                 min_year = 2000
                 max_year = 2023
            else:
                 min_year = int(min_year_val)
                 max_year = int(max_year_val)
        except Exception:
            min_year = 2000
            max_year = 2023

        # Calculate overlap stats
        overlap_stats = {
            "common_years": int(merged['year'].nunique()) if 'year' in merged.columns else 0,
            "common_countries": int(merged['country'].nunique()) if 'country' in merged.columns else 0,
            "total_points": len(merged)
        }

        # Convert to JSON-friendly format
        data_records = merged.to_dict(orient="records")
        cleaned = clean_nan_recursive(data_records)

        return jsonify({
            "status": "success",
            "data": cleaned,
            "columns": merged.columns.tolist(),
            "total_rows": len(merged),
            "year_range": {"min": min_year, "max": max_year},
            "overlap_stats": overlap_stats
        })

    except Exception as e:
        logger.error(f"Error comparing datasets: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

"""
Analysis API endpoints.

Handles statistical analysis (descriptive, regression, comparison).
"""

from flask import request, jsonify, Response
from pathlib import Path

from config import Config
from logger import get_logger

from . import api_bp

logger = get_logger(__name__)


@api_bp.route("/analyze/descriptive", methods=["POST"])
def analyze_descriptive() -> Response:
    """Run descriptive statistical analysis on a dataset."""
    try:
        from analysis import analyze_dataset

        data = request.get_json()
        dataset_id = data.get("dataset_id")

        if not dataset_id:
            return jsonify({"status": "error", "message": "Missing dataset_id"}), 400

        config = Config()
        from dataset_catalog import DatasetCatalog
        catalog = DatasetCatalog(config)
        dataset = catalog.get_dataset(dataset_id)

        if not dataset:
            return jsonify({"status": "error", "message": "Dataset not found"}), 404

        result = analyze_dataset(dataset["file_path"], analysis_type="descriptive")
        return jsonify({"status": "success", "result": result})

    except Exception as e:
        logger.error(f"Descriptive analysis error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/analyze/regression", methods=["POST"])
def analyze_regression() -> Response:
    """Run regression analysis on a dataset."""
    try:
        from analysis import analyze_dataset

        data = request.get_json()
        dataset_id = data.get("dataset_id")
        formula = data.get("formula")

        if not dataset_id or not formula:
            return jsonify({"status": "error", "message": "Missing dataset_id or formula"}), 400

        config = Config()
        from dataset_catalog import DatasetCatalog
        catalog = DatasetCatalog(config)
        dataset = catalog.get_dataset(dataset_id)

        if not dataset:
            return jsonify({"status": "error", "message": "Dataset not found"}), 404

        result = analyze_dataset(
            dataset["file_path"],
            analysis_type="regression",
            formula=formula
        )
        return jsonify({"status": "success", "result": result})

    except Exception as e:
        logger.error(f"Regression analysis error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/analyze/compare", methods=["POST"])
def analyze_compare() -> Response:
    """Compare groups within a dataset."""
    try:
        from analysis import analyze_dataset

        data = request.get_json()
        dataset_id = data.get("dataset_id")
        group_col = data.get("group_col")
        value_col = data.get("value_col")

        if not all([dataset_id, group_col, value_col]):
            return jsonify({"status": "error", "message": "Missing required parameters"}), 400

        config = Config()
        from dataset_catalog import DatasetCatalog
        catalog = DatasetCatalog(config)
        dataset = catalog.get_dataset(dataset_id)

        if not dataset:
            return jsonify({"status": "error", "message": "Dataset not found"}), 404

        result = analyze_dataset(
            dataset["file_path"],
            analysis_type="compare",
            group_col=group_col,
            value_col=value_col
        )
        return jsonify({"status": "success", "result": result})

    except Exception as e:
        logger.error(f"Compare analysis error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

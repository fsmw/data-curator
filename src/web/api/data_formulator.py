"""
Data Formulator compatibility endpoints.

Implements a subset of the Data Formulator API using the Mises dataset catalog.
"""

from __future__ import annotations

import secrets
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import json
from flask import Response, jsonify, request, session

from config import Config
from dataset_catalog import DatasetCatalog
from src.logger import get_logger
from utils.serialization import clean_nan_recursive

from . import api_bp

logger = get_logger(__name__)

_AI_DISABLED_MESSAGE = "AI features are not enabled in this backend."


def _ensure_session_id() -> str:
    if "session_id" not in session:
        session["session_id"] = secrets.token_hex(16)
        session.permanent = True
    return session["session_id"]


def _parse_dataset_id(table_name: str) -> Optional[int]:
    if not table_name:
        return None

    if table_name.startswith("dataset_"):
        remainder = table_name[8:]
        if remainder.isdigit():
            return int(remainder)
        if "__" in remainder:
            id_part = remainder.split("__", 1)[0]
            if id_part.isdigit():
                return int(id_part)

    if table_name.isdigit():
        return int(table_name)

    return None


def _resolve_dataset(table_name: str, catalog: DatasetCatalog) -> Optional[Dict[str, Any]]:
    if not table_name:
        return None

    dataset_id = _parse_dataset_id(table_name)
    if dataset_id is not None:
        return catalog.get_dataset(dataset_id)

    dataset = catalog.get_dataset_by_file_name(table_name)
    if dataset:
        return dataset

    if not table_name.endswith(".csv"):
        return catalog.get_dataset_by_file_name(f"{table_name}.csv")

    return None


def _slugify(value: str) -> str:
    slug = "".join(c.lower() if c.isalnum() else "_" for c in value)
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_")


def _table_name_for_dataset(dataset: Dict[str, Any]) -> str:
    label = dataset.get("indicator_name") or Path(dataset.get("file_name", "dataset")).stem
    slug = _slugify(str(label)) or "dataset"
    return f"dataset_{dataset['id']}__{slug}"


def _map_dtype_to_sql(dtype: Any) -> str:
    if pd.api.types.is_integer_dtype(dtype):
        return "INTEGER"
    if pd.api.types.is_float_dtype(dtype):
        return "DOUBLE"
    if pd.api.types.is_bool_dtype(dtype):
        return "BOOLEAN"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "TIMESTAMP"
    return "STRING"


def _load_dataset_frame(dataset: Dict[str, Any], usecols: Optional[List[str]] = None) -> pd.DataFrame:
    file_path = Path(dataset["file_path"])
    if not file_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {file_path}")
    return pd.read_csv(file_path, usecols=usecols)


def _stream_json_lines(lines: List[Dict[str, Any]]) -> Response:
    payload = "\n".join(json.dumps(line) for line in lines) + "\n"
    return Response(payload, mimetype="text/plain")


def _apply_aggregations(
    df: pd.DataFrame,
    group_fields: List[str],
    aggregate_fields_and_functions: List[List[Any]],
) -> pd.DataFrame:
    valid_group_fields = [f for f in group_fields if f in df.columns]
    has_groups = len(valid_group_fields) > 0
    grouped = df.groupby(valid_group_fields, dropna=False) if has_groups else None

    if has_groups:
        result = grouped.size().reset_index(name="_group_size")
        result = result[valid_group_fields].copy()
    else:
        result = pd.DataFrame([{}])

    for field, func in aggregate_fields_and_functions:
        if func is None:
            continue
        func_lower = str(func).lower()

        if field is None:
            if func_lower == "count":
                if has_groups:
                    counts = grouped.size().reset_index(name="_count")
                    result = result.merge(counts, on=valid_group_fields, how="left")
                else:
                    result["_count"] = [len(df)]
            continue

        if field not in df.columns:
            continue

        if has_groups:
            if func_lower in ["avg", "average", "mean"]:
                values = grouped[field].mean()
                col_name = f"{field}_avg"
            elif func_lower == "sum":
                values = grouped[field].sum()
                col_name = f"{field}_sum"
            elif func_lower == "min":
                values = grouped[field].min()
                col_name = f"{field}_min"
            elif func_lower == "max":
                values = grouped[field].max()
                col_name = f"{field}_max"
            elif func_lower == "count":
                values = grouped[field].count()
                col_name = f"{field}_count"
            else:
                continue

            result = result.merge(values.reset_index(name=col_name), on=valid_group_fields, how="left")
        else:
            series = df[field]
            if func_lower in ["avg", "average", "mean"]:
                value = series.mean()
                col_name = f"{field}_avg"
            elif func_lower == "sum":
                value = series.sum()
                col_name = f"{field}_sum"
            elif func_lower == "min":
                value = series.min()
                col_name = f"{field}_min"
            elif func_lower == "max":
                value = series.max()
                col_name = f"{field}_max"
            elif func_lower == "count":
                value = series.count()
                col_name = f"{field}_count"
            else:
                continue

            result[col_name] = [value]

    return result


@api_bp.route("/get-session-id", methods=["GET", "POST"])
def df_get_session_id() -> Response:
    current_session_id = None
    if request.is_json:
        content = request.get_json()
        current_session_id = content.get("session_id") if content else None

    if current_session_id:
        session["session_id"] = current_session_id
        session.permanent = True
        session_id = current_session_id
    else:
        session_id = _ensure_session_id()

    return jsonify({"status": "ok", "session_id": session_id})


@api_bp.route("/app-config", methods=["GET"])
def df_app_config() -> Response:
    session_id = session.get("session_id")
    return jsonify(
        {
            "EXEC_PYTHON_IN_SUBPROCESS": False,
            "DISABLE_DISPLAY_KEYS": True,
            "DISABLE_DATABASE": False,
            "DISABLE_FILE_UPLOAD": False,
            "PROJECT_FRONT_PAGE": False,
            "SESSION_ID": session_id,
        }
    )


@api_bp.route("/example-datasets")
def df_example_datasets() -> Response:
    return jsonify([])


@api_bp.route("/tables/list-tables", methods=["GET"])
def df_list_tables() -> Response:
    _ensure_session_id()
    try:
        config = Config()
        catalog = DatasetCatalog(config)

        limit = request.args.get("limit", default=500, type=int)
        datasets = catalog.search(limit=limit)

        tables = []
        for dataset in datasets:
            try:
                preview = catalog.get_preview_data(dataset["id"], limit=1000)
                if preview is None:
                    preview = pd.DataFrame()

                columns = [
                    {"name": col, "type": _map_dtype_to_sql(preview[col].dtype)}
                    for col in preview.columns
                ]

                sample_rows = clean_nan_recursive(
                    preview.to_dict(orient="records")
                )

                tables.append(
                    {
                        "name": _table_name_for_dataset(dataset),
                        "columns": columns,
                        "row_count": dataset.get("row_count", len(preview)),
                        "sample_rows": sample_rows,
                        "view_source": None,
                        "source_metadata": None,
                    }
                )
            except Exception as exc:
                logger.warning("Failed to load dataset preview: %s", exc)

        return jsonify({"status": "success", "tables": tables})

    except Exception as exc:
        logger.error("Error listing tables: %s", exc, exc_info=True)
        return jsonify({"status": "error", "message": str(exc)}), 500


@api_bp.route("/tables/sample-table", methods=["POST"])
def df_sample_table() -> Response:
    _ensure_session_id()
    try:
        data = request.get_json() or {}
        table_id = data.get("table")
        sample_size = int(data.get("size", 1000))
        method = data.get("method", "random")
        order_by_fields = data.get("order_by_fields", [])
        select_fields = data.get("select_fields", [])
        aggregate_fields_and_functions = data.get("aggregate_fields_and_functions", [])

        config = Config()
        catalog = DatasetCatalog(config)
        dataset = _resolve_dataset(table_id, catalog)
        if not dataset:
            return jsonify({"status": "error", "message": "Table not found"}), 404

        columns_needed = set()
        for field, _func in aggregate_fields_and_functions:
            if field:
                columns_needed.add(field)
        for field in select_fields:
            columns_needed.add(field)
        for field in order_by_fields:
            columns_needed.add(field)

        usecols = list(columns_needed) if columns_needed else None
        df = _load_dataset_frame(dataset, usecols=usecols)

        valid_select_fields = [f for f in select_fields if f in df.columns]
        valid_order_by_fields = [f for f in order_by_fields if f in df.columns]

        if aggregate_fields_and_functions:
            working_df = _apply_aggregations(df, valid_select_fields, aggregate_fields_and_functions)
        elif valid_select_fields:
            working_df = df[valid_select_fields].copy()
        else:
            working_df = df.copy()

        total_row_count = len(working_df)

        if method == "head":
            if valid_order_by_fields:
                working_df = working_df.sort_values(by=valid_order_by_fields, ascending=True)
            sample_df = working_df.head(sample_size)
        elif method == "bottom":
            if valid_order_by_fields:
                working_df = working_df.sort_values(by=valid_order_by_fields, ascending=False)
                sample_df = working_df.head(sample_size)
            else:
                sample_df = working_df.tail(sample_size)
        else:
            if total_row_count > sample_size:
                sample_df = working_df.sample(n=sample_size, random_state=42)
            else:
                sample_df = working_df

        rows = clean_nan_recursive(sample_df.to_dict(orient="records"))

        return jsonify(
            {
                "status": "success",
                "rows": rows,
                "total_row_count": total_row_count,
            }
        )

    except Exception as exc:
        logger.error("Error sampling table: %s", exc, exc_info=True)
        return jsonify({"status": "error", "message": str(exc)}), 500


@api_bp.route("/tables/get-table", methods=["GET"])
def df_get_table() -> Response:
    _ensure_session_id()
    try:
        table_name = request.args.get("table_name")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 100))
        offset = max(page - 1, 0) * page_size

        if not table_name:
            return jsonify({"status": "error", "message": "Table name is required"}), 400

        config = Config()
        catalog = DatasetCatalog(config)
        dataset = _resolve_dataset(table_name, catalog)
        if not dataset:
            return jsonify({"status": "error", "message": "Table not found"}), 404

        file_path = Path(dataset["file_path"])
        if not file_path.exists():
            return jsonify({"status": "error", "message": "Dataset file not found"}), 404

        df = pd.read_csv(
            file_path,
            skiprows=range(1, offset + 1) if offset > 0 else None,
            nrows=page_size,
        )

        columns = df.columns.tolist()
        rows = clean_nan_recursive(df.to_dict(orient="records"))
        total_rows = dataset.get("row_count", len(rows))

        return jsonify(
            {
                "status": "success",
                "table_name": _table_name_for_dataset(dataset),
                "columns": columns,
                "rows": rows,
                "total_rows": total_rows,
                "page": page,
                "page_size": page_size,
            }
        )

    except Exception as exc:
        logger.error("Error getting table: %s", exc, exc_info=True)
        return jsonify({"status": "error", "message": str(exc)}), 500


@api_bp.route("/tables/analyze", methods=["POST"])
def df_analyze_table() -> Response:
    _ensure_session_id()
    try:
        data = request.get_json() or {}
        table_name = data.get("table_name")
        if not table_name:
            return jsonify({"status": "error", "message": "No table name provided"}), 400

        config = Config()
        catalog = DatasetCatalog(config)
        dataset = _resolve_dataset(table_name, catalog)
        if not dataset:
            return jsonify({"status": "error", "message": "Table not found"}), 404

        df = _load_dataset_frame(dataset)

        stats = []
        for col_name in df.columns:
            series = df[col_name]
            col_type = _map_dtype_to_sql(series.dtype)

            col_stats = {
                "count": int(series.count()),
                "unique_count": int(series.nunique(dropna=True)),
                "null_count": int(series.isna().sum()),
            }

            if pd.api.types.is_numeric_dtype(series):
                col_stats.update(
                    {
                        "min": series.min(),
                        "max": series.max(),
                        "avg": series.mean(),
                    }
                )

            stats.append(
                {
                    "column": col_name,
                    "type": col_type,
                    "statistics": clean_nan_recursive(col_stats),
                }
            )

        return jsonify({"status": "success", "table_name": table_name, "statistics": stats})

    except Exception as exc:
        logger.error("Error analyzing table: %s", exc, exc_info=True)
        return jsonify({"status": "error", "message": str(exc)}), 500


@api_bp.route("/tables/create-table", methods=["POST"])
def df_create_table() -> Response:
    _ensure_session_id()
    try:
        if "file" not in request.files and "raw_data" not in request.form:
            return jsonify({"status": "error", "message": "No file or raw data provided"}), 400

        table_name = request.form.get("table_name")
        if not table_name:
            return jsonify({"status": "error", "message": "No table name provided"}), 400

        df = None
        if "file" in request.files:
            file = request.files["file"]
            filename = file.filename or "upload.csv"

            if filename.endswith(".csv"):
                df = pd.read_csv(file)
            elif filename.endswith((".xlsx", ".xls")):
                df = pd.read_excel(file)
            elif filename.endswith(".json"):
                df = pd.read_json(file)
            else:
                return jsonify({"status": "error", "message": "Unsupported file format"}), 400
        else:
            raw_data = request.form.get("raw_data")
            try:
                df = pd.DataFrame(json.loads(raw_data))
            except Exception as exc:
                return jsonify({"status": "error", "message": f"Invalid JSON data: {exc}"}), 400

        if df is None:
            return jsonify({"status": "error", "message": "No data provided"}), 400

        config = Config()
        uploads_dir = config.get_directory("clean") / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)

        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in table_name).strip("_")
        if not safe_name:
            safe_name = "dataset"

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        file_name = f"{safe_name}_{timestamp}.csv"
        file_path = uploads_dir / file_name
        df.to_csv(file_path, index=False)

        catalog = DatasetCatalog(config)
        dataset_id = catalog.index_dataset(file_path, force=True)
        if not dataset_id:
            return jsonify({"status": "error", "message": "Failed to index dataset"}), 500

        return jsonify(
            {
                "status": "success",
                "table_name": f"dataset_{dataset_id}",
                "row_count": len(df),
                "columns": list(df.columns),
                "original_name": table_name,
                "is_renamed": safe_name != table_name,
            }
        )

    except Exception as exc:
        logger.error("Error creating table: %s", exc, exc_info=True)
        return jsonify({"status": "error", "message": str(exc)}), 500


@api_bp.route("/tables/delete-table", methods=["POST"])
def df_delete_table() -> Response:
    _ensure_session_id()
    try:
        data = request.get_json() or {}
        table_name = data.get("table_name")
        if not table_name:
            return jsonify({"status": "error", "message": "No table name provided"}), 400

        config = Config()
        catalog = DatasetCatalog(config)
        dataset = _resolve_dataset(table_name, catalog)
        if not dataset:
            return jsonify({"status": "error", "message": "Table not found"}), 404

        file_path = Path(dataset["file_path"])
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception as exc:
                logger.warning("Failed to delete file %s: %s", file_path, exc)

        catalog.delete_dataset(dataset["id"])

        return jsonify({"status": "success", "message": f"Table {table_name} deleted"})

    except Exception as exc:
        logger.error("Error deleting table: %s", exc, exc_info=True)
        return jsonify({"status": "error", "message": str(exc)}), 500


@api_bp.route("/tables/upload-db-file", methods=["POST"])
def df_upload_db_file() -> Response:
    _ensure_session_id()
    return jsonify({"status": "error", "message": "Database uploads are not supported."}), 400


@api_bp.route("/tables/download-db-file", methods=["GET"])
def df_download_db_file() -> Response:
    _ensure_session_id()
    return jsonify({"status": "error", "message": "Database downloads are not supported."}), 400


@api_bp.route("/tables/reset-db-file", methods=["POST"])
def df_reset_db_file() -> Response:
    _ensure_session_id()
    return jsonify({"status": "success", "message": "No local database to reset."})


@api_bp.route("/tables/data-loader/list-data-loaders", methods=["GET"])
def df_list_data_loaders() -> Response:
    return jsonify(
        {
            "status": "success",
            "data_loaders": {
                "mises_catalog": {
                    "params": [],
                    "auth_instructions": "Browse datasets already indexed in the Mises catalog.",
                }
            },
        }
    )


@api_bp.route("/tables/data-loader/list-tables", methods=["POST"])
def df_data_loader_list_tables() -> Response:
    _ensure_session_id()
    data = request.get_json() or {}
    data_loader_type = data.get("data_loader_type")

    if data_loader_type != "mises_catalog":
        return jsonify(
            {
                "status": "error",
                "message": "Invalid data loader type. Only 'mises_catalog' is supported.",
            }
        ), 400

    config = Config()
    catalog = DatasetCatalog(config)
    table_filter = (data.get("table_filter") or "").lower()
    datasets = catalog.search(limit=500)

    tables = []
    for dataset in datasets:
        table_name = _table_name_for_dataset(dataset)
        if table_filter and table_filter not in table_name.lower() and table_filter not in dataset.get("indicator_name", "").lower():
            continue

        preview = catalog.get_preview_data(dataset["id"], limit=1000)
        if preview is None:
            preview = pd.DataFrame()

        columns = [
            {"name": col, "type": _map_dtype_to_sql(preview[col].dtype)}
            for col in preview.columns
        ]

        sample_rows = clean_nan_recursive(preview.to_dict(orient="records"))

        tables.append(
            {
                "name": table_name,
                "metadata": {
                    "columns": columns,
                    "row_count": dataset.get("row_count", len(preview)),
                    "sample_rows": sample_rows,
                },
            }
        )

    return jsonify({"status": "success", "tables": tables})


@api_bp.route("/tables/data-loader/ingest-data", methods=["POST"])
def df_data_loader_ingest_data() -> Response:
    _ensure_session_id()
    data = request.get_json() or {}
    data_loader_type = data.get("data_loader_type")
    table_name = data.get("table_name")

    if data_loader_type != "mises_catalog" or not table_name:
        return jsonify(
            {
                "status": "error",
                "message": "Invalid data loader request.",
            }
        ), 400

    return jsonify(
        {
            "status": "success",
            "message": "Dataset available in catalog.",
            "table_name": table_name,
        }
    )


@api_bp.route("/tables/data-loader/view-query-sample", methods=["POST"])
def df_data_loader_view_query_sample() -> Response:
    _ensure_session_id()
    return jsonify(
        {
            "status": "error",
            "sample": [],
            "message": "Query sampling is not supported for the catalog loader.",
        }
    ), 400


@api_bp.route("/tables/data-loader/ingest-data-from-query", methods=["POST"])
def df_data_loader_ingest_data_from_query() -> Response:
    _ensure_session_id()
    return jsonify(
        {
            "status": "error",
            "message": "Query ingestion is not supported for the catalog loader.",
        }
    ), 400


@api_bp.route("/tables/data-loader/refresh-table", methods=["POST"])
def df_data_loader_refresh_table() -> Response:
    _ensure_session_id()
    return jsonify(
        {
            "status": "error",
            "message": "Refresh is not supported for the catalog loader.",
        }
    ), 400


@api_bp.route("/tables/data-loader/get-table-metadata", methods=["POST"])
def df_data_loader_get_table_metadata() -> Response:
    _ensure_session_id()
    return jsonify({"status": "success", "metadata": None})


@api_bp.route("/tables/data-loader/list-table-metadata", methods=["GET"])
def df_data_loader_list_table_metadata() -> Response:
    _ensure_session_id()
    return jsonify({"status": "success", "metadata": []})


# =============================================================================
# Agent compatibility endpoints (stubbed)
# =============================================================================

@api_bp.route("/agent/check-available-models", methods=["GET"])
def df_check_available_models() -> Response:
    return jsonify([])


@api_bp.route("/agent/test-model", methods=["POST"])
def df_test_model() -> Response:
    return jsonify({"status": "error", "message": _AI_DISABLED_MESSAGE})


@api_bp.route("/agent/derive-concept-request", methods=["POST"])
def df_derive_concept_request() -> Response:
    return jsonify({"status": "error", "message": _AI_DISABLED_MESSAGE})


@api_bp.route("/agent/derive-py-concept", methods=["POST"])
def df_derive_py_concept() -> Response:
    return jsonify({"status": "error", "message": _AI_DISABLED_MESSAGE})


@api_bp.route("/agent/sort-data", methods=["POST"])
def df_sort_data() -> Response:
    return jsonify({"status": "error", "message": _AI_DISABLED_MESSAGE})


@api_bp.route("/agent/clean-data-stream", methods=["POST"])
def df_clean_data_stream() -> Response:
    line = {
        "status": "ok",
        "content": [
            {
                "type": "csv",
                "value": "message\nAI features are disabled in this backend.",
                "incomplete": True,
            }
        ],
        "dialog": [],
    }
    return _stream_json_lines([line])


@api_bp.route("/agent/code-expl", methods=["POST"])
def df_code_expl() -> Response:
    return jsonify({"status": "error", "message": _AI_DISABLED_MESSAGE})


@api_bp.route("/agent/process-data-on-load", methods=["POST"])
def df_process_data_on_load() -> Response:
    return jsonify({"status": "error", "message": _AI_DISABLED_MESSAGE})


@api_bp.route("/agent/derive-data", methods=["POST"])
def df_derive_data() -> Response:
    return jsonify({"status": "error", "message": _AI_DISABLED_MESSAGE})


@api_bp.route("/agent/refine-data", methods=["POST"])
def df_refine_data() -> Response:
    return jsonify({"status": "error", "message": _AI_DISABLED_MESSAGE})


@api_bp.route("/agent/explore-data-streaming", methods=["POST"])
def df_explore_data_streaming() -> Response:
    lines = [
        {
            "status": "error",
            "error_message": _AI_DISABLED_MESSAGE,
        }
    ]
    return _stream_json_lines(lines)


@api_bp.route("/agent/get-recommendation-questions", methods=["POST"])
def df_get_recommendation_questions() -> Response:
    lines = [
        {
            "type": "question",
            "text": _AI_DISABLED_MESSAGE,
            "goal": _AI_DISABLED_MESSAGE,
            "difficulty": "easy",
            "tag": "info",
        },
        {
            "questions": [_AI_DISABLED_MESSAGE],
            "goal": _AI_DISABLED_MESSAGE,
            "difficulty": "easy",
        },
    ]
    return _stream_json_lines(lines)


@api_bp.route("/agent/generate-report-stream", methods=["POST"])
def df_generate_report_stream() -> Response:
    payload = f"error:{json.dumps({'content': _AI_DISABLED_MESSAGE})}"
    return Response(payload, mimetype="text/plain")


@api_bp.route("/agent/refresh-derived-data", methods=["POST"])
def df_refresh_derived_data() -> Response:
    return jsonify({"status": "error", "message": _AI_DISABLED_MESSAGE})

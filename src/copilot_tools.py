"""
MCP Tools for GitHub Copilot SDK Integration.

This module defines and implements Model Context Protocol (MCP) tools
that allow the Copilot agent to interact with Mises Data Curator functionality.

Each tool is a function that can be called by the agent to perform
specific data curation operations.

Example:
    >>> from src.copilot_tools import search_datasets, download_owid
    >>> results = await search_datasets("GDP Brazil")
    >>> dataset = await download_owid("gdp-per-capita", countries=["BRA"])
"""

import io
import ast
import json
import shutil
import sqlite3
from typing import Dict, List, Optional, Any, Set, Tuple
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
from contextlib import redirect_stdout

from src.config import Config
from src.searcher import IndicatorSearcher
from src.ingestion import DataIngestionManager, OWIDSource
from src.dataset_catalog import DatasetCatalog
from src.smoothcsv_cache import (
    SQL_PREVIEW_LIMIT,
    SQL_SAMPLE_LIMIT,
    ensure_smoothcsv_table,
    get_smoothcsv_db_path,
    prepare_smoothcsv_sql,
)

TOOL_OPERATION_ERRORS = (
    OSError,
    ValueError,
    TypeError,
    KeyError,
    RuntimeError,
    ImportError,
    sqlite3.Error,
    pd.errors.EmptyDataError,
    pd.errors.ParserError,
)


# Initialize configuration (singleton pattern)
_config = None
def get_config():
    """Get or create Config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


NON_COUNTRY_ENTITIES = {
    "world",
    "europe",
    "asia",
    "africa",
    "north america",
    "south america",
    "european union",
    "high-income countries",
    "upper-middle-income countries",
    "lower-middle-income countries",
    "low-income countries",
    "oecd members",
}

COUNTRY_ALIASES_TO_ISO3 = {
    "united states": "USA",
    "united states of america": "USA",
    "us": "USA",
    "usa": "USA",
    "united kingdom": "GBR",
    "uk": "GBR",
    "south korea": "KOR",
    "korea, republic of": "KOR",
    "north korea": "PRK",
    "russia": "RUS",
    "russian federation": "RUS",
    "iran": "IRN",
    "iran, islamic republic of": "IRN",
    "venezuela": "VEN",
    "venezuela, bolivarian republic of": "VEN",
    "bolivia": "BOL",
    "bolivia, plurinational state of": "BOL",
    "laos": "LAO",
    "viet nam": "VNM",
    "czechia": "CZE",
    "moldova": "MDA",
    "tanzania": "TZA",
    "syrian arab republic": "SYR",
    "brunei": "BRN",
}


def _normalize_entity_text(value: Any) -> str:
    return " ".join(str(value).strip().lower().replace("_", " ").split())


def _detect_entity_column(df: pd.DataFrame) -> Optional[str]:
    candidates = ["iso3", "country_code", "country", "Country", "entity", "Entity", "location", "Location"]
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _detect_year_column(df: pd.DataFrame) -> Optional[str]:
    candidates = ["year", "Year", "YEAR", "time", "Time", "date", "Date"]
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _harmonize_entity(value: Any) -> Dict[str, Any]:
    if pd.isna(value):
        return {"iso3": None, "entity_key": None, "is_country": False, "normalized_entity": None, "match_type": "missing"}
    raw = str(value).strip()
    normalized = _normalize_entity_text(raw)
    if not normalized:
        return {"iso3": None, "entity_key": None, "is_country": False, "normalized_entity": raw, "match_type": "missing"}
    if normalized in NON_COUNTRY_ENTITIES:
        return {"iso3": None, "entity_key": normalized, "is_country": False, "normalized_entity": raw, "match_type": "non_country"}
    if normalized in COUNTRY_ALIASES_TO_ISO3:
        iso3 = COUNTRY_ALIASES_TO_ISO3[normalized]
        return {
            "iso3": iso3,
            "entity_key": iso3,
            "is_country": True,
            "normalized_entity": raw,
            "match_type": "alias",
        }
    compact = raw.strip().upper()
    if len(compact) == 3 and compact.isalpha():
        return {"iso3": compact, "entity_key": compact, "is_country": True, "normalized_entity": raw, "match_type": "iso3"}
    return {
        "iso3": None,
        "entity_key": normalized,
        "is_country": True,
        "normalized_entity": raw,
        "match_type": "name_unmapped",
    }


def _load_catalog_dataset_frame(dataset_id: int) -> Tuple[Dict[str, Any], pd.DataFrame]:
    config = get_config()
    catalog = DatasetCatalog(config)
    dataset = catalog.get_dataset(int(dataset_id))
    if not dataset:
        raise ValueError(f"Dataset '{dataset_id}' not found")
    file_path = dataset.get("file_path")
    if not file_path:
        raise ValueError(f"Dataset '{dataset_id}' has no file_path")
    df = pd.read_csv(file_path)
    if df.empty:
        raise ValueError(f"Dataset '{dataset_id}' is empty")
    return dataset, df


def _infer_value_column(df: pd.DataFrame, entity_col: str, year_col: str) -> Optional[str]:
    excluded = {entity_col, year_col, "iso3", "entity_key", "normalized_entity", "is_country", "_country_match_type"}
    candidates = [col for col in df.columns if col not in excluded]
    numeric_candidates = [col for col in candidates if pd.api.types.is_numeric_dtype(df[col])]
    if numeric_candidates:
        return numeric_candidates[0]
    if candidates:
        return candidates[0]
    return None


def _safe_col_name(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in value.strip())
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "value"


DISALLOWED_AST_NODES = (
    ast.Import,
    ast.ImportFrom,
    ast.Global,
    ast.Nonlocal,
)


def _validate_python_analysis_code(python_code: str) -> Optional[str]:
    """Validate Python analysis script with basic AST safety rules."""
    try:
        tree = ast.parse(python_code)
    except SyntaxError as exc:
        return f"Invalid python_code syntax: {exc}"

    for node in ast.walk(tree):
        if isinstance(node, DISALLOWED_AST_NODES):
            return "python_code contains disallowed statements (import/global/nonlocal)"
    return None


def _country_group_maps() -> Tuple[Dict[str, str], Set[str]]:
    """Build lightweight country group maps from configured regions."""
    try:
        config = get_config()
        regions = config.get_regions() if hasattr(config, "get_regions") else {}
    except (OSError, ValueError, TypeError):
        regions = {}

    region_map: Dict[str, str] = {}
    oecd_set: Set[str] = set()
    for region_name, iso_list in (regions or {}).items():
        if not isinstance(iso_list, list):
            continue
        normalized_region = str(region_name).strip().lower()
        for iso in iso_list:
            iso3 = str(iso).strip().upper()
            if len(iso3) != 3:
                continue
            if normalized_region in {"latam", "latin_america", "latin-america"}:
                region_map.setdefault(iso3, "LATAM")
            elif normalized_region == "oecd":
                oecd_set.add(iso3)
                region_map.setdefault(iso3, "OECD")
            elif normalized_region in {"global", "world"}:
                continue
            else:
                region_map.setdefault(iso3, normalized_region.upper())
    return region_map, oecd_set


# ============================================================================
# TOOL 1: Search Datasets
# ============================================================================

async def search_datasets(
    query: str,
    source: Optional[str] = None,
    topic: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Search for datasets in the catalog.
    
    This tool searches both the local dataset catalog and available indicators
    from configured data sources (OWID, World Bank, ILOSTAT, etc.).
    
    Args:
        query: Search terms (e.g., "GDP", "population", "unemployment")
        source: Filter by data source (e.g., "owid", "worldbank", "ilostat")
        topic: Filter by topic category (e.g., "economy", "health", "population")
        limit: Maximum number of results to return (default 10)
    
    Returns:
        Dictionary with search results including:
        - datasets: List of matching datasets
        - total_found: Total number of matches
        - query: The search query used
    
    Example:
        >>> results = await search_datasets("GDP Brazil", source="owid")
        >>> print(results['datasets'][0]['name'])
        'GDP per capita - Brazil'
    """
    try:
        config = get_config()
        results = {"query": query, "source_filter": source, "topic_filter": topic}
        
        # Search in indicators database
        searcher = IndicatorSearcher(config)
        indicators = searcher.search(query)
        
        # Filter by source if specified
        if source:
            indicators = [ind for ind in indicators if ind.get('source', '').lower() == source.lower()]
        
        # Search in local catalog
        catalog = DatasetCatalog(config)
        filters = {}
        if source:
            filters["source"] = source
        if topic:
            filters["topic"] = topic
        local_datasets = catalog.search(query=query, filters=filters, limit=limit)
        
        # Combine results
        combined_results = []
        
        # Add indicators (available for download)
        for ind in indicators[:limit]:
            combined_results.append({
                "id": ind.get('id', ''),
                "name": ind.get('name', ''),
                "source": ind.get('source', ''),
                "description": ind.get('description', ''),
                "type": "available",
                "url": ind.get('url', ''),
                "tags": ind.get('tags', [])
            })
        
        # Add local datasets (already downloaded)
        for ds in local_datasets[:limit]:
            combined_results.append({
                "id": ds.get('id', ''),
                "name": ds.get('name', ''),
                "source": ds.get('source', ''),
                "description": ds.get('description', ''),
                "type": "local",
                "file_path": str(ds.get('file_path', '')),
                "row_count": ds.get('row_count', 0),
                "tags": ds.get('tags', [])
            })
        
        results["datasets"] = combined_results[:limit]
        results["total_found"] = len(indicators) + len(local_datasets)
        results["status"] = "success"
        
        return results
        
    except TOOL_OPERATION_ERRORS as e:
        return {
            "status": "error",
            "error": str(e),
            "query": query,
            "datasets": []
        }


# ============================================================================
# TOOL 2: List Local Datasets (for "review my datasets" / multi-dataset proposals)
# ============================================================================

async def list_local_datasets(
    topic: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 50,
    include_uncataloged: bool = True,
) -> Dict[str, Any]:
    """
    List datasets the user has locally (cataloged in 02_Datasets_Limpios).
    Call this first when the user asks to "review my datasets" or "propose analyses
    crossing multiple datasets" so you know what they have before proposing.

    Args:
        topic: Filter by topic (e.g. gdp, wages, tax)
        source: Filter by source (e.g. owid, oecd)
        limit: Max datasets to return (default 50)
        include_uncataloged: If True, also list CSV files in the clean folder that
            are not yet in the catalog (user may need to run 'curate index')

    Returns:
        - cataloged: list of {id, name, source, topic, row_count} (use id for preview_data/get_metadata/analyze_data)
        - uncataloged_files: list of file names in 02_Datasets_Limpios not yet indexed (if include_uncataloged)
        - total_cataloged: count
    """
    try:
        config = get_config()
        catalog = DatasetCatalog(config)
        filters = {}
        if topic:
            filters["topic"] = topic
        if source:
            filters["source"] = source
        datasets = catalog.search(query="", filters=filters or None, limit=limit)
        total_cataloged = (
            len(catalog.search(query="", filters=filters or None, limit=5000))
            if filters
            else catalog.get_statistics().get("total_datasets", len(datasets))
        )
        cataloged = []
        for ds in datasets:
            name = ds.get("indicator_name") or ds.get("name") or ds.get("file_name", "")
            cataloged.append({
                "id": ds.get("id"),
                "name": name,
                "source": ds.get("source", ""),
                "topic": ds.get("topic", ""),
                "row_count": ds.get("row_count", 0),
            })
        uncataloged_files = []
        if include_uncataloged:
            clean_dir = config.get_directory("clean")
            if clean_dir.exists():
                all_cataloged = catalog.list_datasets(limit=5000)
                cataloged_paths = {Path(d.get("file_path", "")).name for d in all_cataloged if d.get("file_path")}
                for path in clean_dir.rglob("*.csv"):
                    if path.name not in cataloged_paths:
                        uncataloged_files.append(path.name)
        return {
            "status": "success",
            "cataloged": cataloged,
            "total_cataloged": total_cataloged,
            "returned_count": len(cataloged),
            "is_truncated": len(cataloged) >= limit,
            "uncataloged_files": uncataloged_files[:20],
            "hint": "Use cataloged[].id with preview_data, get_metadata, or analyze_data. If uncataloged_files is not empty, suggest running 'curate index' to add them to the catalog.",
        }
    except TOOL_OPERATION_ERRORS as e:
        return {
            "status": "error",
            "error": str(e),
            "cataloged": [],
            "total_cataloged": 0,
            "uncataloged_files": [],
        }


# ============================================================================
# TOOL: Country Harmonizer (Phase 1)
# ============================================================================

async def country_harmonizer(
    dataset_id: int,
    entity_column: Optional[str] = None,
    exclude_non_country: bool = True,
    persist: bool = False,
    new_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Normalize country entities to ISO3 and classify non-country rows."""
    try:
        dataset, df = _load_catalog_dataset_frame(int(dataset_id))
        col = entity_column or _detect_entity_column(df)
        if not col:
            return {
                "status": "error",
                "error": "No entity/country column found",
                "dataset_id": dataset_id,
            }

        mapped = df[col].apply(_harmonize_entity)
        mapped_df = pd.DataFrame(mapped.tolist())
        work = df.copy()
        work["normalized_entity"] = mapped_df["normalized_entity"]
        work["iso3"] = mapped_df["iso3"]
        work["entity_key"] = mapped_df["entity_key"]
        work["is_country"] = mapped_df["is_country"]
        work["_country_match_type"] = mapped_df["match_type"]

        original_rows = len(work)
        if exclude_non_country:
            work = work[work["is_country"]].copy()

        unmatched = mapped_df[mapped_df["match_type"] == "name_unmapped"]["normalized_entity"].dropna().unique().tolist()
        non_country = mapped_df[mapped_df["match_type"] == "non_country"]["normalized_entity"].dropna().unique().tolist()
        match_counts = mapped_df["match_type"].value_counts(dropna=False).to_dict()

        result: Dict[str, Any] = {
            "status": "success",
            "dataset_id": dataset_id,
            "dataset_name": dataset.get("indicator_name") or dataset.get("file_name"),
            "entity_column": col,
            "rows_original": original_rows,
            "rows_after_filter": len(work),
            "exclude_non_country": exclude_non_country,
            "match_counts": match_counts,
            "unmatched_entities_sample": unmatched[:25],
            "non_country_entities_sample": non_country[:25],
            "sample_rows": work[[col, "normalized_entity", "iso3", "entity_key", "is_country", "_country_match_type"]]
            .head(20)
            .to_dict(orient="records"),
        }

        if persist:
            config = get_config()
            clean_dir = config.get_directory("clean")
            clean_dir.mkdir(parents=True, exist_ok=True)
            safe_base = new_name or f"dataset_{dataset_id}_harmonized"
            safe_base = "".join(c if c.isalnum() or c in "-_" else "_" for c in safe_base).strip("_") or "harmonized"
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            output_path = clean_dir / f"{safe_base}_{timestamp}.csv"
            work.to_csv(output_path, index=False)

            catalog = DatasetCatalog(config)
            new_dataset_id = catalog.index_dataset(output_path, force=True)
            result["persisted"] = True
            result["new_dataset_id"] = new_dataset_id
            result["output_file"] = str(output_path)
        else:
            result["persisted"] = False

        return result
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}


# ============================================================================
# TOOL: Coverage Analyzer (Phase 1)
# ============================================================================

async def coverage_analyzer(
    dataset_ids: List[int],
    period_start: Optional[int] = None,
    period_end: Optional[int] = None,
    countries_only: bool = True,
) -> Dict[str, Any]:
    """Analyze country-year coverage overlap across datasets."""
    try:
        if not dataset_ids:
            return {"status": "error", "error": "dataset_ids cannot be empty"}

        per_dataset: List[Dict[str, Any]] = []
        pair_sets: List[Set[Tuple[str, int]]] = []

        for dataset_id in dataset_ids:
            dataset, df = _load_catalog_dataset_frame(int(dataset_id))
            entity_col = _detect_entity_column(df)
            year_col = _detect_year_column(df)
            if not entity_col or not year_col:
                return {
                    "status": "error",
                    "error": f"Dataset {dataset_id} missing required entity/year columns",
                    "dataset_id": dataset_id,
                }

            mapped = df[entity_col].apply(_harmonize_entity).apply(pd.Series)
            years = pd.to_numeric(df[year_col], errors="coerce")
            frame = pd.DataFrame({
                "iso3": mapped["iso3"],
                "entity_key": mapped["entity_key"],
                "is_country": mapped["is_country"],
                "year": years,
            }).dropna(subset=["year"])
            frame["year"] = frame["year"].astype(int)

            if period_start is not None:
                frame = frame[frame["year"] >= int(period_start)]
            if period_end is not None:
                frame = frame[frame["year"] <= int(period_end)]
            if countries_only:
                frame = frame[frame["is_country"]]

            pair_set = {
                (str(row.iso3 or row.entity_key), int(row.year))
                for row in frame.itertuples(index=False)
                if row.iso3 or row.entity_key
            }
            pair_sets.append(pair_set)
            per_dataset.append(
                {
                    "dataset_id": dataset_id,
                    "name": dataset.get("indicator_name") or dataset.get("file_name"),
                    "entity_column": entity_col,
                    "year_column": year_col,
                    "country_year_points": len(pair_set),
                    "unique_countries": int((frame["iso3"].fillna(frame["entity_key"])).nunique()),
                    "min_year": int(frame["year"].min()) if not frame.empty else None,
                    "max_year": int(frame["year"].max()) if not frame.empty else None,
                }
            )

        intersection = set.intersection(*pair_sets) if pair_sets else set()
        union = set.union(*pair_sets) if pair_sets else set()
        warnings: List[str] = []
        if not intersection:
            warnings.append("No overlapping country-year observations across datasets.")
        elif len(intersection) < 100:
            warnings.append("Low overlap (<100 country-year points). Results may be unstable.")

        limiting = min(per_dataset, key=lambda x: x["country_year_points"]) if per_dataset else None
        overlap_ratio = (len(intersection) / len(union)) if union else 0.0

        return {
            "status": "success",
            "dataset_ids": dataset_ids,
            "period": {"start": period_start, "end": period_end},
            "countries_only": countries_only,
            "intersection_country_year_points": len(intersection),
            "union_country_year_points": len(union),
            "overlap_ratio": overlap_ratio,
            "intersection_countries": len({c for c, _ in intersection}),
            "intersection_years": len({y for _, y in intersection}),
            "limiting_dataset": limiting,
            "datasets": per_dataset,
            "warnings": warnings,
            "intersection_sample": [{"entity_key": entity_key, "year": year} for entity_key, year in sorted(intersection)[:25]],
        }
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e), "dataset_ids": dataset_ids}


# ============================================================================
# TOOL: Panel Builder (Phase 1)
# ============================================================================

async def panel_builder(
    dataset_ids: List[int],
    join_type: str = "inner",
    period_start: Optional[int] = None,
    period_end: Optional[int] = None,
    countries_only: bool = True,
    lags: Optional[Dict[str, int]] = None,
    value_columns: Optional[Dict[str, str]] = None,
    persist: bool = False,
    panel_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a merged panel by entity_key-year across multiple datasets."""
    try:
        if not dataset_ids or len(dataset_ids) < 2:
            return {"status": "error", "error": "panel_builder requires at least 2 dataset_ids"}
        if join_type not in {"inner", "outer"}:
            return {"status": "error", "error": "join_type must be 'inner' or 'outer'"}

        lag_map = {str(k): int(v) for k, v in (lags or {}).items()}
        value_map = {str(k): v for k, v in (value_columns or {}).items()}

        merged_df: Optional[pd.DataFrame] = None
        dataset_report: List[Dict[str, Any]] = []
        warnings: List[str] = []

        for index, dataset_id in enumerate(dataset_ids):
            ds_id = int(dataset_id)
            dataset, df = _load_catalog_dataset_frame(ds_id)
            entity_col = _detect_entity_column(df)
            year_col = _detect_year_column(df)
            if not entity_col or not year_col:
                return {
                    "status": "error",
                    "error": f"Dataset {ds_id} missing required entity/year columns",
                    "dataset_id": ds_id,
                }

            mapped = df[entity_col].apply(_harmonize_entity).apply(pd.Series)
            frame = pd.DataFrame({
                "entity_key": mapped["entity_key"],
                "is_country": mapped["is_country"],
                "year": pd.to_numeric(df[year_col], errors="coerce"),
            }).dropna(subset=["entity_key", "year"])
            frame["year"] = frame["year"].astype(int)

            if countries_only:
                frame = frame[frame["is_country"]]
            if period_start is not None:
                frame = frame[frame["year"] >= int(period_start)]
            if period_end is not None:
                frame = frame[frame["year"] <= int(period_end)]

            selected_value_col = value_map.get(str(ds_id)) or _infer_value_column(df, entity_col, year_col)
            if not selected_value_col or selected_value_col not in df.columns:
                return {
                    "status": "error",
                    "error": f"Dataset {ds_id} has no value column available",
                    "dataset_id": ds_id,
                }

            value_name = f"value_{ds_id}"
            frame[value_name] = pd.to_numeric(df.loc[frame.index, selected_value_col], errors="coerce")
            frame = frame[["entity_key", "year", value_name]].copy()
            frame = frame.groupby(["entity_key", "year"], as_index=False)[value_name].mean()

            lag_n = lag_map.get(str(ds_id), 0)
            if lag_n > 0:
                frame["year"] = frame["year"] + lag_n

            before_merge_points = len(frame)
            if merged_df is None:
                merged_df = frame
            else:
                pre_rows = len(merged_df)
                merged_df = pd.merge(merged_df, frame, on=["entity_key", "year"], how=join_type)
                if join_type == "inner" and len(merged_df) < pre_rows:
                    warnings.append(
                        f"Inner join reduced panel rows after dataset {ds_id}: {pre_rows} -> {len(merged_df)}."
                    )

            dataset_report.append({
                "dataset_id": ds_id,
                "name": dataset.get("indicator_name") or dataset.get("file_name"),
                "entity_column": entity_col,
                "year_column": year_col,
                "value_column": selected_value_col,
                "lag_applied": lag_n,
                "country_year_points": before_merge_points,
            })

        assert merged_df is not None
        merged_df = merged_df.sort_values(["entity_key", "year"]).reset_index(drop=True)
        value_cols = [c for c in merged_df.columns if c.startswith("value_")]
        panel_rows = len(merged_df)
        panel_complete_rows = int(merged_df[value_cols].dropna().shape[0]) if value_cols else panel_rows

        coverage = await coverage_analyzer(
            dataset_ids=[int(d) for d in dataset_ids],
            period_start=period_start,
            period_end=period_end,
            countries_only=countries_only,
        )

        result: Dict[str, Any] = {
            "status": "success",
            "dataset_ids": [int(d) for d in dataset_ids],
            "join_type": join_type,
            "period": {"start": period_start, "end": period_end},
            "countries_only": countries_only,
            "panel_rows": panel_rows,
            "panel_complete_rows": panel_complete_rows,
            "panel_columns": ["entity_key", "year"] + value_cols,
            "datasets": dataset_report,
            "coverage_report": coverage,
            "warnings": warnings,
            "sample_rows": merged_df.head(25).to_dict(orient="records"),
        }

        if persist:
            config = get_config()
            clean_dir = config.get_directory("clean")
            clean_dir.mkdir(parents=True, exist_ok=True)
            safe_name = panel_name or "panel_dataset"
            safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in safe_name).strip("_") or "panel_dataset"
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            output_path = clean_dir / f"{safe_name}_{timestamp}.csv"
            merged_df.to_csv(output_path, index=False)

            catalog = DatasetCatalog(config)
            new_dataset_id = catalog.index_dataset(output_path, force=True)
            result["persisted"] = True
            result["panel_dataset_id"] = new_dataset_id
            result["panel_file_path"] = str(output_path)
        else:
            result["persisted"] = False

        return result
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e), "dataset_ids": dataset_ids}


# ============================================================================
# TOOL: Economic Transformer (Phase 2)
# ============================================================================

def _apply_group_transform(
    frame: pd.DataFrame,
    value_col: str,
    transformation: Dict[str, Any],
) -> Tuple[pd.Series, List[str], str]:
    t_type = str(transformation.get("type", "")).lower()
    safe_value_col = _safe_col_name(value_col)
    t_name = t_type or "unknown"
    warnings: List[str] = []
    grouped = frame.groupby("entity_key", dropna=False)[value_col]

    if t_type == "lag":
        periods = int(transformation.get("periods", 1))
        return grouped.shift(periods), warnings, f"{safe_value_col}_lag{periods}"
    if t_type == "lead":
        periods = int(transformation.get("periods", 1))
        return grouped.shift(-periods), warnings, f"{safe_value_col}_lead{periods}"
    if t_type == "growth_rate":
        return grouped.pct_change(), warnings, f"{safe_value_col}_growth_rate"
    if t_type == "first_diff":
        return grouped.diff(), warnings, f"{safe_value_col}_first_diff"
    if t_type == "moving_avg":
        window = max(int(transformation.get("window", 3)), 1)
        return (
            grouped.transform(lambda s: s.rolling(window=window, min_periods=1).mean()),
            warnings,
            f"{safe_value_col}_moving_avg_{window}",
        )
    if t_type == "log":
        non_positive = int((frame[value_col] <= 0).sum())
        if non_positive > 0:
            warnings.append(f"log generated NaN for {non_positive} non-positive rows")
        return pd.to_numeric(frame[value_col], errors="coerce").where(frame[value_col] > 0).apply(np.log), warnings, f"{safe_value_col}_log"
    if t_type == "zscore":
        series = pd.to_numeric(frame[value_col], errors="coerce")
        std = series.std()
        if std == 0 or pd.isna(std):
            warnings.append("zscore skipped due to zero/NaN standard deviation")
            return pd.Series([pd.NA] * len(series), index=series.index), warnings, f"{safe_value_col}_zscore"
        return (series - series.mean()) / std, warnings, f"{safe_value_col}_zscore"
    if t_type == "min_max":
        series = pd.to_numeric(frame[value_col], errors="coerce")
        min_v, max_v = series.min(), series.max()
        if pd.isna(min_v) or pd.isna(max_v) or max_v == min_v:
            warnings.append("min_max skipped due to invalid range")
            return pd.Series([pd.NA] * len(series), index=series.index), warnings, f"{safe_value_col}_min_max"
        return (series - min_v) / (max_v - min_v), warnings, f"{safe_value_col}_min_max"

    warnings.append(f"Unsupported transformation '{t_name}'")
    return pd.Series([pd.NA] * len(frame), index=frame.index), warnings, f"{safe_value_col}_{t_name}"


async def economic_transformer(
    dataset_id: int,
    column: Optional[str] = None,
    transformations: Optional[List[Dict[str, Any]]] = None,
    output_mode: str = "add_columns",
    persist: bool = False,
    new_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Apply chained economic transformations to a dataset column."""
    try:
        if output_mode not in {"add_columns", "replace"}:
            return {"status": "error", "error": "output_mode must be 'add_columns' or 'replace'"}

        dataset, df = _load_catalog_dataset_frame(int(dataset_id))
        entity_col = _detect_entity_column(df)
        year_col = _detect_year_column(df)
        if not entity_col or not year_col:
            return {"status": "error", "error": "Dataset requires entity and year columns", "dataset_id": dataset_id}

        work = df.copy()
        mapped = work[entity_col].apply(_harmonize_entity).apply(pd.Series)
        work["entity_key"] = mapped["entity_key"]
        work["year"] = pd.to_numeric(work[year_col], errors="coerce")
        work = work.dropna(subset=["entity_key", "year"]).copy()
        work["year"] = work["year"].astype(int)
        work = work.sort_values(["entity_key", "year"]).reset_index(drop=True)

        base_col = column or _infer_value_column(work, entity_col, year_col)
        if not base_col or base_col not in work.columns:
            return {"status": "error", "error": "No valid value column found", "dataset_id": dataset_id}
        work[base_col] = pd.to_numeric(work[base_col], errors="coerce")

        transforms = transformations or [{"type": "growth_rate"}]
        current_col = base_col
        created_cols: List[str] = []
        all_warnings: List[str] = []

        for t in transforms:
            transformed, warnings, out_col = _apply_group_transform(work, current_col, t or {})
            work[out_col] = transformed
            created_cols.append(out_col)
            all_warnings.extend(warnings)
            if output_mode == "replace":
                current_col = out_col

        result: Dict[str, Any] = {
            "status": "success",
            "dataset_id": dataset_id,
            "dataset_name": dataset.get("indicator_name") or dataset.get("file_name"),
            "base_column": base_col,
            "output_mode": output_mode,
            "created_columns": created_cols,
            "warnings": all_warnings,
            "sample_rows": work[["entity_key", "year", base_col] + created_cols].head(25).to_dict(orient="records"),
        }

        if persist:
            config = get_config()
            clean_dir = config.get_directory("clean")
            clean_dir.mkdir(parents=True, exist_ok=True)
            safe_base = new_name or f"dataset_{dataset_id}_transformed"
            safe_base = "".join(c if c.isalnum() or c in "-_" else "_" for c in safe_base).strip("_") or "transformed"
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            output_path = clean_dir / f"{safe_base}_{timestamp}.csv"
            work.to_csv(output_path, index=False)
            catalog = DatasetCatalog(config)
            new_dataset_id = catalog.index_dataset(output_path, force=True)
            result.update({"persisted": True, "new_dataset_id": new_dataset_id, "output_file": str(output_path)})
        else:
            result["persisted"] = False

        return result
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}


# ============================================================================
# TOOL: Missing Data Handler (Phase 2)
# ============================================================================

async def missing_data_handler(
    dataset_id: int,
    strategy: str = "linear",
    columns: Optional[List[str]] = None,
    max_gap: int = 3,
    scope: str = "within_entity",
    persist: bool = False,
    new_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle missing values with explicit strategy and imputation tracking."""
    try:
        strategy = strategy.lower()
        allowed = {"linear", "forward_fill", "backward_fill", "drop", "regional_mean"}
        if strategy not in allowed:
            return {"status": "error", "error": f"Invalid strategy '{strategy}'", "dataset_id": dataset_id}

        dataset, df = _load_catalog_dataset_frame(int(dataset_id))
        entity_col = _detect_entity_column(df)
        year_col = _detect_year_column(df)
        if not entity_col or not year_col:
            return {"status": "error", "error": "Dataset requires entity and year columns", "dataset_id": dataset_id}

        work = df.copy()
        mapped = work[entity_col].apply(_harmonize_entity).apply(pd.Series)
        work["entity_key"] = mapped["entity_key"]
        work["year"] = pd.to_numeric(work[year_col], errors="coerce")
        work = work.dropna(subset=["entity_key", "year"]).copy()
        work["year"] = work["year"].astype(int)
        work = work.sort_values(["entity_key", "year"]).reset_index(drop=True)

        target_cols = columns or [
            c for c in work.columns
            if c not in {entity_col, year_col, "entity_key", "year"} and pd.api.types.is_numeric_dtype(work[c])
        ]
        if not target_cols:
            return {"status": "error", "error": "No numeric columns available for missing-data handling", "dataset_id": dataset_id}

        original_nulls = int(work[target_cols].isna().sum().sum())
        imputed_mask = pd.DataFrame(False, index=work.index, columns=target_cols)

        for col in target_cols:
            series = pd.to_numeric(work[col], errors="coerce")
            before_na = series.isna()

            if strategy == "drop":
                work[col] = series
                continue
            if strategy == "linear":
                if scope == "within_entity":
                    filled = work.groupby("entity_key", dropna=False)[col].transform(
                        lambda s: pd.to_numeric(s, errors="coerce").interpolate(method="linear", limit=max_gap)
                    )
                else:
                    filled = series.interpolate(method="linear", limit=max_gap)
            elif strategy == "forward_fill":
                if scope == "within_entity":
                    filled = work.groupby("entity_key", dropna=False)[col].transform(
                        lambda s: pd.to_numeric(s, errors="coerce").ffill(limit=max_gap)
                    )
                else:
                    filled = series.ffill(limit=max_gap)
            elif strategy == "backward_fill":
                if scope == "within_entity":
                    filled = work.groupby("entity_key", dropna=False)[col].transform(
                        lambda s: pd.to_numeric(s, errors="coerce").bfill(limit=max_gap)
                    )
                else:
                    filled = series.bfill(limit=max_gap)
            else:  # regional_mean fallback: mean by year
                filled = series.fillna(work.groupby("year")[col].transform("mean"))

            after_na = filled.isna()
            imputed_mask[col] = before_na & ~after_na
            work[col] = filled

        if strategy == "drop":
            work = work.dropna(subset=target_cols)
            work["_is_imputed"] = False
            imputed = 0
        else:
            work["_is_imputed"] = imputed_mask.any(axis=1)
            imputed = int(imputed_mask.sum().sum())

        remaining_nulls = int(work[target_cols].isna().sum().sum())
        result: Dict[str, Any] = {
            "status": "success",
            "dataset_id": dataset_id,
            "dataset_name": dataset.get("indicator_name") or dataset.get("file_name"),
            "strategy": strategy,
            "columns": target_cols,
            "max_gap": max_gap,
            "scope": scope,
            "original_nulls": original_nulls,
            "imputed": imputed,
            "remaining_nulls": remaining_nulls,
            "sample_rows": work[["entity_key", "year"] + target_cols[:4] + ["_is_imputed"]].head(25).to_dict(orient="records"),
        }

        if persist:
            config = get_config()
            clean_dir = config.get_directory("clean")
            clean_dir.mkdir(parents=True, exist_ok=True)
            safe_base = new_name or f"dataset_{dataset_id}_{strategy}"
            safe_base = "".join(c if c.isalnum() or c in "-_" else "_" for c in safe_base).strip("_") or "missing_handled"
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            output_path = clean_dir / f"{safe_base}_{timestamp}.csv"
            work.to_csv(output_path, index=False)
            catalog = DatasetCatalog(config)
            new_dataset_id = catalog.index_dataset(output_path, force=True)
            result.update({"persisted": True, "new_dataset_id": new_dataset_id, "output_file": str(output_path)})
        else:
            result["persisted"] = False

        return result
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}


# ============================================================================
# TOOL: Data Profiler (Phase 2)
# ============================================================================

async def data_profiler(
    dataset_id: int,
    by_country: bool = True,
    by_year: bool = True,
    by_column: bool = True,
) -> Dict[str, Any]:
    """Profile data quality, missingness, and panel readiness."""
    try:
        dataset, df = _load_catalog_dataset_frame(int(dataset_id))
        entity_col = _detect_entity_column(df)
        year_col = _detect_year_column(df)

        if entity_col:
            mapped = df[entity_col].apply(_harmonize_entity).apply(pd.Series)
            df = df.copy()
            df["entity_key"] = mapped["entity_key"]
            df["is_country"] = mapped["is_country"]

        year_series = pd.to_numeric(df[year_col], errors="coerce") if year_col else pd.Series([pd.NA] * len(df))
        overall_null_pct = float(df.isna().sum().sum() / (len(df) * max(len(df.columns), 1)) * 100) if len(df) > 0 else 0.0

        warnings: List[str] = []
        if overall_null_pct > 30:
            warnings.append("High missingness (>30%) may bias panel analysis.")
        if entity_col is None or year_col is None:
            warnings.append("Dataset lacks standard entity/year columns for panel operations.")

        result: Dict[str, Any] = {
            "status": "success",
            "dataset_id": dataset_id,
            "dataset_name": dataset.get("indicator_name") or dataset.get("file_name"),
            "row_count": len(df),
            "column_count": len(df.columns),
            "overall_null_percentage": overall_null_pct,
            "entity_column": entity_col,
            "year_column": year_col,
            "year_range": {
                "min": int(year_series.min()) if year_col and year_series.notna().any() else None,
                "max": int(year_series.max()) if year_col and year_series.notna().any() else None,
            },
            "warnings": warnings,
        }

        if by_column:
            column_profile = []
            for col in df.columns:
                s = df[col]
                column_profile.append({
                    "column": col,
                    "dtype": str(s.dtype),
                    "null_count": int(s.isna().sum()),
                    "null_percentage": float((s.isna().sum() / len(df) * 100) if len(df) else 0),
                    "unique_values": int(s.nunique(dropna=True)),
                })
            result["column_profile"] = column_profile

        if by_country and "entity_key" in df.columns:
            country_profile = (
                df.dropna(subset=["entity_key"])
                .groupby("entity_key")
                .agg(rows=("entity_key", "count"), years=(year_col if year_col else "entity_key", "nunique"))
                .reset_index()
                .sort_values("rows", ascending=False)
            )
            result["country_profile_sample"] = country_profile.head(30).to_dict(orient="records")

        if by_year and year_col:
            year_frame = pd.DataFrame({"year": year_series})
            if "entity_key" in df.columns:
                year_frame["entity_key"] = df["entity_key"]
                yearly = (
                    year_frame.dropna(subset=["year"])
                    .groupby("year")
                    .agg(rows=("year", "count"), unique_entities=("entity_key", "nunique"))
                    .reset_index()
                    .sort_values("year")
                )
            else:
                yearly = (
                    year_frame.dropna(subset=["year"])
                    .groupby("year")
                    .agg(rows=("year", "count"))
                    .reset_index()
                    .sort_values("year")
                )
            result["year_profile_sample"] = yearly.head(50).to_dict(orient="records")

        return result
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}


# ============================================================================
# TOOL: Run Python Analysis (Phase 3 foundation)
# ============================================================================

async def run_python_analysis(
    dataset_ids: List[int],
    python_code: str,
    preview_rows: int = 25,
) -> Dict[str, Any]:
    """Execute restricted Python analysis code against one or more local datasets."""
    try:
        if not dataset_ids:
            return {"status": "error", "error": "dataset_ids cannot be empty"}
        if not python_code or not python_code.strip():
            return {"status": "error", "error": "python_code cannot be empty"}

        validation_error = _validate_python_analysis_code(python_code)
        if validation_error:
            return {"status": "error", "error": validation_error}

        dfs: Dict[str, pd.DataFrame] = {}
        dataset_report: List[Dict[str, Any]] = []
        for dataset_id in dataset_ids:
            dataset, df = _load_catalog_dataset_frame(int(dataset_id))
            dfs[str(dataset_id)] = df.copy()
            dataset_report.append(
                {
                    "dataset_id": int(dataset_id),
                    "name": dataset.get("indicator_name") or dataset.get("file_name"),
                    "rows": int(len(df)),
                    "columns": int(len(df.columns)),
                }
            )

        primary_df = dfs[str(dataset_ids[0])]
        safe_builtins = {
            "len": len,
            "min": min,
            "max": max,
            "sum": sum,
            "abs": abs,
            "round": round,
            "sorted": sorted,
            "range": range,
            "print": print,
        }
        global_scope: Dict[str, Any] = {
            "__builtins__": safe_builtins,
            "pd": pd,
            "np": np,
            "dfs": dfs,
            "df": primary_df,
        }
        local_scope: Dict[str, Any] = {}
        stdout_buffer = io.StringIO()
        with redirect_stdout(stdout_buffer):
            exec(python_code, global_scope, local_scope)

        result_obj = local_scope.get("result", global_scope.get("result"))
        result_df = local_scope.get("result_df", global_scope.get("result_df"))
        response: Dict[str, Any] = {
            "status": "success",
            "dataset_ids": [int(d) for d in dataset_ids],
            "datasets": dataset_report,
            "stdout": stdout_buffer.getvalue().strip(),
        }

        if result_obj is not None:
            if isinstance(result_obj, (dict, list, str, int, float, bool)) or result_obj is None:
                response["result"] = result_obj
            else:
                response["result"] = str(result_obj)

        if isinstance(result_df, pd.DataFrame):
            preview_limit = max(1, min(int(preview_rows), 200))
            response["result_df_shape"] = [int(result_df.shape[0]), int(result_df.shape[1])]
            response["result_df_columns"] = list(result_df.columns)
            response["result_df_preview"] = result_df.head(preview_limit).to_dict(orient="records")

        return response
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e), "dataset_ids": dataset_ids}
    except (ValueError, TypeError, SyntaxError, NameError, KeyError, AttributeError, ArithmeticError) as e:
        return {"status": "error", "error": str(e), "dataset_ids": dataset_ids}


# ============================================================================
# TOOL: Correlation Analyzer (Phase 3 MVP)
# ============================================================================

async def correlation_analyzer(
    dataset_id: int,
    columns: Optional[List[str]] = None,
    method: str = "pooled",
    entity_column: Optional[str] = None,
    year_column: Optional[str] = None,
    window: int = 5,
    min_periods: int = 3,
    top_n: int = 10,
) -> Dict[str, Any]:
    """Compute pooled/within/rolling correlations using run_python_analysis runtime."""
    try:
        method_normalized = str(method or "pooled").strip().lower()
        if method_normalized not in {"pooled", "within", "rolling"}:
            return {"status": "error", "error": "method must be one of: pooled, within, rolling"}

        dataset, df = _load_catalog_dataset_frame(int(dataset_id))
        detected_entity_col = entity_column or _detect_entity_column(df)
        detected_year_col = year_column or _detect_year_column(df)

        if columns:
            selected_columns = [str(c) for c in columns]
        else:
            excluded = {c for c in [detected_entity_col, detected_year_col] if c}
            selected_columns = [c for c in df.columns if c not in excluded and pd.api.types.is_numeric_dtype(df[c])]
            selected_columns = selected_columns[:8]

        missing_columns = [c for c in selected_columns if c not in df.columns]
        if missing_columns:
            return {"status": "error", "error": f"Columns not found: {missing_columns}", "dataset_id": dataset_id}
        if len(selected_columns) < 2:
            return {"status": "error", "error": "At least two columns are required for correlation analysis", "dataset_id": dataset_id}
        if method_normalized in {"within", "rolling"} and not detected_entity_col:
            return {"status": "error", "error": "Entity column is required for within/rolling methods", "dataset_id": dataset_id}
        if method_normalized == "rolling" and not detected_year_col:
            return {"status": "error", "error": "Year column is required for rolling method", "dataset_id": dataset_id}

        safe_window = max(2, int(window))
        safe_min_periods = max(2, min(int(min_periods), safe_window))
        safe_top_n = max(1, min(int(top_n), 50))

        python_code = """
columns = %(columns)r
method = %(method)r
entity_col = %(entity_col)r
year_col = %(year_col)r
window = %(window)d
min_periods = %(min_periods)d
top_n = %(top_n)d

work = df.copy()
for col in columns:
    work[col] = pd.to_numeric(work[col], errors="coerce")

valid_columns = [c for c in columns if work[c].notna().sum() >= 2]
if len(valid_columns) < 2:
    raise ValueError("Not enough valid numeric columns after coercion")

warnings = []
if len(valid_columns) != len(columns):
    warnings.append("Some columns were dropped because they lacked enough numeric values.")

if method == "pooled":
    corr_df = work[valid_columns].corr()
    observations = work[valid_columns].dropna().shape[0]
elif method == "within":
    panel = df[[entity_col] + valid_columns].copy()
    for col in valid_columns:
        panel[col] = pd.to_numeric(panel[col], errors="coerce")
    panel = panel.dropna(subset=[entity_col])
    demeaned = panel[valid_columns] - panel.groupby(entity_col)[valid_columns].transform("mean")
    corr_df = demeaned.corr()
    observations = demeaned.dropna().shape[0]
else:
    panel = df[[entity_col, year_col] + valid_columns].copy()
    panel[year_col] = pd.to_numeric(panel[year_col], errors="coerce")
    panel = panel.dropna(subset=[entity_col, year_col]).sort_values([entity_col, year_col])
    corr_df = pd.DataFrame(index=valid_columns, columns=valid_columns, dtype="float64")
    for c in valid_columns:
        corr_df.loc[c, c] = 1.0
    rolling_counts = 0
    for i in range(len(valid_columns)):
        for j in range(i + 1, len(valid_columns)):
            c1 = valid_columns[i]
            c2 = valid_columns[j]
            pair_vals = []
            for _, grp in panel.groupby(entity_col):
                grp = grp.sort_values(year_col)
                s1 = pd.to_numeric(grp[c1], errors="coerce")
                s2 = pd.to_numeric(grp[c2], errors="coerce")
                roll = s1.rolling(window=window, min_periods=min_periods).corr(s2).dropna()
                if len(roll) > 0:
                    pair_vals.extend(roll.tolist())
            if pair_vals:
                avg_corr = sum(pair_vals) / len(pair_vals)
                corr_df.loc[c1, c2] = avg_corr
                corr_df.loc[c2, c1] = avg_corr
                rolling_counts += len(pair_vals)
    observations = rolling_counts
    if observations == 0:
        warnings.append("No rolling windows produced valid pairwise correlation estimates.")

top_pairs = []
for i in range(len(valid_columns)):
    for j in range(i + 1, len(valid_columns)):
        c1 = valid_columns[i]
        c2 = valid_columns[j]
        val = corr_df.loc[c1, c2] if c1 in corr_df.index and c2 in corr_df.columns else None
        if pd.notna(val):
            top_pairs.append({"var1": c1, "var2": c2, "correlation": round(val, 6), "abs_correlation": round(abs(val), 6)})
top_pairs = sorted(top_pairs, key=lambda x: x["abs_correlation"], reverse=True)[:top_n]

if top_pairs:
    t = top_pairs[0]
    direction = "positive" if t["correlation"] >= 0 else "negative"
    interpretation = f"Strongest {method} correlation is {direction}: {t['var1']} vs {t['var2']} ({t['correlation']})."
else:
    interpretation = "No valid pairwise correlations could be computed with the selected configuration."

correlation_matrix = {}
for row_name in valid_columns:
    correlation_matrix[row_name] = {}
    for col_name in valid_columns:
        v = corr_df.loc[row_name, col_name] if row_name in corr_df.index and col_name in corr_df.columns else None
        correlation_matrix[row_name][col_name] = None if pd.isna(v) else round(v, 6)

result = {
    "method": method,
    "columns_used": valid_columns,
    "observations": observations,
    "correlation_matrix": correlation_matrix,
    "top_pairs": top_pairs,
    "interpretation": interpretation,
    "warnings": warnings,
}
""" % {
            "columns": selected_columns,
            "method": method_normalized,
            "entity_col": detected_entity_col,
            "year_col": detected_year_col,
            "window": safe_window,
            "min_periods": safe_min_periods,
            "top_n": safe_top_n,
        }

        analysis = await run_python_analysis(dataset_ids=[int(dataset_id)], python_code=python_code)
        if analysis.get("status") != "success":
            return {"status": "error", "error": analysis.get("error", "Correlation analysis failed"), "dataset_id": dataset_id}

        result = analysis.get("result")
        if not isinstance(result, dict):
            return {"status": "error", "error": "Correlation analysis returned invalid result payload", "dataset_id": dataset_id}

        return {
            "status": "success",
            "dataset_id": int(dataset_id),
            "dataset_name": dataset.get("indicator_name") or dataset.get("file_name"),
            "method": result.get("method", method_normalized),
            "columns_used": result.get("columns_used", []),
            "observations": result.get("observations"),
            "correlation_matrix": result.get("correlation_matrix", {}),
            "top_pairs": result.get("top_pairs", []),
            "interpretation": result.get("interpretation", ""),
            "warnings": result.get("warnings", []),
        }
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}
    except (ValueError, TypeError, KeyError) as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}


# ============================================================================
# TOOL: Group Classifier (Phase 3 MVP)
# ============================================================================

async def group_classifier(
    dataset_id: int,
    group_by: str = "region",
    entity_column: Optional[str] = None,
    value_column: Optional[str] = None,
    income_column: Optional[str] = None,
    region_column: Optional[str] = None,
    oecd_column: Optional[str] = None,
    population_column: Optional[str] = None,
) -> Dict[str, Any]:
    """Classify observations by country metadata groups and summarize coverage."""
    try:
        group_key = str(group_by or "region").strip().lower()
        if group_key not in {"region", "income", "oecd", "population_band"}:
            return {"status": "error", "error": "group_by must be one of: region, income, oecd, population_band"}

        dataset, df = _load_catalog_dataset_frame(int(dataset_id))
        if df.empty:
            return {"status": "error", "error": "Dataset is empty", "dataset_id": dataset_id}

        detected_entity_col = entity_column or _detect_entity_column(df)
        if not detected_entity_col:
            return {"status": "error", "error": "Could not detect entity column", "dataset_id": dataset_id}

        work = df.copy()
        harmonized = work[detected_entity_col].apply(_harmonize_entity).apply(pd.Series)
        work["_iso3"] = harmonized["iso3"]
        work["_entity_key"] = harmonized["entity_key"]
        work["_is_country"] = harmonized["is_country"].fillna(False)

        detected_value_col = value_column
        if not detected_value_col:
            numeric_cols = [c for c in work.columns if pd.api.types.is_numeric_dtype(work[c])]
            excluded = {"year", "Year", "date", "Date"}
            numeric_cols = [c for c in numeric_cols if c not in excluded]
            detected_value_col = numeric_cols[0] if numeric_cols else None

        region_map, oecd_set = _country_group_maps()
        if group_key == "region":
            meta_col = region_column or next((c for c in ["region", "Region", "world_region"] if c in work.columns), None)
            if meta_col:
                region_vals = work[meta_col].where(work[meta_col].notna(), "unknown")
                work["_group"] = region_vals.astype(str).str.strip().replace({"": "unknown"})
            else:
                work["_group"] = work["_iso3"].map(region_map).fillna("unknown")
        elif group_key == "income":
            meta_col = income_column or next((c for c in ["income_group", "income", "IncomeGroup", "incomeLevel"] if c in work.columns), None)
            if not meta_col:
                return {"status": "error", "error": "Income metadata not found. Provide income_column or dataset with income metadata.", "dataset_id": dataset_id}
            income_vals = work[meta_col].where(work[meta_col].notna(), "unknown")
            work["_group"] = income_vals.astype(str).str.strip().replace({"": "unknown"})
        elif group_key == "oecd":
            meta_col = oecd_column or next((c for c in ["is_oecd", "oecd", "OECD"] if c in work.columns), None)
            if meta_col:
                raw = work[meta_col].astype(str).str.strip().str.lower()
                work["_group"] = np.where(raw.isin({"1", "true", "yes", "y", "oecd"}), "OECD", "Non-OECD")
            else:
                work["_group"] = np.where(work["_iso3"].isin(oecd_set), "OECD", "Non-OECD")
        else:  # population_band
            meta_col = population_column or next((c for c in ["population_band", "pop_band", "population", "Population"] if c in work.columns), None)
            if not meta_col:
                return {"status": "error", "error": "Population metadata not found. Provide population_column or dataset with population metadata.", "dataset_id": dataset_id}
            if meta_col in {"population", "Population"} and pd.api.types.is_numeric_dtype(work[meta_col]):
                pop = pd.to_numeric(work[meta_col], errors="coerce")
                work["_group"] = pd.cut(
                    pop,
                    bins=[-np.inf, 1_000_000, 10_000_000, 50_000_000, np.inf],
                    labels=["small", "medium", "large", "very_large"],
                ).astype("object").fillna("unknown")
            else:
                pop_vals = work[meta_col].where(work[meta_col].notna(), "unknown")
                work["_group"] = pop_vals.astype(str).str.strip().replace({"": "unknown"})

        scope = work[work["_is_country"] == True].copy()
        if scope.empty:
            scope = work.copy()

        agg = scope.groupby("_group", dropna=False).agg(
            rows=("_group", "count"),
            unique_entities=("_entity_key", "nunique"),
        )
        if detected_value_col:
            agg["mean_value"] = pd.to_numeric(scope[detected_value_col], errors="coerce").groupby(scope["_group"]).mean()
        agg = agg.reset_index().rename(columns={"_group": "group"}).sort_values("rows", ascending=False)

        unknown_count = int((scope["_group"].astype(str).str.lower() == "unknown").sum())
        warnings: List[str] = []
        if unknown_count > 0:
            warnings.append(f"{unknown_count} rows could not be classified and were marked as 'unknown'.")
        if detected_value_col is None:
            warnings.append("No numeric value_column detected; summary excludes mean_value.")

        return {
            "status": "success",
            "dataset_id": int(dataset_id),
            "dataset_name": dataset.get("indicator_name") or dataset.get("file_name"),
            "group_by": group_key,
            "entity_column": detected_entity_col,
            "value_column": detected_value_col,
            "total_rows": int(len(scope)),
            "groups": agg.to_dict(orient="records"),
            "warnings": warnings,
        }
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}
    except (ValueError, TypeError, KeyError) as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}


# ============================================================================
# TOOL: Regression Engine (Phase 3 MVP)
# ============================================================================

async def regression_engine(
    dataset_id: int,
    dependent: str,
    independents: List[str],
    model: str = "pooled",
    entity_column: Optional[str] = None,
    year_column: Optional[str] = None,
) -> Dict[str, Any]:
    """Estimate pooled OLS and basic fixed-effects models over local datasets."""
    try:
        model_key = str(model or "pooled").strip().lower()
        allowed_models = {"pooled", "fe_entity", "fe_two_way"}
        if model_key not in allowed_models:
            return {"status": "error", "error": "model must be one of: pooled, fe_entity, fe_two_way"}
        if not dependent:
            return {"status": "error", "error": "dependent is required"}
        if not independents:
            return {"status": "error", "error": "independents cannot be empty"}

        dataset, df = _load_catalog_dataset_frame(int(dataset_id))
        missing_cols = [c for c in [dependent, *independents] if c not in df.columns]
        if missing_cols:
            return {"status": "error", "error": f"Columns not found: {missing_cols}", "dataset_id": dataset_id}

        detected_entity_col = entity_column or _detect_entity_column(df)
        detected_year_col = year_column or _detect_year_column(df)
        if model_key in {"fe_entity", "fe_two_way"} and not detected_entity_col:
            return {"status": "error", "error": "Entity column is required for fixed-effects models", "dataset_id": dataset_id}
        if model_key == "fe_two_way" and not detected_year_col:
            return {"status": "error", "error": "Year column is required for fe_two_way model", "dataset_id": dataset_id}

        python_code = """
y_col = %(y_col)r
x_cols = %(x_cols)r
model = %(model)r
entity_col = %(entity_col)r
year_col = %(year_col)r

work = df.copy()
for c in [y_col] + x_cols:
    work[c] = pd.to_numeric(work[c], errors="coerce")

base_cols = [y_col] + x_cols
if model in ["fe_entity", "fe_two_way"]:
    base_cols = base_cols + [entity_col]
if model == "fe_two_way":
    base_cols = base_cols + [year_col]

work = work.dropna(subset=base_cols)
warnings = []
if len(work) < 10:
    warnings.append("Very small sample size (<10 observations).")

Y = work[y_col].to_numpy()
X = work[x_cols].to_numpy()

if model == "pooled":
    X_design = np.column_stack([np.ones(len(X)), X])
    coef_names = ["const"] + x_cols
elif model == "fe_entity":
    group_means_y = work.groupby(entity_col)[y_col].transform("mean").to_numpy()
    Y = Y - group_means_y
    X_demeaned = X.copy()
    i = 0
    for xc in x_cols:
        X_demeaned[:, i] = X_demeaned[:, i] - work.groupby(entity_col)[xc].transform("mean").to_numpy()
        i = i + 1
    X_design = X_demeaned
    coef_names = x_cols
else:
    entity_means_y = work.groupby(entity_col)[y_col].transform("mean").to_numpy()
    time_means_y = work.groupby(year_col)[y_col].transform("mean").to_numpy()
    grand_mean_y = np.nanmean(Y)
    Y = Y - entity_means_y - time_means_y + grand_mean_y

    X_tw = X.copy()
    i = 0
    for xc in x_cols:
        entity_m = work.groupby(entity_col)[xc].transform("mean").to_numpy()
        time_m = work.groupby(year_col)[xc].transform("mean").to_numpy()
        grand_m = np.nanmean(X_tw[:, i])
        X_tw[:, i] = X_tw[:, i] - entity_m - time_m + grand_m
        i = i + 1
    X_design = X_tw
    coef_names = x_cols

beta, residuals_sum, rank, singular = np.linalg.lstsq(X_design, Y, rcond=None)
y_hat = X_design @ beta
resid = Y - y_hat
n_obs = len(Y)
k = X_design.shape[1]
rss = np.sum(resid ** 2)
tss = np.sum((Y - np.mean(Y)) ** 2)
r_squared = None if tss == 0 else 1 - (rss / tss)
adj_r_squared = None
if r_squared is not None and n_obs > k + 1:
    adj_r_squared = 1 - (1 - r_squared) * ((n_obs - 1) / (n_obs - k - 1))

if n_obs <= k:
    warnings.append("Model may be underidentified (observations <= parameters).")

coefficients = {}
i = 0
for name in coef_names:
    coefficients[name] = round(beta[i], 8)
    i = i + 1

result = {
    "model": model,
    "dependent": y_col,
    "independents": x_cols,
    "n_obs": n_obs,
    "n_params": k,
    "r_squared": None if r_squared is None else round(r_squared, 8),
    "adj_r_squared": None if adj_r_squared is None else round(adj_r_squared, 8),
    "coefficients": coefficients,
    "warnings": warnings,
}
"""

        analysis = await run_python_analysis(
            dataset_ids=[int(dataset_id)],
            python_code=python_code
            % {
                "y_col": dependent,
                "x_cols": [str(c) for c in independents],
                "model": model_key,
                "entity_col": detected_entity_col,
                "year_col": detected_year_col,
            },
        )
        if analysis.get("status") != "success":
            return {"status": "error", "error": analysis.get("error", "Regression failed"), "dataset_id": dataset_id}

        payload = analysis.get("result")
        if not isinstance(payload, dict):
            return {"status": "error", "error": "Regression returned invalid payload", "dataset_id": dataset_id}

        return {
            "status": "success",
            "dataset_id": int(dataset_id),
            "dataset_name": dataset.get("indicator_name") or dataset.get("file_name"),
            "model": payload.get("model", model_key),
            "dependent": payload.get("dependent", dependent),
            "independents": payload.get("independents", independents),
            "n_obs": payload.get("n_obs"),
            "n_params": payload.get("n_params"),
            "r_squared": payload.get("r_squared"),
            "adj_r_squared": payload.get("adj_r_squared"),
            "coefficients": payload.get("coefficients", {}),
            "warnings": payload.get("warnings", []),
        }
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}
    except (ValueError, TypeError, KeyError) as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}


# ============================================================================
# TOOL: Smart Visualizer (Phase 3 MVP)
# ============================================================================

async def smart_visualizer(
    dataset_id: int,
    chart_type: str = "line",
    x: Optional[str] = None,
    y: Optional[str] = None,
    color: Optional[str] = None,
    top_n: int = 50,
) -> Dict[str, Any]:
    """Create a reproducible Vega-Lite chart specification from a local dataset."""
    try:
        chart_kind = str(chart_type or "line").strip().lower()
        allowed = {"line", "scatter", "heatmap"}
        if chart_kind not in allowed:
            return {"status": "error", "error": "chart_type must be one of: line, scatter, heatmap"}

        dataset, df = _load_catalog_dataset_frame(int(dataset_id))
        if df.empty:
            return {"status": "error", "error": "Dataset is empty", "dataset_id": dataset_id}

        entity_col = _detect_entity_column(df)
        year_col = _detect_year_column(df)
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

        x_col = x
        y_col = y
        color_col = color

        if chart_kind == "line":
            if not x_col:
                x_col = year_col or (df.columns[0] if len(df.columns) > 0 else None)
            if not y_col:
                y_candidates = [c for c in numeric_cols if c != x_col]
                y_col = y_candidates[0] if y_candidates else None
            if not color_col and entity_col and entity_col in df.columns:
                color_col = entity_col
        elif chart_kind == "scatter":
            if len(numeric_cols) < 2 and (not x_col or not y_col):
                return {"status": "error", "error": "Scatter requires at least two numeric columns", "dataset_id": dataset_id}
            if not x_col:
                x_col = numeric_cols[0]
            if not y_col:
                y_col = numeric_cols[1]
            if not color_col and entity_col and entity_col in df.columns:
                color_col = entity_col
        else:  # heatmap
            if not x_col:
                x_col = entity_col or (df.columns[0] if len(df.columns) > 0 else None)
            if not y_col:
                y_col = year_col or (df.columns[1] if len(df.columns) > 1 else None)
            if not color_col:
                color_col = numeric_cols[0] if numeric_cols else None

        missing = [c for c in [x_col, y_col] if not c or c not in df.columns]
        if missing:
            return {"status": "error", "error": f"Missing required chart columns: {missing}", "dataset_id": dataset_id}
        if chart_kind == "heatmap" and (not color_col or color_col not in df.columns):
            return {"status": "error", "error": "Heatmap requires a valid color/value column", "dataset_id": dataset_id}

        safe_top_n = max(5, min(int(top_n), 500))
        cols = [x_col, y_col] + ([color_col] if color_col and color_col not in {x_col, y_col} else [])
        chart_df = df[cols].copy().dropna().head(safe_top_n)
        if chart_df.empty:
            return {"status": "error", "error": "No rows available after filtering null values", "dataset_id": dataset_id}

        def _vega_type(col_name: str) -> str:
            if col_name == year_col:
                return "temporal"
            if pd.api.types.is_numeric_dtype(df[col_name]):
                return "quantitative"
            return "nominal"

        if chart_kind == "heatmap":
            mark = "rect"
            encoding = {
                "x": {"field": x_col, "type": _vega_type(x_col)},
                "y": {"field": y_col, "type": _vega_type(y_col)},
                "color": {"field": color_col, "type": "quantitative"},
            }
        else:
            mark = "line" if chart_kind == "line" else "point"
            encoding = {
                "x": {"field": x_col, "type": _vega_type(x_col)},
                "y": {"field": y_col, "type": _vega_type(y_col)},
            }
            if color_col and color_col in chart_df.columns:
                encoding["color"] = {"field": color_col, "type": _vega_type(color_col)}

        spec = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "description": f"{chart_kind} chart generated by smart_visualizer",
            "mark": mark,
            "encoding": encoding,
            "data": {"values": chart_df.to_dict(orient="records")},
        }

        return {
            "status": "success",
            "dataset_id": int(dataset_id),
            "dataset_name": dataset.get("indicator_name") or dataset.get("file_name"),
            "chart_type": chart_kind,
            "fields": {"x": x_col, "y": y_col, "color": color_col},
            "row_count": int(len(chart_df)),
            "chart_spec": spec,
            "reproducible_config": {
                "dataset_id": int(dataset_id),
                "chart_type": chart_kind,
                "x": x_col,
                "y": y_col,
                "color": color_col,
                "top_n": safe_top_n,
            },
        }
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}
    except (ValueError, TypeError, KeyError) as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}


# ============================================================================
# TOOL: Analysis Planner (Phase 4 foundation)
# ============================================================================

async def analysis_planner(
    objective: str,
    dataset_ids: Optional[List[int]] = None,
    include_visualization: bool = True,
    include_robustness: bool = False,
) -> Dict[str, Any]:
    """Create a tool-aware analysis plan using available OWID agent tools."""
    try:
        goal = str(objective or "").strip()
        if not goal:
            return {"status": "error", "error": "objective cannot be empty"}

        dataset_ids = [int(d) for d in (dataset_ids or [])]
        goal_l = goal.lower()

        steps: List[Dict[str, Any]] = []
        step_id = 1

        def add_step(tool: str, reason: str, params: Dict[str, Any]) -> None:
            nonlocal step_id
            steps.append({
                "step": step_id,
                "tool": tool,
                "reason": reason,
                "parameters": params,
            })
            step_id += 1

        if dataset_ids:
            add_step(
                "data_profiler",
                "Profile data quality before running analysis.",
                {"dataset_id": dataset_ids[0], "by_column": True},
            )
        else:
            add_step(
                "list_local_datasets",
                "List available datasets to pick valid inputs for analysis.",
                {"limit": 50},
            )

        if "correl" in goal_l:
            if dataset_ids:
                add_step(
                    "correlation_analyzer",
                    "Compute structured correlation metrics for the objective.",
                    {"dataset_id": dataset_ids[0], "method": "pooled"},
                )
        if any(k in goal_l for k in ["regress", "effect", "impact", "determinant", "causal"]):
            if dataset_ids:
                add_step(
                    "regression_engine",
                    "Estimate baseline model to quantify relationships.",
                    {
                        "dataset_id": dataset_ids[0],
                        "dependent": "<define_dependent>",
                        "independents": ["<define_independent_1>"],
                        "model": "pooled",
                    },
                )

        if any(k in goal_l for k in ["segment", "group", "region", "income", "oecd", "heterogene"]):
            if dataset_ids:
                add_step(
                    "group_classifier",
                    "Classify entities for heterogeneity/segment analysis.",
                    {"dataset_id": dataset_ids[0], "group_by": "region"},
                )

        if include_visualization and dataset_ids:
            chart_type = "line" if any(k in goal_l for k in ["trend", "series", "time"]) else "scatter"
            add_step(
                "smart_visualizer",
                "Produce a reproducible chart spec for communication.",
                {"dataset_id": dataset_ids[0], "chart_type": chart_type},
            )

        if include_robustness and dataset_ids:
            add_step(
                "regression_engine",
                "Run a robustness variant with stronger controls/fixed effects.",
                {
                    "dataset_id": dataset_ids[0],
                    "dependent": "<define_dependent>",
                    "independents": ["<define_independent_1>", "<define_independent_2>"],
                    "model": "fe_two_way",
                },
            )

        if not dataset_ids:
            next_action = "Run list_local_datasets first, then rerun analysis_planner with selected dataset_ids."
        else:
            next_action = "Execute steps in order and replace placeholder parameter values where needed."

        return {
            "status": "success",
            "objective": goal,
            "dataset_ids": dataset_ids,
            "steps": steps,
            "next_action": next_action,
        }
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e)}
    except (ValueError, TypeError, KeyError) as e:
        return {"status": "error", "error": str(e)}


# ============================================================================
# TOOL: Caveat Engine (Phase 4)
# ============================================================================

async def caveat_engine(
    dataset_id: int,
    value_columns: Optional[List[str]] = None,
    sample_threshold: int = 30,
    missing_threshold: float = 0.30,
    concentration_threshold: float = 0.60,
    imputation_threshold: float = 0.20,
) -> Dict[str, Any]:
    """Generate automatic caveats for analysis reliability and interpretation."""
    try:
        dataset, df = _load_catalog_dataset_frame(int(dataset_id))
        if df.empty:
            return {"status": "error", "error": "Dataset is empty", "dataset_id": dataset_id}

        entity_col = _detect_entity_column(df)
        year_col = _detect_year_column(df)
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        target_cols = [c for c in (value_columns or []) if c in df.columns]
        if not target_cols:
            excluded = {entity_col, year_col}
            target_cols = [c for c in numeric_cols if c not in excluded]
        if not target_cols:
            target_cols = numeric_cols[:3]

        caveats: List[Dict[str, Any]] = []

        row_count = int(len(df))
        if row_count < int(sample_threshold):
            caveats.append(
                {
                    "code": "small_sample",
                    "severity": "high",
                    "message": "Small sample size may yield unstable estimates.",
                    "evidence": {"row_count": row_count, "threshold": int(sample_threshold)},
                }
            )

        if target_cols:
            miss_ratio = float(df[target_cols].isna().sum().sum() / (len(df) * max(len(target_cols), 1)))
            if miss_ratio > float(missing_threshold):
                caveats.append(
                    {
                        "code": "high_missingness",
                        "severity": "high" if miss_ratio > 0.5 else "medium",
                        "message": "High missingness may bias comparisons and model coefficients.",
                        "evidence": {"missing_ratio": round(miss_ratio, 4), "threshold": float(missing_threshold)},
                    }
                )

        if "_is_imputed" in df.columns:
            imputed_ratio = float(pd.to_numeric(df["_is_imputed"], errors="coerce").fillna(0).astype(bool).mean())
            if imputed_ratio > float(imputation_threshold):
                caveats.append(
                    {
                        "code": "high_imputation",
                        "severity": "medium",
                        "message": "A high share of rows appears imputed; interpret causal claims cautiously.",
                        "evidence": {"imputed_ratio": round(imputed_ratio, 4), "threshold": float(imputation_threshold)},
                    }
                )

        if entity_col and entity_col in df.columns:
            ent = df[entity_col].astype(str).str.strip()
            if len(ent) > 0:
                top_share = float(ent.value_counts(normalize=True, dropna=False).iloc[0])
                if top_share > float(concentration_threshold):
                    caveats.append(
                        {
                            "code": "geographic_concentration",
                            "severity": "medium",
                            "message": "Observations are concentrated in few entities, reducing representativeness.",
                            "evidence": {"top_entity_share": round(top_share, 4), "threshold": float(concentration_threshold)},
                        }
                    )

        if year_col and year_col in df.columns:
            years = pd.to_numeric(df[year_col], errors="coerce").dropna()
            if not years.empty:
                span = int(years.max() - years.min())
                if span < 5:
                    caveats.append(
                        {
                            "code": "short_time_span",
                            "severity": "low",
                            "message": "Short time coverage may miss medium-term dynamics.",
                            "evidence": {"year_span": span, "min_year": int(years.min()), "max_year": int(years.max())},
                        }
                    )

        return {
            "status": "success",
            "dataset_id": int(dataset_id),
            "dataset_name": dataset.get("indicator_name") or dataset.get("file_name"),
            "target_columns": target_cols,
            "caveat_count": len(caveats),
            "caveats": caveats,
            "summary": "No major caveats detected." if not caveats else "Caveats detected. Review before drawing strong conclusions.",
        }
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}
    except (ValueError, TypeError, KeyError) as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}


# ============================================================================
# TOOL: Robustness Checker (Phase 4)
# ============================================================================

async def robustness_checker(
    dataset_id: int,
    dependent: str,
    independents: List[str],
    key_variable: Optional[str] = None,
    models: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Check coefficient stability across multiple model specifications."""
    try:
        if not dependent:
            return {"status": "error", "error": "dependent is required"}
        if not independents:
            return {"status": "error", "error": "independents cannot be empty"}

        key_var = key_variable or independents[0]
        if key_var not in independents:
            return {"status": "error", "error": "key_variable must be included in independents"}

        dataset, df = _load_catalog_dataset_frame(int(dataset_id))
        entity_col = _detect_entity_column(df)
        year_col = _detect_year_column(df)

        requested_models = [str(m).strip().lower() for m in (models or ["pooled", "fe_entity", "fe_two_way"])]
        allowed = {"pooled", "fe_entity", "fe_two_way"}
        invalid = [m for m in requested_models if m not in allowed]
        if invalid:
            return {"status": "error", "error": f"Invalid model(s): {invalid}. Allowed: pooled, fe_entity, fe_two_way"}

        run_models: List[str] = []
        for m in requested_models:
            if m in {"fe_entity", "fe_two_way"} and not entity_col:
                continue
            if m == "fe_two_way" and not year_col:
                continue
            run_models.append(m)
        if not run_models:
            return {"status": "error", "error": "No runnable models for this dataset (missing entity/year columns)."}

        model_results: List[Dict[str, Any]] = []
        warnings: List[str] = []
        coeff_values: List[float] = []

        for model_name in run_models:
            res = await regression_engine(
                dataset_id=int(dataset_id),
                dependent=dependent,
                independents=independents,
                model=model_name,
                entity_column=entity_col,
                year_column=year_col,
            )
            if res.get("status") != "success":
                warnings.append(f"Model {model_name} failed: {res.get('error')}")
                continue
            coef = res.get("coefficients", {}).get(key_var)
            if coef is None:
                warnings.append(f"Model {model_name} did not produce coefficient for key variable '{key_var}'.")
            else:
                coeff_values.append(float(coef))
            model_results.append(
                {
                    "model": model_name,
                    "n_obs": res.get("n_obs"),
                    "r_squared": res.get("r_squared"),
                    "coefficient_key_variable": coef,
                    "all_coefficients": res.get("coefficients", {}),
                    "warnings": res.get("warnings", []),
                }
            )

        if not model_results:
            return {"status": "error", "error": "All robustness models failed.", "warnings": warnings}

        stability: Dict[str, Any] = {"key_variable": key_var}
        if len(coeff_values) >= 2:
            max_coef = max(coeff_values)
            min_coef = min(coeff_values)
            abs_range = abs(max_coef - min_coef)
            base = abs(coeff_values[0]) if abs(coeff_values[0]) > 1e-12 else 1.0
            pct_range = abs_range / base
            stability.update(
                {
                    "min_coefficient": round(min_coef, 8),
                    "max_coefficient": round(max_coef, 8),
                    "absolute_range": round(abs_range, 8),
                    "relative_range": round(pct_range, 8),
                    "is_stable": pct_range < 0.25,
                }
            )
            if pct_range >= 0.25:
                warnings.append("Key coefficient varies materially across model specifications.")
        else:
            stability.update(
                {
                    "min_coefficient": coeff_values[0] if coeff_values else None,
                    "max_coefficient": coeff_values[0] if coeff_values else None,
                    "absolute_range": 0.0 if coeff_values else None,
                    "relative_range": 0.0 if coeff_values else None,
                    "is_stable": True if coeff_values else False,
                }
            )
            warnings.append("Robustness assessment limited because fewer than 2 valid coefficient estimates were available.")

        return {
            "status": "success",
            "dataset_id": int(dataset_id),
            "dataset_name": dataset.get("indicator_name") or dataset.get("file_name"),
            "dependent": dependent,
            "independents": independents,
            "models_run": [m["model"] for m in model_results],
            "results": model_results,
            "stability": stability,
            "warnings": warnings,
        }
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}
    except (ValueError, TypeError, KeyError) as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}


# ============================================================================
# TOOL: Cross Source Validator (Phase 5 optional)
# ============================================================================

async def cross_source_validator(
    dataset_ids: List[int],
    value_column: Optional[str] = None,
    min_overlap: int = 20,
) -> Dict[str, Any]:
    """Validate consistency between datasets from different sources on overlapping entity-year points."""
    try:
        if len(dataset_ids) < 2:
            return {"status": "error", "error": "cross_source_validator requires at least 2 dataset_ids"}

        prepared: List[Dict[str, Any]] = []
        sources: Set[str] = set()

        for ds_id in dataset_ids:
            dataset, df = _load_catalog_dataset_frame(int(ds_id))
            entity_col = _detect_entity_column(df)
            year_col = _detect_year_column(df)
            if not entity_col or not year_col:
                return {
                    "status": "error",
                    "error": f"Dataset {ds_id} missing entity/year columns",
                    "dataset_id": ds_id,
                }

            harmonized = df[entity_col].apply(_harmonize_entity).apply(pd.Series)
            work = df.copy()
            work["entity_key"] = harmonized["entity_key"]
            work["year_num"] = pd.to_numeric(work[year_col], errors="coerce")
            work = work.dropna(subset=["entity_key", "year_num"])
            work["year_num"] = work["year_num"].astype(int)

            vcol = value_column if value_column and value_column in work.columns else _infer_value_column(work, entity_col, year_col)
            if not vcol or vcol not in work.columns:
                return {"status": "error", "error": f"Dataset {ds_id} has no usable value column"}

            source_name = str(dataset.get("source") or "unknown").strip().lower() or "unknown"
            sources.add(source_name)
            prepared.append(
                {
                    "dataset_id": int(ds_id),
                    "source": source_name,
                    "value_column": vcol,
                    "frame": work[["entity_key", "year_num", vcol]].rename(columns={vcol: f"value_{ds_id}"}),
                }
            )

        pairwise: List[Dict[str, Any]] = []
        warnings: List[str] = []

        for i in range(len(prepared)):
            for j in range(i + 1, len(prepared)):
                a = prepared[i]
                b = prepared[j]
                merged = a["frame"].merge(b["frame"], on=["entity_key", "year_num"], how="inner")
                overlap = int(len(merged))
                if overlap == 0:
                    pairwise.append(
                        {
                            "dataset_a": a["dataset_id"],
                            "dataset_b": b["dataset_id"],
                            "source_a": a["source"],
                            "source_b": b["source"],
                            "overlap_points": 0,
                            "correlation": None,
                            "mean_abs_diff": None,
                        }
                    )
                    warnings.append(f"No overlap between datasets {a['dataset_id']} and {b['dataset_id']}.")
                    continue

                col_a = f"value_{a['dataset_id']}"
                col_b = f"value_{b['dataset_id']}"
                x = pd.to_numeric(merged[col_a], errors="coerce")
                y = pd.to_numeric(merged[col_b], errors="coerce")
                valid = pd.DataFrame({"x": x, "y": y}).dropna()
                corr_val = None
                mad_val = None
                if len(valid) >= 2:
                    corr = valid["x"].corr(valid["y"])
                    corr_val = None if pd.isna(corr) else float(corr)
                    mad_val = float((valid["x"] - valid["y"]).abs().mean())
                if overlap < int(min_overlap):
                    warnings.append(
                        f"Low overlap ({overlap}) between datasets {a['dataset_id']} and {b['dataset_id']}."
                    )

                pairwise.append(
                    {
                        "dataset_a": a["dataset_id"],
                        "dataset_b": b["dataset_id"],
                        "source_a": a["source"],
                        "source_b": b["source"],
                        "overlap_points": overlap,
                        "correlation": None if corr_val is None else round(corr_val, 6),
                        "mean_abs_diff": None if mad_val is None else round(mad_val, 6),
                    }
                )

        if len(sources) < 2:
            warnings.append("Datasets appear to come from a single source; cross-source validation is limited.")

        return {
            "status": "success",
            "dataset_ids": [int(d) for d in dataset_ids],
            "sources": sorted(list(sources)),
            "pairwise": pairwise,
            "warnings": warnings,
        }
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e), "dataset_ids": dataset_ids}
    except (ValueError, TypeError, KeyError) as e:
        return {"status": "error", "error": str(e), "dataset_ids": dataset_ids}


# ============================================================================
# TOOL: Assumption Checker (Phase 5 optional)
# ============================================================================

async def assumption_checker(
    dataset_id: int,
    dependent: str,
    independents: List[str],
) -> Dict[str, Any]:
    """Check basic regression assumptions: sample size, collinearity, residual shape, and heteroskedasticity proxy."""
    try:
        if not dependent:
            return {"status": "error", "error": "dependent is required"}
        if not independents:
            return {"status": "error", "error": "independents cannot be empty"}

        dataset, df = _load_catalog_dataset_frame(int(dataset_id))
        missing_cols = [c for c in [dependent, *independents] if c not in df.columns]
        if missing_cols:
            return {"status": "error", "error": f"Columns not found: {missing_cols}", "dataset_id": dataset_id}

        # Reuse pooled model baseline and compute diagnostics with run_python_analysis
        code = """
y_col = %(y_col)r
x_cols = %(x_cols)r
work = df.copy()
for c in [y_col] + x_cols:
    work[c] = pd.to_numeric(work[c], errors="coerce")
work = work.dropna(subset=[y_col] + x_cols)

n_obs = len(work)
X = work[x_cols].to_numpy()
Y = work[y_col].to_numpy()
X_design = np.column_stack([np.ones(len(X)), X])
beta, _, _, _ = np.linalg.lstsq(X_design, Y, rcond=None)
fitted = X_design @ beta
resid = Y - fitted

max_abs_corr = 0.0
collinearity_flag = False
if len(x_cols) >= 2:
    cmat = work[x_cols].corr().abs()
    if cmat.shape[0] > 1:
        vals = []
        for i in range(cmat.shape[0]):
            for j in range(i + 1, cmat.shape[1]):
                vals.append(cmat.iloc[i, j])
        if vals:
            max_abs_corr = max(vals)
            collinearity_flag = max_abs_corr >= 0.85

resid_std = np.std(resid) if len(resid) else 0.0
if resid_std > 0:
    resid_center = (resid - np.mean(resid)) / resid_std
else:
    resid_center = resid
skew = np.mean(resid_center ** 3) if len(resid_center) else 0.0
kurtosis = np.mean(resid_center ** 4) - 3.0 if len(resid_center) else 0.0
normality_flag = abs(skew) > 1.0 or abs(kurtosis) > 2.0

hetero_proxy = None
hetero_flag = False
if len(resid) > 1:
    ar = np.abs(resid)
    corr = np.corrcoef(np.abs(fitted), ar)[0, 1]
    if not np.isnan(corr):
        hetero_proxy = corr
        hetero_flag = abs(hetero_proxy) > 0.3

assumptions = []
assumptions.append({
    "name": "sample_size",
    "status": "pass" if n_obs >= 30 else "warn",
    "evidence": {"n_obs": n_obs, "recommended_min": 30},
})
assumptions.append({
    "name": "multicollinearity",
    "status": "warn" if collinearity_flag else "pass",
    "evidence": {"max_abs_corr": round(max_abs_corr, 6), "threshold": 0.85},
})
assumptions.append({
    "name": "residual_normality_proxy",
    "status": "warn" if normality_flag else "pass",
    "evidence": {"skewness": round(skew, 6), "excess_kurtosis": round(kurtosis, 6), "thresholds": {"skew": 1.0, "kurtosis": 2.0}},
})
assumptions.append({
    "name": "heteroskedasticity_proxy",
    "status": "warn" if hetero_flag else "pass",
    "evidence": {"corr_abs_fitted_resid": None if hetero_proxy is None else round(hetero_proxy, 6), "threshold": 0.3},
})

warnings = [a["name"] for a in assumptions if a["status"] == "warn"]
result = {
    "n_obs": n_obs,
    "assumptions": assumptions,
    "warnings": warnings,
}
"""
        analysis = await run_python_analysis(
            dataset_ids=[int(dataset_id)],
            python_code=code % {"y_col": dependent, "x_cols": [str(c) for c in independents]},
        )
        if analysis.get("status") != "success":
            return {"status": "error", "error": analysis.get("error", "assumption check failed"), "dataset_id": dataset_id}

        payload = analysis.get("result")
        if not isinstance(payload, dict):
            return {"status": "error", "error": "Assumption checker returned invalid payload", "dataset_id": dataset_id}

        return {
            "status": "success",
            "dataset_id": int(dataset_id),
            "dataset_name": dataset.get("indicator_name") or dataset.get("file_name"),
            "dependent": dependent,
            "independents": independents,
            "n_obs": payload.get("n_obs"),
            "assumptions": payload.get("assumptions", []),
            "warnings": payload.get("warnings", []),
        }
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}
    except (ValueError, TypeError, KeyError) as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}


# ============================================================================
# TOOL: Trend Analyzer (Phase 5 optional)
# ============================================================================

async def trend_analyzer(
    dataset_id: int,
    value_column: Optional[str] = None,
    entity_column: Optional[str] = None,
    year_column: Optional[str] = None,
    min_points: int = 5,
    top_entities: int = 10,
) -> Dict[str, Any]:
    """Analyze linear trend direction and change rates overall and by entity."""
    try:
        dataset, df = _load_catalog_dataset_frame(int(dataset_id))
        e_col = entity_column or _detect_entity_column(df)
        y_col = year_column or _detect_year_column(df)
        if not e_col or e_col not in df.columns:
            return {"status": "error", "error": "Entity column not found", "dataset_id": dataset_id}
        if not y_col or y_col not in df.columns:
            return {"status": "error", "error": "Year column not found", "dataset_id": dataset_id}

        v_col = value_column if value_column and value_column in df.columns else _infer_value_column(df, e_col, y_col)
        if not v_col or v_col not in df.columns:
            return {"status": "error", "error": "Value column not found", "dataset_id": dataset_id}

        safe_min_points = max(2, int(min_points))
        safe_top_entities = max(1, min(int(top_entities), 50))

        work = df[[e_col, y_col, v_col]].copy()
        work[y_col] = pd.to_numeric(work[y_col], errors="coerce")
        work[v_col] = pd.to_numeric(work[v_col], errors="coerce")
        work = work.dropna(subset=[e_col, y_col, v_col])
        if work.empty:
            return {"status": "error", "error": "No valid rows after numeric conversion", "dataset_id": dataset_id}

        work[y_col] = work[y_col].astype(int)
        overall_series = work.groupby(y_col)[v_col].mean().sort_index()
        if len(overall_series) < 2:
            return {"status": "error", "error": "At least 2 year points are required", "dataset_id": dataset_id}

        years = overall_series.index.to_numpy()
        values = overall_series.to_numpy()
        slope = float(np.polyfit(years, values, 1)[0])
        direction = "increasing" if slope > 0 else ("decreasing" if slope < 0 else "flat")
        first_value = float(values[0])
        last_value = float(values[-1])
        change_pct = None if abs(first_value) < 1e-12 else round((last_value - first_value) / abs(first_value), 8)

        biggest_jump = None
        if len(overall_series) >= 2:
            diffs = overall_series.diff().dropna()
            if not diffs.empty:
                max_year = int(diffs.abs().idxmax())
                prev_year = int(max_year - 1)
                biggest_jump = {
                    "from_year": prev_year,
                    "to_year": max_year,
                    "delta": round(float(diffs.loc[max_year]), 8),
                }

        entity_rows: List[Dict[str, Any]] = []
        grouped = work.groupby(e_col)
        for entity_name, g in grouped:
            series = g.groupby(y_col)[v_col].mean().sort_index()
            if len(series) < safe_min_points:
                continue
            e_years = series.index.to_numpy()
            e_values = series.to_numpy()
            e_slope = float(np.polyfit(e_years, e_values, 1)[0])
            e_direction = "increasing" if e_slope > 0 else ("decreasing" if e_slope < 0 else "flat")
            e_first = float(e_values[0])
            e_last = float(e_values[-1])
            e_change_pct = None if abs(e_first) < 1e-12 else round((e_last - e_first) / abs(e_first), 8)
            entity_rows.append(
                {
                    "entity": str(entity_name),
                    "n_years": int(len(series)),
                    "slope": round(e_slope, 8),
                    "direction": e_direction,
                    "change_pct": e_change_pct,
                }
            )

        entity_rows = sorted(entity_rows, key=lambda r: (r["n_years"], abs(r["slope"])), reverse=True)[:safe_top_entities]
        warnings: List[str] = []
        if not entity_rows:
            warnings.append("No entity trends met min_points; reduce min_points to include more entities.")

        return {
            "status": "success",
            "dataset_id": int(dataset_id),
            "dataset_name": dataset.get("indicator_name") or dataset.get("file_name"),
            "entity_column": e_col,
            "year_column": y_col,
            "value_column": v_col,
            "overall_trend": {
                "n_years": int(len(overall_series)),
                "start_year": int(years[0]),
                "end_year": int(years[-1]),
                "slope": round(slope, 8),
                "direction": direction,
                "change_pct": change_pct,
                "largest_annual_jump": biggest_jump,
            },
            "entity_trends": entity_rows,
            "warnings": warnings,
        }
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}
    except (ValueError, TypeError, KeyError) as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}


# ============================================================================
# TOOL: Causality Tester (Phase 5 optional)
# ============================================================================

async def causality_tester(
    dataset_id: int,
    dependent: str,
    driver: str,
    entity_column: Optional[str] = None,
    year_column: Optional[str] = None,
    max_lag: int = 3,
    min_points: int = 20,
) -> Dict[str, Any]:
    """Run lead-lag and placebo checks to assess temporal precedence between two variables."""
    try:
        if not dependent or not driver:
            return {"status": "error", "error": "dependent and driver are required"}
        dataset, df = _load_catalog_dataset_frame(int(dataset_id))

        e_col = entity_column or _detect_entity_column(df)
        y_col = year_column or _detect_year_column(df)
        if not e_col or e_col not in df.columns:
            return {"status": "error", "error": "Entity column not found", "dataset_id": dataset_id}
        if not y_col or y_col not in df.columns:
            return {"status": "error", "error": "Year column not found", "dataset_id": dataset_id}

        missing_cols = [c for c in [dependent, driver] if c not in df.columns]
        if missing_cols:
            return {"status": "error", "error": f"Columns not found: {missing_cols}", "dataset_id": dataset_id}

        safe_max_lag = max(1, min(int(max_lag), 8))
        safe_min_points = max(10, int(min_points))
        work = df[[e_col, y_col, dependent, driver]].copy()
        work[y_col] = pd.to_numeric(work[y_col], errors="coerce")
        work[dependent] = pd.to_numeric(work[dependent], errors="coerce")
        work[driver] = pd.to_numeric(work[driver], errors="coerce")
        work = work.dropna(subset=[e_col, y_col, dependent, driver]).sort_values([e_col, y_col])
        if len(work) < safe_min_points:
            return {
                "status": "error",
                "error": f"Not enough valid observations ({len(work)}). Need at least {safe_min_points}.",
                "dataset_id": dataset_id,
            }

        panel = work.copy()
        lead_results: List[Dict[str, Any]] = []
        placebo_results: List[Dict[str, Any]] = []

        for lag in range(0, safe_max_lag + 1):
            shifted_driver = panel.groupby(e_col)[driver].shift(lag)
            valid = pd.DataFrame({"x": shifted_driver, "y": panel[dependent]}).dropna()
            corr = valid["x"].corr(valid["y"]) if len(valid) >= 2 else None
            lead_results.append(
                {
                    "lag": lag,
                    "n_obs": int(len(valid)),
                    "corr_x_leads_y": None if corr is None or pd.isna(corr) else round(float(corr), 8),
                }
            )

            if lag > 0:
                shifted_dep = panel.groupby(e_col)[dependent].shift(lag)
                placebo_valid = pd.DataFrame({"x": panel[driver], "y": shifted_dep}).dropna()
                placebo_corr = placebo_valid["x"].corr(placebo_valid["y"]) if len(placebo_valid) >= 2 else None
                placebo_results.append(
                    {
                        "lag": lag,
                        "n_obs": int(len(placebo_valid)),
                        "corr_y_leads_x": None if placebo_corr is None or pd.isna(placebo_corr) else round(float(placebo_corr), 8),
                    }
                )

        scored = [r for r in lead_results if r["lag"] > 0 and r["corr_x_leads_y"] is not None]
        if not scored:
            return {"status": "error", "error": "Unable to compute lead-lag correlations", "dataset_id": dataset_id}

        best = max(scored, key=lambda r: abs(r["corr_x_leads_y"]))
        placebo_at_best = next((r for r in placebo_results if r["lag"] == best["lag"]), None)
        placebo_corr = placebo_at_best["corr_y_leads_x"] if placebo_at_best else None
        current_corr = lead_results[0]["corr_x_leads_y"]

        passes_placebo = False
        if best["corr_x_leads_y"] is not None:
            best_abs = abs(best["corr_x_leads_y"])
            placebo_abs = abs(placebo_corr) if placebo_corr is not None else 0.0
            current_abs = abs(current_corr) if current_corr is not None else 0.0
            passes_placebo = best_abs > placebo_abs + 0.05 and best_abs >= current_abs

        interpretation = (
            f"Strongest driver lead effect at lag={best['lag']} with corr={best['corr_x_leads_y']}."
            if passes_placebo
            else "Temporal precedence signal is weak or not robust versus placebo."
        )
        warnings: List[str] = []
        if not passes_placebo:
            warnings.append("Placebo check did not clearly support directional precedence.")

        return {
            "status": "success",
            "dataset_id": int(dataset_id),
            "dataset_name": dataset.get("indicator_name") or dataset.get("file_name"),
            "dependent": dependent,
            "driver": driver,
            "lead_lag": lead_results,
            "placebo_reverse": placebo_results,
            "signal": {
                "best_lag": int(best["lag"]),
                "best_corr": best["corr_x_leads_y"],
                "contemporaneous_corr": current_corr,
                "placebo_corr_same_lag": placebo_corr,
                "passes_placebo": passes_placebo,
                "interpretation": interpretation,
            },
            "warnings": warnings,
        }
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}
    except (ValueError, TypeError, KeyError) as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}


# ============================================================================
# TOOL: Dimensionality Reducer (Phase 5 optional)
# ============================================================================

async def dimensionality_reducer(
    dataset_id: int,
    columns: Optional[List[str]] = None,
    n_components: int = 2,
) -> Dict[str, Any]:
    """Run a lightweight PCA-style reduction over numeric columns."""
    try:
        dataset, df = _load_catalog_dataset_frame(int(dataset_id))
        selected_cols = [str(c) for c in (columns or []) if str(c) in df.columns]
        if not selected_cols:
            selected_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if len(selected_cols) < 2:
            return {"status": "error", "error": "At least 2 numeric columns are required", "dataset_id": dataset_id}

        matrix = df[selected_cols].apply(pd.to_numeric, errors="coerce").dropna()
        if matrix.empty or len(matrix) < 3:
            return {"status": "error", "error": "Not enough complete rows for dimensionality reduction", "dataset_id": dataset_id}

        max_components = min(len(selected_cols), int(n_components))
        safe_components = max(1, min(max_components, 5))

        X = matrix.to_numpy(dtype=float)
        means = X.mean(axis=0)
        stds = X.std(axis=0)
        stds[stds == 0] = 1.0
        Z = (X - means) / stds
        cov = np.cov(Z, rowvar=False)
        eigvals, eigvecs = np.linalg.eigh(cov)
        order = np.argsort(eigvals)[::-1]
        eigvals = eigvals[order]
        eigvecs = eigvecs[:, order]

        eigvals_pos = np.clip(eigvals, 0.0, None)
        total_var = float(eigvals_pos.sum()) if eigvals_pos.size else 0.0
        if total_var <= 0:
            return {"status": "error", "error": "Unable to compute explained variance", "dataset_id": dataset_id}

        components = eigvecs[:, :safe_components]
        scores = Z @ components
        explained = eigvals_pos[:safe_components] / total_var
        explained_cumulative = np.cumsum(explained)

        loadings: List[Dict[str, Any]] = []
        for i in range(safe_components):
            comp_name = f"PC{i + 1}"
            pairs = []
            for j, col in enumerate(selected_cols):
                pairs.append({"column": col, "loading": round(float(components[j, i]), 8)})
            pairs = sorted(pairs, key=lambda r: abs(r["loading"]), reverse=True)
            loadings.append({"component": comp_name, "top_loadings": pairs[: min(5, len(pairs))]})

        sample_rows: List[Dict[str, Any]] = []
        limit = min(10, scores.shape[0])
        for i in range(limit):
            row = {}
            for j in range(safe_components):
                row[f"PC{j + 1}"] = round(float(scores[i, j]), 8)
            sample_rows.append(row)

        return {
            "status": "success",
            "dataset_id": int(dataset_id),
            "dataset_name": dataset.get("indicator_name") or dataset.get("file_name"),
            "columns_used": selected_cols,
            "n_rows_used": int(matrix.shape[0]),
            "n_components": int(safe_components),
            "explained_variance_ratio": [round(float(v), 8) for v in explained.tolist()],
            "explained_variance_cumulative": [round(float(v), 8) for v in explained_cumulative.tolist()],
            "component_loadings": loadings,
            "scores_preview": sample_rows,
            "warnings": [],
        }
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}
    except (ValueError, TypeError, KeyError) as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}


# ============================================================================
# TOOL: Convergence Analyzer (Phase 5 optional)
# ============================================================================

async def convergence_analyzer(
    dataset_id: int,
    value_column: Optional[str] = None,
    entity_column: Optional[str] = None,
    year_column: Optional[str] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
) -> Dict[str, Any]:
    """Estimate beta/sigma convergence diagnostics on panel-style data."""
    try:
        dataset, df = _load_catalog_dataset_frame(int(dataset_id))
        e_col = entity_column or _detect_entity_column(df)
        y_col = year_column or _detect_year_column(df)
        if not e_col or e_col not in df.columns:
            return {"status": "error", "error": "Entity column not found", "dataset_id": dataset_id}
        if not y_col or y_col not in df.columns:
            return {"status": "error", "error": "Year column not found", "dataset_id": dataset_id}

        v_col = value_column if value_column and value_column in df.columns else _infer_value_column(df, e_col, y_col)
        if not v_col or v_col not in df.columns:
            return {"status": "error", "error": "Value column not found", "dataset_id": dataset_id}

        work = df[[e_col, y_col, v_col]].copy()
        work[y_col] = pd.to_numeric(work[y_col], errors="coerce")
        work[v_col] = pd.to_numeric(work[v_col], errors="coerce")
        work = work.dropna(subset=[e_col, y_col, v_col])
        work = work[work[v_col] > 0]
        if work.empty:
            return {"status": "error", "error": "No positive observations available", "dataset_id": dataset_id}

        work[y_col] = work[y_col].astype(int)
        sy = int(start_year) if start_year is not None else int(work[y_col].min())
        ey = int(end_year) if end_year is not None else int(work[y_col].max())
        if ey <= sy:
            return {"status": "error", "error": "end_year must be greater than start_year", "dataset_id": dataset_id}

        start_vals = work[work[y_col] == sy].groupby(e_col)[v_col].mean()
        end_vals = work[work[y_col] == ey].groupby(e_col)[v_col].mean()
        common = start_vals.index.intersection(end_vals.index)
        if len(common) < 3:
            return {"status": "error", "error": "Need at least 3 entities with start/end values", "dataset_id": dataset_id}

        s = start_vals.loc[common]
        e = end_vals.loc[common]
        years_gap = ey - sy
        growth = (np.log(e.to_numpy()) - np.log(s.to_numpy())) / years_gap
        initial = np.log(s.to_numpy())
        X = np.column_stack([np.ones(len(initial)), initial])
        beta_coef, _, _, _ = np.linalg.lstsq(X, growth, rcond=None)
        beta_slope = float(beta_coef[1])
        beta_converging = beta_slope < 0

        sigma_rows = (
            work.groupby(y_col)[v_col]
            .agg(lambda s: np.std(np.log(s.to_numpy())) if len(s) >= 3 else np.nan)
            .dropna()
            .sort_index()
        )
        sigma_slope = None
        sigma_converging = None
        if len(sigma_rows) >= 2:
            yv = sigma_rows.index.to_numpy()
            xv = sigma_rows.to_numpy()
            sigma_slope = float(np.polyfit(yv, xv, 1)[0])
            sigma_converging = sigma_slope < 0

        warnings: List[str] = []
        if sigma_slope is None:
            warnings.append("Sigma convergence unavailable: insufficient yearly dispersion points.")

        return {
            "status": "success",
            "dataset_id": int(dataset_id),
            "dataset_name": dataset.get("indicator_name") or dataset.get("file_name"),
            "entity_column": e_col,
            "year_column": y_col,
            "value_column": v_col,
            "period": {"start_year": sy, "end_year": ey, "years": years_gap},
            "sample": {"entities": int(len(common)), "obs_used": int(len(work))},
            "beta_convergence": {
                "beta_slope": round(beta_slope, 8),
                "is_converging": beta_converging,
            },
            "sigma_convergence": {
                "sigma_slope": None if sigma_slope is None else round(sigma_slope, 8),
                "is_converging": sigma_converging,
                "start_sigma": round(float(sigma_rows.iloc[0]), 8) if len(sigma_rows) else None,
                "end_sigma": round(float(sigma_rows.iloc[-1]), 8) if len(sigma_rows) else None,
            },
            "warnings": warnings,
        }
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}
    except (ValueError, TypeError, KeyError) as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}


# ============================================================================
# TOOL 3: Preview Data
# ============================================================================

async def preview_data(
    dataset_id: str,
    limit: int = 10,
    include_stats: bool = True
) -> Dict[str, Any]:
    """
    Preview a dataset by showing the first N rows.
    
    This tool loads a dataset (either local or from a source) and returns
    a preview with sample data, column information, and basic statistics.
    
    Args:
        dataset_id: Dataset identifier (local ID or OWID slug)
        limit: Number of rows to preview (default 10, max 100)
        include_stats: Whether to include basic statistics (default True)
    
    Returns:
        Dictionary with:
        - sample_data: First N rows as list of dicts
        - columns: Column names and types
        - stats: Basic statistics (if include_stats=True)
        - total_rows: Total number of rows in dataset
        - dataset_info: Metadata about the dataset
    
    Example:
        >>> preview = await preview_data("gdp-per-capita", limit=5)
        >>> print(preview['sample_data'])
        [{'country': 'Brazil', 'year': 2020, 'gdp_per_capita': 15000.50}, ...]
    """
    try:
        config = get_config()
        limit = min(limit, 100)  # Cap at 100 rows
        
        # Try to find dataset in catalog first
        catalog = DatasetCatalog(config)
        dataset = catalog.get_dataset(dataset_id)
        
        if dataset and dataset.get('file_path'):
            # Load local dataset
            df = pd.read_csv(dataset['file_path'])
        else:
            # Try to fetch from OWID if it looks like a slug
            if '-' in dataset_id and not dataset_id.endswith('.csv'):
                owid = OWIDSource(config.get_directory('raw'))
                df = owid.fetch(dataset_id)
            else:
                return {
                    "status": "error",
                    "error": f"Dataset '{dataset_id}' not found locally or in OWID",
                    "dataset_id": dataset_id
                }
        
        if df.empty:
            return {
                "status": "error",
                "error": f"Dataset '{dataset_id}' is empty",
                "dataset_id": dataset_id
            }
        
        # Get sample data
        sample_df = df.head(limit)
        sample_data = sample_df.to_dict(orient='records')
        
        # Get column info
        columns = []
        for col in df.columns:
            col_info = {
                "name": col,
                "type": str(df[col].dtype),
                "null_count": int(df[col].isna().sum()),
                "null_percentage": float(df[col].isna().sum() / len(df) * 100)
            }
            
            # Add sample values
            sample_values = df[col].dropna().head(3).tolist()
            col_info["sample_values"] = sample_values
            
            columns.append(col_info)
        
        # Build response
        result = {
            "status": "success",
            "dataset_id": dataset_id,
            "total_rows": len(df),
            "preview_rows": len(sample_data),
            "columns": columns,
            "sample_data": sample_data
        }
        
        # Include statistics if requested
        if include_stats:
            stats = {}
            
            # Numeric columns stats
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                stats["numeric_summary"] = {
                    col: {
                        "min": float(df[col].min()),
                        "max": float(df[col].max()),
                        "mean": float(df[col].mean()),
                        "median": float(df[col].median())
                    }
                    for col in numeric_cols
                }
            
            # Categorical columns (country, entity)
            if 'country' in df.columns:
                stats["countries"] = int(df['country'].nunique())
            if 'entity' in df.columns:
                stats["entities"] = int(df['entity'].nunique())
            
            # Year range
            if 'year' in df.columns:
                stats["year_range"] = {
                    "min": int(df['year'].min()),
                    "max": int(df['year'].max())
                }
            
            result["statistics"] = stats
        
        return result
        
    except TOOL_OPERATION_ERRORS as e:
        return {
            "status": "error",
            "error": str(e),
            "dataset_id": dataset_id,
            "sample_data": []
        }


# ============================================================================
# TOOL 3: Download OWID Data
# ============================================================================

async def download_owid(
    slug: str,
    countries: Optional[List[str]] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    create_ai_package: bool = True
) -> Dict[str, Any]:
    """
    Download data from Our World in Data (OWID).
    
    This tool fetches data from OWID using a grapher slug, cleans it,
    and optionally creates an AI-ready package with metadata.
    
    Args:
        slug: OWID grapher slug (e.g., "gdp-per-capita", "life-expectancy")
        countries: List of country names or ISO codes (e.g., ["BRA", "Argentina"])
        start_year: Starting year for data (e.g., 2010)
        end_year: Ending year for data (e.g., 2023)
        create_ai_package: Whether to create AI package with metadata (default True)
    
    Returns:
        Dictionary with:
        - status: "success" or "error"
        - file_path: Path to saved CSV file
        - metadata: OWID metadata (if available)
        - ai_package: Paths to AI package files (if created)
        - row_count: Number of rows downloaded
        - countries: List of countries in dataset
    
    Example:
        >>> result = await download_owid("gdp-per-capita", 
        ...                              countries=["BRA", "ARG"],
        ...                              start_year=2010,
        ...                              end_year=2023)
        >>> print(result['file_path'])
        '/path/to/gdp_per_capita_owid_latam_2010_2023.csv'
    """
    try:
        config = get_config()
        
        # Initialize OWID source
        raw_dir = config.get_directory('raw')
        owid = OWIDSource(raw_dir)
        
        print(f"📥 Downloading OWID data: {slug}")
        
        # Fetch data with metadata
        df, metadata = owid.fetch_with_metadata(
            slug=slug,
            countries=countries,
            start_year=start_year,
            end_year=end_year
        )
        
        if df.empty:
            return {
                "status": "error",
                "error": f"No data returned for slug '{slug}'",
                "slug": slug
            }
        
        # Determine topic from metadata or use "general"
        topic = "general"
        if metadata.get('title'):
            # Simple topic detection from title
            title_lower = metadata['title'].lower()
            if any(word in title_lower for word in ['gdp', 'economy', 'income', 'poverty']):
                topic = "economy"
            elif any(word in title_lower for word in ['health', 'life', 'mortality']):
                topic = "health"
            elif any(word in title_lower for word in ['population', 'birth', 'death']):
                topic = "population"
        
        # Save cleaned dataset
        from src.cleaning import DataCleaner
        cleaner = DataCleaner(config)
        
        # Clean the data
        df_clean = cleaner.clean_dataset(df)
        
        # Generate identifier
        identifier = slug.replace('-', '_')
        
        # Save to clean directory
        output_path, friendly_name = cleaner.save_clean_dataset(
            data=df_clean,
            topic=topic,
            source="owid",
            coverage="latam",  # Could be inferred from countries
            start_year=start_year,
            end_year=end_year,
            identifier=identifier,
        )
        
        result = {
            "status": "success",
            "slug": slug,
            "file_path": str(output_path),
            "friendly_name": friendly_name,
            "row_count": len(df_clean),
            "column_count": len(df_clean.columns),
            "topic": topic,
        }
        
        # Add countries info
        if 'country' in df_clean.columns:
            result["countries"] = df_clean['country'].unique().tolist()
            result["country_count"] = len(result["countries"])
        
        # Add metadata if available
        if metadata and 'error' not in metadata:
            result["metadata"] = {
                "title": metadata.get('title', ''),
                "description": metadata.get('description', ''),
                "unit": metadata.get('unit', ''),
                "source_name": metadata.get('sources', [{}])[0].get('name', 'OWID') if metadata.get('sources') else 'OWID',
                "last_updated": metadata.get('last_updated', '')
            }
        
        # Create AI package if requested
        if create_ai_package and 'error' not in metadata:
            try:
                from src.ai_packager import create_ai_package_from_owid
                ai_files = create_ai_package_from_owid(
                    csv_path=output_path,
                    owid_metadata=metadata,
                    topic=topic
                )
                result["ai_package"] = {
                    "schema": str(ai_files.get('schema', '')),
                    "context": str(ai_files.get('context', '')),
                    "prompts": str(ai_files.get('prompts', ''))
                }
                print(f"✅ AI package created")
            except TOOL_OPERATION_ERRORS as e:
                print(f"⚠️  AI package creation failed: {e}")
                result["ai_package_error"] = str(e)
        
        return result
        
    except TOOL_OPERATION_ERRORS as e:
        return {
            "status": "error",
            "error": str(e),
            "slug": slug
        }


# ============================================================================
# TOOL 4: Get Metadata
# ============================================================================

async def get_metadata(
    dataset_id: str,
    include_schema: bool = True,
    include_context: bool = True
) -> Dict[str, Any]:
    """
    Get comprehensive metadata for a dataset.
    
    This tool retrieves all available metadata for a dataset including:
    - Basic info (name, source, description)
    - Data schema (columns, types, statistics)
    - OWID context (methodology, sources, limitations)
    - AI-generated prompts and suggestions
    
    Args:
        dataset_id: Dataset identifier (local ID or OWID slug)
        include_schema: Whether to include data schema (default True)
        include_context: Whether to include OWID context (default True)
    
    Returns:
        Dictionary with comprehensive metadata:
        - basic_info: Name, source, description
        - schema: Column definitions and statistics
        - context: OWID metadata (methodology, sources, limitations)
        - prompts: Suggested analysis prompts
        - dataset_stats: Row counts, countries, year range
    
    Example:
        >>> meta = await get_metadata("gdp-per-capita")
        >>> print(meta['context']['methodology'])
        'GDP per capita is calculated by dividing GDP by population...'
    """
    try:
        config = get_config()
        result = {"dataset_id": dataset_id}
        
        # Try to find in catalog
        catalog = DatasetCatalog(config)
        dataset = catalog.get_dataset(dataset_id)
        
        # Basic info
        if dataset:
            result["basic_info"] = {
                "name": dataset.get('name', dataset_id),
                "source": dataset.get('source', 'unknown'),
                "description": dataset.get('description', ''),
                "file_path": str(dataset.get('file_path', '')),
                "created_at": dataset.get('created_at', ''),
                "last_modified": dataset.get('last_modified', '')
            }
        
        # Load data for schema and stats
        if dataset and dataset.get('file_path'):
            df = pd.read_csv(dataset['file_path'])
        else:
            # Try OWID
            if '-' in dataset_id:
                owid = OWIDSource(config.get_directory('raw'))
                df, metadata = owid.fetch_with_metadata(dataset_id)
                
                if not df.empty:
                    result["basic_info"] = {
                        "name": metadata.get('title', dataset_id),
                        "source": "owid",
                        "description": metadata.get('description', ''),
                        "url": metadata.get('url', '')
                    }
            else:
                return {
                    "status": "error",
                    "error": f"Dataset '{dataset_id}' not found",
                    "dataset_id": dataset_id
                }
        
        if df.empty:
            return {
                "status": "error",
                "error": f"Dataset '{dataset_id}' is empty",
                "dataset_id": dataset_id
            }
        
        # Schema information
        if include_schema:
            schema = []
            for col in df.columns:
                col_info = {
                    "name": col,
                    "type": str(df[col].dtype),
                    "nullable": bool(df[col].isna().any()),
                    "unique_values": int(df[col].nunique()),
                    "sample_values": df[col].dropna().head(3).tolist()
                }
                
                # Add stats for numeric columns
                if pd.api.types.is_numeric_dtype(df[col]):
                    col_info["statistics"] = {
                        "min": float(df[col].min()),
                        "max": float(df[col].max()),
                        "mean": float(df[col].mean()),
                        "std": float(df[col].std())
                    }
                
                schema.append(col_info)
            
            result["schema"] = schema
        
        # Dataset statistics
        stats = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "memory_usage_mb": float(df.memory_usage(deep=True).sum() / 1024 / 1024)
        }
        
        if 'country' in df.columns:
            stats["countries"] = int(df['country'].nunique())
            stats["country_list"] = df['country'].unique().tolist()
        
        if 'year' in df.columns:
            stats["year_range"] = {
                "min": int(df['year'].min()),
                "max": int(df['year'].max())
            }
        
        result["dataset_stats"] = stats
        
        # Context from AI package
        if include_context and dataset and dataset.get('file_path'):
            file_path = Path(dataset['file_path'])
            parent_dir = file_path.parent
            
            # Look for context_owid.md
            context_file = parent_dir / "context_owid.md"
            if context_file.exists():
                with open(context_file, 'r', encoding='utf-8') as f:
                    result["context"] = {"full_text": f.read()}
            
            # Look for prompts.json
            prompts_file = parent_dir / "prompts.json"
            if prompts_file.exists():
                with open(prompts_file, 'r', encoding='utf-8') as f:
                    prompts_data = json.load(f)
                    result["prompts"] = prompts_data.get("suggested_prompts", [])
            
            # Look for schema.json
            schema_file = parent_dir / "schema.json"
            if schema_file.exists():
                with open(schema_file, 'r', encoding='utf-8') as f:
                    schema_data = json.load(f)
                    result["ai_schema"] = schema_data.get("columns", [])
        
        result["status"] = "success"
        return result
        
    except TOOL_OPERATION_ERRORS as e:
        return {
            "status": "error",
            "error": str(e),
            "dataset_id": dataset_id
        }


# ============================================================================
# TOOL 5: Analyze Data
# ============================================================================

async def analyze_data(
    dataset_id: str,
    analysis_type: str = "summary",
    column: Optional[str] = None,
    group_by: Optional[str] = None
) -> Dict[str, Any]:
    """
    Perform automated analysis on a dataset.
    
    This tool provides various analysis types:
    - summary: Descriptive statistics
    - trends: Time series analysis
    - outliers: Anomaly detection
    - correlations: Correlation matrix
    - comparison: Compare groups
    
    Args:
        dataset_id: Dataset identifier
        analysis_type: Type of analysis (summary, trends, outliers, correlations, comparison)
        column: Specific column to analyze (optional)
        group_by: Column to group by (optional, for comparison analysis)
    
    Returns:
        Dictionary with analysis results:
        - analysis_type: Type of analysis performed
        - results: Analysis results (varies by type)
        - insights: AI-generated insights and observations
        - visualizations: Suggested visualizations
    
    Example:
        >>> analysis = await analyze_data("gdp-per-capita", 
        ...                                analysis_type="trends",
        ...                                column="gdp_per_capita")
        >>> print(analysis['insights'])
        ['Brazil shows steady growth from 2010-2023', ...]
    """
    try:
        config = get_config()
        
        # Load dataset
        catalog = DatasetCatalog(config)
        dataset = catalog.get_dataset(dataset_id)
        
        if not dataset or not dataset.get('file_path'):
            return {
                "status": "error",
                "error": f"Dataset '{dataset_id}' not found",
                "dataset_id": dataset_id
            }
        
        df = pd.read_csv(dataset['file_path'])
        
        if df.empty:
            return {
                "status": "error",
                "error": f"Dataset '{dataset_id}' is empty",
                "dataset_id": dataset_id
            }
        
        result = {
            "dataset_id": dataset_id,
            "analysis_type": analysis_type,
            "row_count": len(df)
        }
        
        # Perform analysis based on type
        if analysis_type == "summary":
            # Descriptive statistics
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            
            summary = {}
            for col in numeric_cols[:5]:  # Limit to first 5 numeric columns
                summary[col] = {
                    "count": int(df[col].count()),
                    "mean": float(df[col].mean()),
                    "std": float(df[col].std()),
                    "min": float(df[col].min()),
                    "25%": float(df[col].quantile(0.25)),
                    "median": float(df[col].median()),
                    "75%": float(df[col].quantile(0.75)),
                    "max": float(df[col].max())
                }
            
            result["results"] = summary
            
            # Generate insights
            insights = []
            if summary:
                for col, stats in list(summary.items())[:3]:
                    insights.append(f"{col}: mean={stats['mean']:.2f}, range=[{stats['min']:.2f}, {stats['max']:.2f}]")
            
            result["insights"] = insights
            
        elif analysis_type == "trends":
            # Time series analysis
            if 'year' in df.columns and column and column in df.columns:
                # Group by year
                yearly = df.groupby('year')[column].agg(['mean', 'min', 'max']).reset_index()
                
                trend_data = []
                for _, row in yearly.iterrows():
                    trend_data.append({
                        "year": int(row['year']),
                        "mean": float(row['mean']),
                        "min": float(row['min']),
                        "max": float(row['max'])
                    })
                
                result["results"] = {
                    "column": column,
                    "yearly_data": trend_data,
                    "trend_direction": "increasing" if trend_data[-1]['mean'] > trend_data[0]['mean'] else "decreasing"
                }
                
                # Calculate growth rate
                first_val = trend_data[0]['mean']
                last_val = trend_data[-1]['mean']
                growth_rate = ((last_val - first_val) / first_val) * 100 if first_val != 0 else 0
                
                result["insights"] = [
                    f"Overall trend: {result['results']['trend_direction']}",
                    f"Total growth: {growth_rate:.1f}% from {trend_data[0]['year']} to {trend_data[-1]['year']}"
                ]
            else:
                result["insights"] = ["No 'year' column found for trend analysis"]
                
        elif analysis_type == "outliers":
            # Outlier detection using IQR method
            if column and column in df.columns and pd.api.types.is_numeric_dtype(df[column]):
                Q1 = df[column].quantile(0.25)
                Q3 = df[column].quantile(0.75)
                IQR = Q3 - Q1
                
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outliers = df[(df[column] < lower_bound) | (df[column] > upper_bound)]
                
                result["results"] = {
                    "column": column,
                    "outlier_count": len(outliers),
                    "outlier_percentage": float(len(outliers) / len(df) * 100),
                    "bounds": {
                        "lower": float(lower_bound),
                        "upper": float(upper_bound)
                    },
                    "outlier_examples": outliers.head(5).to_dict(orient='records') if not outliers.empty else []
                }
                
                result["insights"] = [
                    f"Found {len(outliers)} outliers ({result['results']['outlier_percentage']:.1f}% of data)",
                    f"Outliers are values outside [{lower_bound:.2f}, {upper_bound:.2f}]"
                ]
            else:
                result["insights"] = ["No valid numeric column specified for outlier detection"]
                
        elif analysis_type == "correlations":
            # Correlation analysis
            numeric_cols = df.select_dtypes(include=['number']).columns
            
            if len(numeric_cols) >= 2:
                corr_matrix = df[numeric_cols].corr()
                
                # Find strongest correlations
                correlations = []
                for i in range(len(numeric_cols)):
                    for j in range(i+1, len(numeric_cols)):
                        corr_val = corr_matrix.iloc[i, j]
                        correlations.append({
                            "column1": numeric_cols[i],
                            "column2": numeric_cols[j],
                            "correlation": float(corr_val),
                            "strength": "strong" if abs(corr_val) > 0.7 else "moderate" if abs(corr_val) > 0.4 else "weak"
                        })
                
                # Sort by absolute correlation
                correlations.sort(key=lambda x: abs(x['correlation']), reverse=True)
                
                result["results"] = {
                    "correlations": correlations[:10],  # Top 10
                    "correlation_matrix": corr_matrix.to_dict()
                }
                
                # Insights
                if correlations:
                    top = correlations[0]
                    result["insights"] = [
                        f"Strongest correlation: {top['column1']} vs {top['column2']} (r={top['correlation']:.2f})",
                        f"Relationship is {top['strength']} and {'positive' if top['correlation'] > 0 else 'negative'}"
                    ]
            else:
                result["insights"] = ["Need at least 2 numeric columns for correlation analysis"]
        
        # Suggested visualizations
        result["visualizations"] = {
            "summary": ["histogram", "box_plot"],
            "trends": ["line_chart", "area_chart"],
            "outliers": ["scatter_plot", "box_plot"],
            "correlations": ["heatmap", "scatter_matrix"]
        }.get(analysis_type, ["bar_chart"])
        
        result["status"] = "success"
        return result
        
    except TOOL_OPERATION_ERRORS as e:
        return {
            "status": "error",
            "error": str(e),
            "dataset_id": dataset_id,
            "analysis_type": analysis_type
        }


# ============================================================================
# TOOL 6: Recommend Related Datasets
# ============================================================================

async def recommend_datasets(
    dataset_id: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 5
) -> Dict[str, Any]:
    """
    Recommend related datasets using semantic similarity.
    
    This tool suggests datasets that are:
    - Semantically similar (same or related topics)
    - From different sources (for cross-validation)
    - Covering similar time periods or geographies
    - Complementary for analysis
    
    Args:
        dataset_id: ID of dataset to find similar datasets for (optional)
        query: Text query to find relevant datasets (optional)
        limit: Maximum number of recommendations (default 5)
    
    Returns:
        Dictionary with:
        - status: "success" or "error"
        - recommendations: List of recommended datasets with similarity scores
        - total_found: Number of recommendations
        - query_info: Information about what was searched
    
    Example:
        >>> result = await recommend_datasets(query="salarios reales")
        >>> for rec in result['recommendations']:
        ...     print(f"{rec['name']}: {rec['similarity']:.2f} - {rec['match_reasons']}")
    """
    try:
        config = get_config()
        
        # Import recommender
        from src.recommender import DatasetRecommender
        recommender = DatasetRecommender(config)
        
        # Get recommendations
        recommendations = await recommender.get_recommendations(
            dataset_id=dataset_id,
            query=query,
            limit=limit
        )
        
        return {
            "status": "success",
            "recommendations": recommendations,
            "total_found": len(recommendations),
            "query_info": {
                "dataset_id": dataset_id,
                "query": query,
                "limit": limit
            }
        }
        
    except TOOL_OPERATION_ERRORS as e:
        return {
            "status": "error",
            "error": str(e),
            "recommendations": [],
            "total_found": 0
        }


# ============================================================================
# TOOL 7: Semantic Search Datasets (vector store)
# ============================================================================

async def semantic_search_datasets(
    query: str,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Search for datasets by semantic similarity (vector search over catalog metadata).

    Use this when the user asks for datasets "like X" or "related to Y" or
    when keyword search might miss relevant indicators. Requires RAG index
    to be built (curate rag-index) and rag.enabled in config.

    Args:
        query: Natural language description of desired data (e.g. "real wages", "inflation")
        limit: Maximum number of results (default 10)

    Returns:
        Dictionary with datasets (from local catalog), total_found, query, status.
    """
    try:
        config = get_config()
        rag_cfg = config.get_rag_config()
        try:
            from src.embeddings import get_embedding_provider
            from src.vector_store import VectorStore
            provider = get_embedding_provider(
                rag_cfg.get("embedding_provider", "openai"),
                model=rag_cfg.get("embedding_model"),
                base_url=rag_cfg.get("embedding_base_url"),
            )
            store = VectorStore(rag_cfg["chroma_persist_dir"])
        except TOOL_OPERATION_ERRORS as e:
            return {
                "status": "error",
                "error": f"RAG/vector store not available: {e}",
                "query": query,
                "datasets": [],
                "total_found": 0,
            }
        embedding = provider.embed(query)
        hits = store.search(
            embedding,
            top_k=limit,
            filter_metadata={"type": "catalog"},
        )
        catalog = DatasetCatalog(config)
        datasets_out = []
        seen_ids = set()
        for h in hits:
            meta = h.get("metadata") or {}
            did = meta.get("dataset_id")
            if did is None or did in seen_ids:
                continue
            seen_ids.add(did)
            ds = catalog.get_dataset(int(did))
            if not ds:
                continue
            name = ds.get("indicator_name") or ds.get("name", "")
            datasets_out.append({
                "id": ds.get("id", ""),
                "name": name,
                "source": ds.get("source", ""),
                "description": ds.get("description", ""),
                "type": "local",
                "file_path": str(ds.get("file_path", "")),
                "row_count": ds.get("row_count", 0),
                "similarity_distance": h.get("distance"),
            })
        return {
            "status": "success",
            "query": query,
            "datasets": datasets_out,
            "total_found": len(datasets_out),
        }
    except TOOL_OPERATION_ERRORS as e:
        return {
            "status": "error",
            "error": str(e),
            "query": query,
            "datasets": [],
            "total_found": 0,
        }

# ============================================================================
# TOOL 8: Run SQL Query (sampled)
# ============================================================================

async def run_sql_query(
    dataset_id: int,
    sql: str,
    limit: int = SQL_PREVIEW_LIMIT,
) -> Dict[str, Any]:
    """
    Run a SQL query against a sampled dataset table.

    Args:
        dataset_id: Catalog dataset ID
        sql: SQL SELECT query (table name is 'dataset')
        limit: Max rows to return (default 200)

    Returns:
        Dictionary with columns, rows, and executed query.
    """
    try:
        config = get_config()
        catalog = DatasetCatalog(config)
        dataset = catalog.get_dataset(int(dataset_id))
        if not dataset:
            return {"status": "error", "error": "Dataset not found", "dataset_id": dataset_id}

        db_path = get_smoothcsv_db_path(config.data_root)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            table_name = ensure_smoothcsv_table(conn, dataset, SQL_SAMPLE_LIMIT)
            cursor = conn.cursor()
            cursor.execute("DROP VIEW IF EXISTS dataset")
            cursor.execute(f'CREATE TEMP VIEW dataset AS SELECT * FROM "{table_name}"')

            query_sql = prepare_smoothcsv_sql(sql, int(limit))
            cursor.execute(query_sql)
            rows = cursor.fetchall()
            columns = [col[0] for col in cursor.description] if cursor.description else []
            values = [list(row) for row in rows]
            return {
                "status": "success",
                "columns": columns,
                "rows": values,
                "table_name": table_name,
                "sample_limit": SQL_SAMPLE_LIMIT,
                "query": query_sql,
            }
        finally:
            conn.close()
    except (ValueError, FileNotFoundError) as exc:
        return {"status": "error", "error": str(exc), "dataset_id": dataset_id}
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}


# ============================================================================
# TOOL 9: Fork Dataset
# ============================================================================

async def fork_dataset(
    dataset_id: int,
    new_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a fork of a dataset and mark it as edited.

    Args:
        dataset_id: Catalog dataset ID
        new_name: Optional filename base for the fork

    Returns:
        Dictionary with new dataset info.
    """
    try:
        config = get_config()
        catalog = DatasetCatalog(config)
        dataset = catalog.get_dataset(int(dataset_id))
        if not dataset:
            return {"status": "error", "error": "Dataset not found", "dataset_id": dataset_id}

        source_path = Path(dataset["file_path"])
        if not source_path.exists():
            return {"status": "error", "error": "Dataset file not found", "dataset_id": dataset_id}

        fork_name = (new_name or "").strip()
        safe_base = fork_name or f"{source_path.stem}_edited"
        safe_base = "".join(c if c.isalnum() or c in "-_" else "_" for c in safe_base).strip("_")
        if not safe_base:
            safe_base = f"dataset_{dataset_id}_edited"

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        dest_name = f"{safe_base}_{timestamp}.csv"
        dest_path = source_path.parent / dest_name

        shutil.copyfile(source_path, dest_path)
        new_id = catalog.index_dataset(
            dest_path,
            display_file_name=dest_name,
            force=True,
        )
        if not new_id:
            return {"status": "error", "error": "Failed to index forked dataset", "dataset_id": dataset_id}

        conn = sqlite3.connect(catalog.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE datasets SET is_edited = 1 WHERE id = ?", (new_id,))
            conn.commit()
        finally:
            conn.close()

        return {
            "status": "success",
            "dataset": {
                "id": new_id,
                "file_name": dest_name,
                "file_path": str(dest_path),
                "is_edited": True,
            },
        }
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}


# ============================================================================
# TOOL 10: Get Dataset Versions
# ============================================================================

async def get_dataset_versions(
    identifier: str,
    source: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return all dataset versions for a given identifier (indicator_id or indicator_name).
    """
    try:
        config = get_config()
        catalog = DatasetCatalog(config)
        versions = catalog.get_versions_for_identifier(identifier, source=source or None)
        formatted = []
        for v in versions:
            formatted.append({
                "id": v.get("id"),
                "file_name": v.get("file_name"),
                "indicator_id": v.get("indicator_id"),
                "indicator_name": v.get("indicator_name"),
                "source": v.get("source"),
                "indexed_at": v.get("indexed_at"),
                "row_count": v.get("row_count"),
                "column_count": v.get("column_count"),
                "is_edited": bool(v.get("is_edited")),
            })
        return {
            "status": "success",
            "identifier": identifier,
            "source": source,
            "total": len(formatted),
            "versions": formatted,
        }
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e), "identifier": identifier}


# ============================================================================
# TOOL 11: Get Dataset Statistics (catalog-only)
# ============================================================================

async def get_dataset_statistics(
    dataset_id: int,
) -> Dict[str, Any]:
    """
    Return catalog statistics for a dataset without loading the full file.
    """
    try:
        config = get_config()
        catalog = DatasetCatalog(config)
        dataset = catalog.get_dataset(int(dataset_id))
        if not dataset:
            return {"status": "error", "error": "Dataset not found", "dataset_id": dataset_id}

        file_size_bytes = dataset.get("file_size_bytes") or 0
        return {
            "status": "success",
            "dataset_id": dataset_id,
            "name": dataset.get("indicator_name") or dataset.get("file_name"),
            "source": dataset.get("source"),
            "topic": dataset.get("topic"),
            "row_count": dataset.get("row_count"),
            "column_count": dataset.get("column_count"),
            "min_year": dataset.get("min_year"),
            "max_year": dataset.get("max_year"),
            "country_count": dataset.get("country_count"),
            "file_size_bytes": file_size_bytes,
            "file_size_mb": file_size_bytes / (1024 * 1024) if file_size_bytes else 0,
            "completeness_score": dataset.get("completeness_score"),
            "null_percentage": dataset.get("null_percentage"),
            "is_edited": bool(dataset.get("is_edited")),
            "indexed_at": dataset.get("indexed_at"),
        }
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}


# ============================================================================
# TOOL 12: Export Preview CSV
# ============================================================================

async def export_preview_csv(
    dataset_id: int,
    limit: int = 200,
) -> Dict[str, Any]:
    """
    Export a CSV preview (first N rows) for sharing.
    """
    try:
        config = get_config()
        catalog = DatasetCatalog(config)
        df = catalog.get_preview_data(int(dataset_id), limit=min(int(limit), 1000))
        if df is None:
            return {"status": "error", "error": "Dataset not found", "dataset_id": dataset_id}

        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        return {
            "status": "success",
            "dataset_id": dataset_id,
            "row_count": len(df),
            "columns": list(df.columns),
            "csv": buffer.getvalue(),
        }
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e), "dataset_id": dataset_id}


# ============================================================================
# TOOL 13: List Datasets With Filters
# ============================================================================

async def list_datasets_with_filters(
    query: str = "",
    source: Optional[str] = None,
    topic: Optional[str] = None,
    edited_only: bool = False,
    latest_only: bool = False,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    List datasets with optional filters (source/topic/edited/latest).
    """
    try:
        config = get_config()
        catalog = DatasetCatalog(config)
        filters = {}
        if source:
            filters["source"] = source
        if topic:
            filters["topic"] = topic

        fetch_limit = max(int(limit) * 5, int(limit))
        datasets = catalog.search(query=query or "", filters=filters or None, limit=fetch_limit)

        if edited_only:
            datasets = [ds for ds in datasets if ds.get("is_edited")]

        if latest_only:
            seen = set()
            latest = []
            for ds in datasets:
                gid = ds.get("indicator_id") or ds.get("indicator_name")
                if not gid or gid in seen:
                    continue
                seen.add(gid)
                latest.append(ds)
            datasets = latest

        datasets = datasets[: int(limit)]
        formatted = []
        for ds in datasets:
            formatted.append({
                "id": ds.get("id"),
                "name": ds.get("indicator_name") or ds.get("file_name"),
                "source": ds.get("source"),
                "topic": ds.get("topic"),
                "row_count": ds.get("row_count"),
                "column_count": ds.get("column_count"),
                "file_name": ds.get("file_name"),
                "is_edited": bool(ds.get("is_edited")),
                "indexed_at": ds.get("indexed_at"),
            })
        return {
            "status": "success",
            "query": query,
            "filters": {
                "source": source,
                "topic": topic,
                "edited_only": edited_only,
                "latest_only": latest_only,
            },
            "datasets": formatted,
            "total_found": len(formatted),
        }
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e), "datasets": []}


# ============================================================================
# TOOL 14: List Available Tools
# ============================================================================

async def list_available_tools(
    include_parameters: bool = False,
) -> Dict[str, Any]:
    """
    List available MCP tools and their descriptions.
    """
    tools_out = []
    for name, info in TOOL_REGISTRY.items():
        entry = {
            "name": name,
            "description": info.get("description", ""),
        }
        if include_parameters:
            entry["parameters"] = info.get("parameters", {})
        tools_out.append(entry)
    return {
        "status": "success",
        "total": len(tools_out),
        "tools": tools_out,
    }

# ============================================================================
# TOOL REGISTRY
# ============================================================================

# Registry of all available tools
TOOL_REGISTRY = {
    "search_datasets": {
        "function": search_datasets,
        "description": "Search for datasets in the catalog by query, source, or topic",
        "parameters": {
            "query": {"type": "string", "required": True, "description": "Search terms"},
            "source": {"type": "string", "required": False, "description": "Filter by source (owid, worldbank, etc.)"},
            "topic": {"type": "string", "required": False, "description": "Filter by topic"},
            "limit": {"type": "integer", "required": False, "description": "Max results to return"}
        }
    },
    "list_local_datasets": {
        "function": list_local_datasets,
        "description": "List the user's local datasets (cataloged). Call this FIRST when the user asks to 'review my datasets' or 'propose analyses crossing multiple datasets' so you know what they have; then propose concrete analyses using the returned ids with preview_data/analyze_data.",
        "parameters": {
            "topic": {"type": "string", "required": False, "description": "Filter by topic"},
            "source": {"type": "string", "required": False, "description": "Filter by source"},
            "limit": {"type": "integer", "required": False, "description": "Max datasets to return (default 50)"},
            "include_uncataloged": {"type": "boolean", "required": False, "description": "Include CSV files not yet in catalog (default true)"}
        }
    },
    "country_harmonizer": {
        "function": country_harmonizer,
        "description": "Normalize dataset entity/country values to ISO3 and classify non-country aggregates.",
        "parameters": {
            "dataset_id": {"type": "integer", "required": True, "description": "Catalog dataset ID"},
            "entity_column": {"type": "string", "required": False, "description": "Optional explicit entity column name"},
            "exclude_non_country": {"type": "boolean", "required": False, "description": "Exclude non-country aggregates"},
            "persist": {"type": "boolean", "required": False, "description": "Persist harmonized output as a new catalog dataset"},
            "new_name": {"type": "string", "required": False, "description": "Optional base name for persisted dataset"},
        },
    },
    "coverage_analyzer": {
        "function": coverage_analyzer,
        "description": "Analyze country-year overlap coverage across multiple datasets.",
        "parameters": {
            "dataset_ids": {"type": "array", "required": True, "description": "List of catalog dataset IDs"},
            "period_start": {"type": "integer", "required": False, "description": "Optional start year"},
            "period_end": {"type": "integer", "required": False, "description": "Optional end year"},
            "countries_only": {"type": "boolean", "required": False, "description": "Keep only rows mapped to countries"},
        },
    },
    "panel_builder": {
        "function": panel_builder,
        "description": "Build a merged panel across datasets using entity-year keys, with optional lags and persistence.",
        "parameters": {
            "dataset_ids": {"type": "array", "required": True, "description": "List of catalog dataset IDs (min 2)"},
            "join_type": {"type": "string", "required": False, "description": "Join type: inner|outer"},
            "period_start": {"type": "integer", "required": False, "description": "Optional start year"},
            "period_end": {"type": "integer", "required": False, "description": "Optional end year"},
            "countries_only": {"type": "boolean", "required": False, "description": "Keep only country entities"},
            "lags": {"type": "object", "required": False, "description": "Dataset lag mapping, e.g. {'42': 5}"},
            "value_columns": {"type": "object", "required": False, "description": "Dataset value column mapping, e.g. {'42': 'aid'}"},
            "persist": {"type": "boolean", "required": False, "description": "Persist resulting panel as a new dataset"},
            "panel_name": {"type": "string", "required": False, "description": "Optional name prefix for persisted panel"},
        },
    },
    "economic_transformer": {
        "function": economic_transformer,
        "description": "Apply economic transformations (lag, growth_rate, log, moving_avg, first_diff, zscore, min_max).",
        "parameters": {
            "dataset_id": {"type": "integer", "required": True, "description": "Catalog dataset ID"},
            "column": {"type": "string", "required": False, "description": "Target value column (auto-detected if omitted)"},
            "transformations": {"type": "array", "required": False, "description": "List of transformation objects"},
            "output_mode": {"type": "string", "required": False, "description": "add_columns or replace"},
            "persist": {"type": "boolean", "required": False, "description": "Persist transformed dataset"},
            "new_name": {"type": "string", "required": False, "description": "Optional base name for persisted dataset"},
        },
    },
    "missing_data_handler": {
        "function": missing_data_handler,
        "description": "Handle missing values with explicit strategy and imputation tracking.",
        "parameters": {
            "dataset_id": {"type": "integer", "required": True, "description": "Catalog dataset ID"},
            "strategy": {"type": "string", "required": False, "description": "linear|forward_fill|backward_fill|drop|regional_mean"},
            "columns": {"type": "array", "required": False, "description": "Optional numeric columns to process"},
            "max_gap": {"type": "integer", "required": False, "description": "Max consecutive gaps to impute"},
            "scope": {"type": "string", "required": False, "description": "within_entity or global"},
            "persist": {"type": "boolean", "required": False, "description": "Persist handled dataset"},
            "new_name": {"type": "string", "required": False, "description": "Optional base name for persisted dataset"},
        },
    },
    "data_profiler": {
        "function": data_profiler,
        "description": "Profile data quality, missingness, and panel readiness diagnostics.",
        "parameters": {
            "dataset_id": {"type": "integer", "required": True, "description": "Catalog dataset ID"},
            "by_country": {"type": "boolean", "required": False, "description": "Include country/entity profile sample"},
            "by_year": {"type": "boolean", "required": False, "description": "Include year profile sample"},
            "by_column": {"type": "boolean", "required": False, "description": "Include per-column quality profile"},
        },
    },
    "run_python_analysis": {
        "function": run_python_analysis,
        "description": "Run restricted Python analysis code over one or more local datasets (phase 3 foundation).",
        "parameters": {
            "dataset_ids": {"type": "array", "required": True, "description": "List of catalog dataset IDs"},
            "python_code": {"type": "string", "required": True, "description": "Python code using df/dfs and optionally setting result/result_df"},
            "preview_rows": {"type": "integer", "required": False, "description": "Rows to return from result_df preview (default 25)"},
        },
    },
    "correlation_analyzer": {
        "function": correlation_analyzer,
        "description": "Compute pooled/within/rolling correlations with interpretation and top correlated pairs.",
        "parameters": {
            "dataset_id": {"type": "integer", "required": True, "description": "Catalog dataset ID"},
            "columns": {"type": "array", "required": False, "description": "Numeric columns to correlate (auto-detected if omitted)"},
            "method": {"type": "string", "required": False, "description": "Correlation method: pooled|within|rolling"},
            "entity_column": {"type": "string", "required": False, "description": "Entity column for within/rolling"},
            "year_column": {"type": "string", "required": False, "description": "Year column for rolling"},
            "window": {"type": "integer", "required": False, "description": "Rolling window size (rolling method)"},
            "min_periods": {"type": "integer", "required": False, "description": "Minimum periods in rolling window"},
            "top_n": {"type": "integer", "required": False, "description": "Top correlated pairs to return"},
        },
    },
    "group_classifier": {
        "function": group_classifier,
        "description": "Classify entities by region/income/OECD/population bands and return grouped coverage summary.",
        "parameters": {
            "dataset_id": {"type": "integer", "required": True, "description": "Catalog dataset ID"},
            "group_by": {"type": "string", "required": False, "description": "region|income|oecd|population_band"},
            "entity_column": {"type": "string", "required": False, "description": "Optional entity column override"},
            "value_column": {"type": "string", "required": False, "description": "Optional numeric column for mean_value summary"},
            "income_column": {"type": "string", "required": False, "description": "Metadata column for income grouping"},
            "region_column": {"type": "string", "required": False, "description": "Metadata column for region grouping"},
            "oecd_column": {"type": "string", "required": False, "description": "Metadata column for OECD grouping"},
            "population_column": {"type": "string", "required": False, "description": "Metadata column for population band grouping"},
        },
    },
    "regression_engine": {
        "function": regression_engine,
        "description": "Estimate pooled OLS or basic fixed-effects regressions (entity/two-way).",
        "parameters": {
            "dataset_id": {"type": "integer", "required": True, "description": "Catalog dataset ID"},
            "dependent": {"type": "string", "required": True, "description": "Dependent variable column"},
            "independents": {"type": "array", "required": True, "description": "Independent variable columns"},
            "model": {"type": "string", "required": False, "description": "pooled|fe_entity|fe_two_way"},
            "entity_column": {"type": "string", "required": False, "description": "Entity column for FE models"},
            "year_column": {"type": "string", "required": False, "description": "Year column for two-way FE"},
        },
    },
    "smart_visualizer": {
        "function": smart_visualizer,
        "description": "Generate reproducible Vega-Lite specs for line/scatter/heatmap charts.",
        "parameters": {
            "dataset_id": {"type": "integer", "required": True, "description": "Catalog dataset ID"},
            "chart_type": {"type": "string", "required": False, "description": "line|scatter|heatmap"},
            "x": {"type": "string", "required": False, "description": "X axis field"},
            "y": {"type": "string", "required": False, "description": "Y axis field"},
            "color": {"type": "string", "required": False, "description": "Color/value field"},
            "top_n": {"type": "integer", "required": False, "description": "Max rows to include in chart data (default 50)"},
        },
    },
    "analysis_planner": {
        "function": analysis_planner,
        "description": "Create a tool-aware analysis execution plan from an objective and optional dataset IDs.",
        "parameters": {
            "objective": {"type": "string", "required": True, "description": "Analysis goal in natural language"},
            "dataset_ids": {"type": "array", "required": False, "description": "Optional list of catalog dataset IDs"},
            "include_visualization": {"type": "boolean", "required": False, "description": "Include visualization step (default true)"},
            "include_robustness": {"type": "boolean", "required": False, "description": "Include robustness step (default false)"},
        },
    },
    "caveat_engine": {
        "function": caveat_engine,
        "description": "Generate automatic caveats about sample size, missingness, imputation, concentration, and time span.",
        "parameters": {
            "dataset_id": {"type": "integer", "required": True, "description": "Catalog dataset ID"},
            "value_columns": {"type": "array", "required": False, "description": "Optional numeric columns to evaluate"},
            "sample_threshold": {"type": "integer", "required": False, "description": "Small-sample threshold (default 30)"},
            "missing_threshold": {"type": "number", "required": False, "description": "Missingness threshold (default 0.30)"},
            "concentration_threshold": {"type": "number", "required": False, "description": "Top-entity concentration threshold (default 0.60)"},
            "imputation_threshold": {"type": "number", "required": False, "description": "Imputation ratio threshold (default 0.20)"},
        },
    },
    "robustness_checker": {
        "function": robustness_checker,
        "description": "Check key coefficient stability across pooled/entity FE/two-way FE specifications.",
        "parameters": {
            "dataset_id": {"type": "integer", "required": True, "description": "Catalog dataset ID"},
            "dependent": {"type": "string", "required": True, "description": "Dependent variable column"},
            "independents": {"type": "array", "required": True, "description": "Independent variable columns"},
            "key_variable": {"type": "string", "required": False, "description": "Coefficient to track for robustness"},
            "models": {"type": "array", "required": False, "description": "Model list from pooled|fe_entity|fe_two_way"},
        },
    },
    "cross_source_validator": {
        "function": cross_source_validator,
        "description": "Compare overlapping entity-year observations across datasets/sources for consistency checks.",
        "parameters": {
            "dataset_ids": {"type": "array", "required": True, "description": "At least 2 catalog dataset IDs"},
            "value_column": {"type": "string", "required": False, "description": "Optional common value column override"},
            "min_overlap": {"type": "integer", "required": False, "description": "Warn when overlap is below this threshold (default 20)"},
        },
    },
    "assumption_checker": {
        "function": assumption_checker,
        "description": "Check regression assumptions with lightweight diagnostics (sample size, collinearity, residual proxies).",
        "parameters": {
            "dataset_id": {"type": "integer", "required": True, "description": "Catalog dataset ID"},
            "dependent": {"type": "string", "required": True, "description": "Dependent variable column"},
            "independents": {"type": "array", "required": True, "description": "Independent variable columns"},
        },
    },
    "trend_analyzer": {
        "function": trend_analyzer,
        "description": "Analyze trend direction and change rates overall and by entity.",
        "parameters": {
            "dataset_id": {"type": "integer", "required": True, "description": "Catalog dataset ID"},
            "value_column": {"type": "string", "required": False, "description": "Optional numeric value column override"},
            "entity_column": {"type": "string", "required": False, "description": "Optional entity column override"},
            "year_column": {"type": "string", "required": False, "description": "Optional year column override"},
            "min_points": {"type": "integer", "required": False, "description": "Minimum yearly points per entity (default 5)"},
            "top_entities": {"type": "integer", "required": False, "description": "Max entity trends to return (default 10)"},
        },
    },
    "causality_tester": {
        "function": causality_tester,
        "description": "Run lead-lag and placebo checks to assess directional temporal precedence.",
        "parameters": {
            "dataset_id": {"type": "integer", "required": True, "description": "Catalog dataset ID"},
            "dependent": {"type": "string", "required": True, "description": "Outcome variable column"},
            "driver": {"type": "string", "required": True, "description": "Potential driver variable column"},
            "entity_column": {"type": "string", "required": False, "description": "Optional entity column override"},
            "year_column": {"type": "string", "required": False, "description": "Optional year column override"},
            "max_lag": {"type": "integer", "required": False, "description": "Maximum lag to test (default 3)"},
            "min_points": {"type": "integer", "required": False, "description": "Minimum valid observations required (default 20)"},
        },
    },
    "dimensionality_reducer": {
        "function": dimensionality_reducer,
        "description": "Reduce correlated numeric variables with PCA-style components.",
        "parameters": {
            "dataset_id": {"type": "integer", "required": True, "description": "Catalog dataset ID"},
            "columns": {"type": "array", "required": False, "description": "Optional numeric columns for reduction"},
            "n_components": {"type": "integer", "required": False, "description": "Number of components to return (default 2)"},
        },
    },
    "convergence_analyzer": {
        "function": convergence_analyzer,
        "description": "Estimate beta and sigma convergence diagnostics over a selected period.",
        "parameters": {
            "dataset_id": {"type": "integer", "required": True, "description": "Catalog dataset ID"},
            "value_column": {"type": "string", "required": False, "description": "Optional numeric value column override"},
            "entity_column": {"type": "string", "required": False, "description": "Optional entity column override"},
            "year_column": {"type": "string", "required": False, "description": "Optional year column override"},
            "start_year": {"type": "integer", "required": False, "description": "Optional period start year"},
            "end_year": {"type": "integer", "required": False, "description": "Optional period end year"},
        },
    },
    "preview_data": {
        "function": preview_data,
        "description": "Preview a dataset by showing the first N rows with statistics",
        "parameters": {
            "dataset_id": {"type": "string", "required": True, "description": "Dataset identifier"},
            "limit": {"type": "integer", "required": False, "description": "Number of rows to preview"},
            "include_stats": {"type": "boolean", "required": False, "description": "Include statistics"}
        }
    },
    "download_owid": {
        "function": download_owid,
        "description": "Download data from Our World in Data (OWID) using a grapher slug",
        "parameters": {
            "slug": {"type": "string", "required": True, "description": "OWID grapher slug"},
            "countries": {"type": "array", "required": False, "description": "List of countries to filter"},
            "start_year": {"type": "integer", "required": False, "description": "Start year"},
            "end_year": {"type": "integer", "required": False, "description": "End year"},
            "create_ai_package": {"type": "boolean", "required": False, "description": "Create AI package with metadata"}
        }
    },
    "get_metadata": {
        "function": get_metadata,
        "description": "Get comprehensive metadata for a dataset including schema and context",
        "parameters": {
            "dataset_id": {"type": "string", "required": True, "description": "Dataset identifier"},
            "include_schema": {"type": "boolean", "required": False, "description": "Include data schema"},
            "include_context": {"type": "boolean", "required": False, "description": "Include OWID context"}
        }
    },
    "analyze_data": {
        "function": analyze_data,
        "description": "Perform automated analysis (summary, trends, outliers, correlations)",
        "parameters": {
            "dataset_id": {"type": "string", "required": True, "description": "Dataset identifier"},
            "analysis_type": {"type": "string", "required": True, "description": "Type of analysis"},
            "column": {"type": "string", "required": False, "description": "Column to analyze"},
            "group_by": {"type": "string", "required": False, "description": "Column to group by"}
        }
    },
    "recommend_datasets": {
        "function": recommend_datasets,
        "description": "Recommend related datasets using semantic similarity",
        "parameters": {
            "dataset_id": {"type": "string", "required": False, "description": "Dataset ID to find similar datasets for"},
            "query": {"type": "string", "required": False, "description": "Text query to find relevant datasets"},
            "limit": {"type": "integer", "required": False, "description": "Maximum number of recommendations"}
        }
    },
    "semantic_search_datasets": {
        "function": semantic_search_datasets,
        "description": "Search datasets by semantic similarity (vector search). Use for 'datasets like X' or related topics.",
        "parameters": {
            "query": {"type": "string", "required": True, "description": "Natural language description of desired data"},
            "limit": {"type": "integer", "required": False, "description": "Max results (default 10)"}
        }
    },
    "run_sql_query": {
        "function": run_sql_query,
        "description": "Run a SQL SELECT query against a sampled dataset table (table name is 'dataset').",
        "parameters": {
            "dataset_id": {"type": "integer", "required": True, "description": "Catalog dataset ID"},
            "sql": {"type": "string", "required": True, "description": "SQL SELECT query"},
            "limit": {"type": "integer", "required": False, "description": "Max rows to return (default 200)"}
        }
    },
    "fork_dataset": {
        "function": fork_dataset,
        "description": "Create a forked dataset marked as edited.",
        "parameters": {
            "dataset_id": {"type": "integer", "required": True, "description": "Catalog dataset ID"},
            "new_name": {"type": "string", "required": False, "description": "Optional filename base for the fork"}
        }
    },
    "get_dataset_versions": {
        "function": get_dataset_versions,
        "description": "List all versions for an identifier (indicator_id or indicator_name).",
        "parameters": {
            "identifier": {"type": "string", "required": True, "description": "Indicator id or indicator name"},
            "source": {"type": "string", "required": False, "description": "Optional source filter"}
        }
    },
    "get_dataset_statistics": {
        "function": get_dataset_statistics,
        "description": "Get catalog statistics for a dataset without loading the full file.",
        "parameters": {
            "dataset_id": {"type": "integer", "required": True, "description": "Catalog dataset ID"}
        }
    },
    "export_preview_csv": {
        "function": export_preview_csv,
        "description": "Export a CSV preview (first N rows) for a dataset.",
        "parameters": {
            "dataset_id": {"type": "integer", "required": True, "description": "Catalog dataset ID"},
            "limit": {"type": "integer", "required": False, "description": "Preview row limit (default 200)"}
        }
    },
    "list_datasets_with_filters": {
        "function": list_datasets_with_filters,
        "description": "List datasets with filters (source/topic/edited/latest).",
        "parameters": {
            "query": {"type": "string", "required": False, "description": "Search query"},
            "source": {"type": "string", "required": False, "description": "Filter by source"},
            "topic": {"type": "string", "required": False, "description": "Filter by topic"},
            "edited_only": {"type": "boolean", "required": False, "description": "Only edited datasets"},
            "latest_only": {"type": "boolean", "required": False, "description": "Only latest version per identifier"},
            "limit": {"type": "integer", "required": False, "description": "Max results (default 50)"}
        }
    },
    "list_available_tools": {
        "function": list_available_tools,
        "description": "List available MCP tools and their descriptions.",
        "parameters": {
            "include_parameters": {"type": "boolean", "required": False, "description": "Include parameter schema"}
        }
    }
}


def get_tool(name: str) -> Optional[Dict[str, Any]]:
    """
    Get a tool from the registry by name.
    
    Args:
        name: Tool name
        
    Returns:
        Tool definition or None if not found
    """
    return TOOL_REGISTRY.get(name)


def list_tools() -> List[str]:
    """
    List all available tool names.
    
    Returns:
        List of tool names
    """
    return list(TOOL_REGISTRY.keys())


async def execute_tool(name: str, **kwargs) -> Dict[str, Any]:
    """
    Execute a tool by name with the given parameters.
    
    Args:
        name: Tool name
        **kwargs: Tool parameters
        
    Returns:
        Tool execution result
    """
    tool = get_tool(name)
    if not tool:
        return {"status": "error", "error": f"Tool '{name}' not found"}
    
    try:
        function = tool["function"]
        return await function(**kwargs)
    except TOOL_OPERATION_ERRORS as e:
        return {"status": "error", "error": str(e), "tool": name}


# For testing
if __name__ == "__main__":
    import asyncio
    
    async def test_tools():
        print("🧪 Testing MCP Tools")
        print("=" * 50)
        
        # Test search
        print("\n1. Testing search_datasets...")
        results = await search_datasets("GDP", limit=3)
        print(f"   Status: {results['status']}")
        print(f"   Found: {results.get('total_found', 0)} datasets")
        
        # List tools
        print("\n2. Available tools:")
        for tool_name in list_tools():
            tool = get_tool(tool_name)
            print(f"   - {tool_name}: {tool['description'][:50]}...")
        
        print("\n✅ Tools module loaded successfully!")
    
    asyncio.run(test_tools())

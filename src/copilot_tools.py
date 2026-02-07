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
import json
import os
import re
import shutil
import sqlite3
from typing import Dict, List, Optional, Any
from pathlib import Path
import pandas as pd
from datetime import datetime

from src.config import Config
from src.searcher import IndicatorSearcher
from src.ingestion import DataIngestionManager, OWIDSource
from src.dataset_catalog import DatasetCatalog


# Initialize configuration (singleton pattern)
_config = None
def get_config():
    """Get or create Config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


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
        
    except Exception as e:
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
        cataloged = []
        for ds in datasets:
            name = ds.get("indicator_name") or ds.get("name") or ds.get("file_name", "")
            cataloged.append({
                "id": ds.get("id"),
                "name": name,
                "source": ds.get("source", ""),
                "topic": ds.get("topic", ""),
                "row_count": ds.get("row_count", 0),
                "columns": (ds.get("columns") or [])[:10],
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
            "total_cataloged": len(cataloged),
            "uncataloged_files": uncataloged_files[:20],
            "hint": "Use cataloged[].id with preview_data, get_metadata, or analyze_data. If uncataloged_files is not empty, suggest running 'curate index' to add them to the catalog.",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "cataloged": [],
            "total_cataloged": 0,
            "uncataloged_files": [],
        }


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
        
    except Exception as e:
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
        output_path = cleaner.save_clean_dataset(
            data=df_clean,
            topic=topic,
            source="owid",
            coverage="latam",  # Could be inferred from countries
            start_year=start_year,
            end_year=end_year,
            identifier=identifier
        )
        
        result = {
            "status": "success",
            "slug": slug,
            "file_path": str(output_path),
            "row_count": len(df_clean),
            "column_count": len(df_clean.columns),
            "topic": topic
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
            except Exception as e:
                print(f"⚠️  AI package creation failed: {e}")
                result["ai_package_error"] = str(e)
        
        return result
        
    except Exception as e:
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
        
    except Exception as e:
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
        
    except Exception as e:
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
        
    except Exception as e:
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
        except Exception as e:
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
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "query": query,
            "datasets": [],
            "total_found": 0,
        }

SQL_SAMPLE_LIMIT = int(os.getenv("SMOOTHCSV_SQL_SAMPLE_LIMIT", "5000"))
SQL_PREVIEW_LIMIT = int(os.getenv("SMOOTHCSV_SQL_PREVIEW_LIMIT", "200"))


def _get_smoothcsv_db_path(config: Config) -> Path:
    return config.data_root / "smoothcsv_cache.db"


def _init_smoothcsv_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dataset_mapping (
            dataset_id INTEGER PRIMARY KEY,
            table_name TEXT NOT NULL,
            file_hash TEXT,
            sample_limit INTEGER,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def _smoothcsv_table_name(dataset_id: int) -> str:
    return f"table{dataset_id:06d}"


def _ensure_smoothcsv_table(
    conn: sqlite3.Connection,
    dataset: dict,
    sample_limit: int,
) -> str:
    _init_smoothcsv_db(conn)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT table_name, file_hash, sample_limit FROM dataset_mapping WHERE dataset_id = ?",
        (dataset["id"],),
    )
    row = cursor.fetchone()
    table_name = row["table_name"] if row else _smoothcsv_table_name(dataset["id"])
    current_hash = dataset.get("file_hash")
    needs_reload = (
        row is None
        or row["file_hash"] != current_hash
        or row["sample_limit"] != sample_limit
    )

    if needs_reload:
        file_path = Path(dataset["file_path"])
        if not file_path.exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")
        df = pd.read_csv(file_path, nrows=sample_limit)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        cursor.execute(
            """
            INSERT INTO dataset_mapping (dataset_id, table_name, file_hash, sample_limit)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(dataset_id) DO UPDATE SET
                table_name = excluded.table_name,
                file_hash = excluded.file_hash,
                sample_limit = excluded.sample_limit,
                updated_at = CURRENT_TIMESTAMP
            """,
            (dataset["id"], table_name, current_hash, sample_limit),
        )
        conn.commit()

    return table_name


def _prepare_smoothcsv_sql(sql: str, limit: int) -> str:
    sql = sql.strip().rstrip(";")
    if not sql:
        raise ValueError("Missing SQL query.")
    if not sql.lower().startswith("select"):
        raise ValueError("Only SELECT queries are supported.")
    if not re.search(r"\blimit\b", sql, flags=re.IGNORECASE):
        sql = f"{sql} LIMIT {limit}"
    return sql


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

        db_path = _get_smoothcsv_db_path(config)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            table_name = _ensure_smoothcsv_table(conn, dataset, SQL_SAMPLE_LIMIT)
            cursor = conn.cursor()
            cursor.execute("DROP VIEW IF EXISTS dataset")
            cursor.execute(f'CREATE TEMP VIEW dataset AS SELECT * FROM "{table_name}"')

            query_sql = _prepare_smoothcsv_sql(sql, int(limit))
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
    except Exception as e:
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
        new_id = catalog.index_dataset(dest_path, force=True)
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
    except Exception as e:
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
    except Exception as e:
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
    except Exception as e:
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
    except Exception as e:
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
    except Exception as e:
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
    except Exception as e:
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

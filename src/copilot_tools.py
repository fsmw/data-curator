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

import json
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
        local_datasets = catalog.search_datasets(query=query, source=source, topic=topic)
        
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
# TOOL 2: Preview Data
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

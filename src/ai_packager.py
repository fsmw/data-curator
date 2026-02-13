"""
AI Packager - Prepare datasets for AI agent consumption.

This module creates AI-ready packages of datasets including:
- schema.json: Data structure definition
- context_owid.md: Extracted metadata from OWID
- prompts.json: Suggested prompts for analysis
- data_summary.json: Statistics and quality metrics
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime


class AIPackager:
    """Creates AI-ready packages from datasets and metadata."""

    def __init__(self, output_dir: Path):
        """
        Initialize AI Packager.

        Args:
            output_dir: Directory to save AI packages
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_schema(self, df: pd.DataFrame, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate JSON schema from DataFrame.

        Args:
            df: DataFrame to analyze
            metadata: Dataset metadata

        Returns:
            Schema dictionary
        """
        columns = []

        for col in df.columns:
            col_info = {
                "name": col,
                "type": str(df[col].dtype),
                "description": self._infer_column_description(col, metadata),
                "sample_values": df[col].dropna().head(5).tolist() if not df[col].empty else [],
                "null_count": int(df[col].isna().sum()),
                "null_percentage": float(df[col].isna().sum() / len(df) * 100),
            }

            # Add statistics for numeric columns
            if pd.api.types.is_numeric_dtype(df[col]):
                col_info["statistics"] = {
                    "min": float(df[col].min()) if not df[col].empty else None,
                    "max": float(df[col].max()) if not df[col].empty else None,
                    "mean": float(df[col].mean()) if not df[col].empty else None,
                    "median": float(df[col].median()) if not df[col].empty else None,
                }

            columns.append(col_info)

        schema = {
            "dataset_info": {
                "name": metadata.get("title", "Unknown Dataset"),
                "slug": metadata.get("slug", ""),
                "description": metadata.get("description", ""),
                "source": metadata.get("sources", [{}])[0].get("name", "Unknown") if metadata.get("sources") else "Unknown",
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "created_at": datetime.now().isoformat(),
            },
            "columns": columns,
        }

        return schema

    def _infer_column_description(self, column: str, metadata: Dict[str, Any]) -> str:
        """Infer description for a column based on name and metadata."""
        col_lower = column.lower()

        # Common column descriptions
        descriptions = {
            "country": "Country or region name",
            "year": "Year of observation",
            "country_code": "ISO country code",
            "entity": "Entity name (country, region, or organization)",
        }

        if col_lower in descriptions:
            return descriptions[col_lower]

        # Try to get from metadata unit
        unit = metadata.get("unit", "")
        if unit and column.lower() not in ["country", "year", "entity", "code"]:
            return f"Value measured in {unit}"

        return f"{column.replace('_', ' ').title()}"

    def create_context_owid(self, metadata: Dict[str, Any]) -> str:
        """
        Create markdown context document from OWID metadata.

        Args:
            metadata: OWID metadata dictionary

        Returns:
            Markdown content
        """
        raw_metadata = metadata.get("raw_metadata") or {}
        description = metadata.get("description") or raw_metadata.get("description") or "No description available"
        note = metadata.get("note") or raw_metadata.get("note") or ""
        citation = metadata.get("citation") or raw_metadata.get("citation") or ""
        additional_info = metadata.get("methodology") or raw_metadata.get("additionalInfo") or ""

        lines = [
            f"# {metadata.get('title', 'Dataset')}",
            "",
            "## Description",
            description,
            "",
            "## Data Source",
        ]

        # Add sources
        sources = metadata.get("sources", [])
        if sources:
            for source in sources:
                name = source.get("name", "Unknown")
                url = source.get("url", "")
                date_accessed = source.get("date_accessed", "")

                if url:
                    lines.append(f"- **{name}**: [{url}]({url})")
                else:
                    lines.append(f"- **{name}**")

                if date_accessed:
                    lines.append(f"  - Date accessed: {date_accessed}")

                if source.get("description"):
                    lines.append(f"  - {source['description']}")
        else:
            lines.append("Source information not available")

        if note:
            lines.extend(["", "## Notes and Context", note])

        lines.extend(["", "## Methodology"])
        if additional_info:
            lines.append(additional_info)
        else:
            lines.append("No specific methodology documented")

        lines.extend(["", "## Units and Measurements"])
        unit = metadata.get("unit", "")
        if unit:
            lines.append(f"- **Unit**: {unit}")
        lines.append("- Data is harmonized across countries and time periods")

        lines.extend(["", "## Limitations and Notes"])
        limitations = metadata.get("limitations", [])
        if limitations:
            for limitation in limitations:
                lines.append(f"- {limitation}")
        else:
            lines.append("- See original source for specific limitations")

        lines.extend(["", "## License"])
        lines.append(f"- **License**: {metadata.get('license', 'CC BY 4.0')}")
        lines.append(f"- **URL**: {metadata.get('url', '')}")

        if metadata.get("last_updated"):
            lines.extend(["", "## Last Updated"])
            lines.append(metadata["last_updated"])

        if citation:
            lines.extend(["", "## Citation", citation])

        # Add data statistics if available
        data_stats = metadata.get("data_stats", {})
        if data_stats:
            lines.extend(["", "## Data Statistics"])
            lines.append(f"- **Total rows**: {data_stats.get('total_rows', 'N/A')}")
            lines.append(f"- **Countries**: {data_stats.get('countries_count', 'N/A')}")

            date_range = data_stats.get("date_range", {})
            if date_range.get("min_year") and date_range.get("max_year"):
                lines.append(f"- **Time range**: {date_range['min_year']} - {date_range['max_year']}")

        return "\n".join(lines)

    def create_prompts(self, metadata: Dict[str, Any], topic: str = "general") -> Dict[str, Any]:
        """
        Create suggested prompts for dataset analysis.

        Args:
            metadata: Dataset metadata
            topic: Topic category

        Returns:
            Dictionary with suggested prompts
        """
        title = metadata.get("title", "this dataset")
        description = metadata.get("description", "")

        # Base prompts applicable to most datasets
        base_prompts = [
            f"Analyze trends and patterns in {title}",
            f"Identify outliers or anomalies in {title}",
            f"Compare values across different countries/regions in {title}",
            f"What is the historical evolution of {title}?",
            f"Which countries have the highest and lowest values for {title}?",
        ]

        # Topic-specific prompts
        topic_prompts = {
            "population": [
                "Analyze population growth rates by region",
                "Compare population trends between developed and developing countries",
                "Identify countries with declining populations",
                "Correlate population growth with economic indicators",
            ],
            "health": [
                "Analyze health outcomes by income level",
                "Identify countries with best/worst health metrics",
                "Track progress towards health-related SDGs",
                "Compare health indicators across regions",
            ],
            "economy": [
                "Analyze GDP per capita trends",
                "Compare economic growth across regions",
                "Identify countries with fastest economic growth",
                "Correlate economic indicators with social outcomes",
            ],
            "energy": [
                "Analyze energy consumption patterns",
                "Compare renewable vs non-renewable energy usage",
                "Identify leaders in clean energy adoption",
                "Track progress in energy transition",
            ],
            "poverty": [
                "Analyze poverty reduction trends",
                "Compare poverty rates across regions",
                "Identify countries with significant poverty reduction",
                "Correlate poverty with education and health outcomes",
            ],
            "education": [
                "Analyze education enrollment trends",
                "Compare literacy rates across countries",
                "Identify gender gaps in education",
                "Track progress in education access",
            ],
            "climate": [
                "Analyze CO2 emissions trends",
                "Compare emissions per capita across countries",
                "Track progress towards climate goals",
                "Identify countries with declining emissions",
            ],
        }

        specific_prompts = topic_prompts.get(topic.lower(), [])

        # Context-aware prompts based on description
        context_prompts = []
        if "growth" in description.lower():
            context_prompts.append(f"Analyze growth rates and project future trends for {title}")
        if "rate" in description.lower():
            context_prompts.append(f"Compare rates across different demographics in {title}")
        if "per capita" in description.lower():
            context_prompts.append(f"Analyze per capita variations and their implications")

        all_prompts = base_prompts + specific_prompts + context_prompts

        return {
            "dataset_name": title,
            "topic": topic,
            "suggested_prompts": all_prompts[:10],  # Top 10 prompts
            "analysis_types": [
                "Trend analysis",
                "Comparative analysis",
                "Outlier detection",
                "Correlation analysis",
                "Regional comparison",
                "Time series forecasting",
            ],
            "context_hints": {
                "unit": metadata.get("unit", ""),
                "time_range": metadata.get("data_stats", {}).get("date_range", {}),
                "geographic_coverage": "Global" if metadata.get("data_stats", {}).get("countries_count", 0) > 100 else "Regional",
            },
        }

    def package_dataset(
        self,
        df: pd.DataFrame,
        metadata: Dict[str, Any],
        topic: str,
        source: str,
        output_path: Path,
    ) -> Dict[str, Path]:
        """
        Create complete AI-ready package for a dataset.

        Args:
            df: DataFrame with data
            metadata: Dataset metadata
            topic: Topic category
            source: Data source
            output_path: Base path for output files

        Returns:
            Dictionary mapping file types to paths
        """
        # Ensure output directory exists
        output_path.mkdir(parents=True, exist_ok=True)

        # Get dataset identifier
        dataset_name = output_path.name

        # 1. Save schema
        schema = self.create_schema(df, metadata)
        schema_path = output_path / "schema.json"
        with open(schema_path, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)

        # 2. Save OWID context
        context = self.create_context_owid(metadata)
        context_path = output_path / "context_owid.md"
        with open(context_path, "w", encoding="utf-8") as f:
            f.write(context)

        # 3. Save prompts
        prompts = self.create_prompts(metadata, topic)
        prompts_path = output_path / "prompts.json"
        with open(prompts_path, "w", encoding="utf-8") as f:
            json.dump(prompts, f, indent=2, ensure_ascii=False)

        # 4. Save data summary
        summary = {
            "dataset_info": {
                "name": dataset_name,
                "topic": topic,
                "source": source,
                "created_at": datetime.now().isoformat(),
            },
            "files": {
                "data": f"{dataset_name}.csv",
                "schema": "schema.json",
                "context": "context_owid.md",
                "prompts": "prompts.json",
            },
            "ai_ready": True,
        }
        summary_path = output_path / "data_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        return {
            "schema": schema_path,
            "context": context_path,
            "prompts": prompts_path,
            "summary": summary_path,
        }

    def enhance_existing_dataset(
        self,
        csv_path: Path,
        metadata: Dict[str, Any],
        topic: str = "general",
    ) -> Dict[str, Path]:
        """
        Enhance an existing dataset with AI-ready packaging.

        Args:
            csv_path: Path to existing CSV file
            metadata: Dataset metadata
            topic: Topic category

        Returns:
            Dictionary mapping file types to paths
        """
        # Read existing CSV
        df = pd.read_csv(csv_path)

        # Get parent directory
        output_path = csv_path.parent

        # Create package
        source = metadata.get("sources", [{}])[0].get("name", "unknown") if metadata.get("sources") else "unknown"

        return self.package_dataset(df, metadata, topic, source, output_path)


def create_ai_package_from_owid(
    csv_path: Path,
    owid_metadata: Dict[str, Any],
    topic: str = "general",
) -> Dict[str, Path]:
    """
    Convenience function to create AI package from OWID data.

    Args:
        csv_path: Path to CSV file
        owid_metadata: Metadata from OWID API
        topic: Topic category

    Returns:
        Dictionary with paths to generated files
    """
    packager = AIPackager(csv_path.parent)
    return packager.enhance_existing_dataset(csv_path, owid_metadata, topic)

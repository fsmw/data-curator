"""
Web-optimized data visualization utilities using Vega-Lite.

Provides interactive, responsive charts for the Flask web interface.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import json


class VegaLiteChartBuilder:
    """Build Vega-Lite specifications for web display."""

    # Professional color palette for economic data
    # Defaults; overwritten if brand assets are loaded
    PROFESSIONAL_COLORS = [
        "#002b36", "#b58900", "#cb4b16", "#dc322f", 
        "#d33682", "#6c71c4", "#268bd2", "#2aa198", "#859900"
    ]

    @staticmethod
    def _load_brand_colors():
        """Attempt to load brand colors from assets."""
        try:
            from pathlib import Path
            import json
            # Assume file is at assets/brand/colors.json relative to project root
            # src/visualization_web.py -> src -> root
            path = Path(__file__).parent.parent / "assets" / "brand" / "colors.json"
            if path.exists():
                with open(path, 'r') as f:
                    brand = json.load(f)
                    if "chart_sequence" in brand:
                        VegaLiteChartBuilder.PROFESSIONAL_COLORS = brand["chart_sequence"]
        except Exception as e:
            print(f"Warning: Could not load brand colors: {e}")

    # Load on class definition (or first access if preferred, but simple here)
    # _load_brand_colors() calls are usually inside methods or executed once


    @staticmethod
    def build_time_series(
        data: pd.DataFrame,
        x_col: str = "year",
        y_col: Optional[str] = None,
        series_col: str = "country",
        title: str = "",
        max_series: int = 8,
        height: int = 450,
        width: int = 800,
    ) -> Dict[str, Any]:
        """
        Build interactive time-series Vega-Lite specification.

        Automatically limits series and provides smooth interactivity.

        Args:
            data: DataFrame with time series data
            x_col: Column for X-axis (typically 'year')
            y_col: Column for Y-axis (value). If None, uses first numeric col
            series_col: Column to group by (typically 'country')
            title: Chart title
            max_series: Maximum number of series to display (default 8)
            height: Chart height in pixels
            width: Chart width in pixels

        Returns:
            Vega-Lite specification dict
        """

        # Get unique series, limit to max_series
        unique_series = sorted(data[series_col].unique())[:max_series]
        filtered_data = data[data[series_col].isin(unique_series)].copy()

        # Auto-detect Y column if not specified
        if y_col is None:
            numeric_cols = filtered_data.select_dtypes(
                include=["number"]
            ).columns.tolist()
            y_col = next(
                (col for col in numeric_cols if col not in [x_col, series_col]),
                numeric_cols[0] if numeric_cols else "value",
            )

        # Clean data: remove NaN values
        filtered_data = filtered_data.dropna(subset=[x_col, y_col, series_col])

        # Convert to records
        data_records = filtered_data.to_dict(orient="records")

        spec = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": title,
            "data": {"values": data_records},
            "width": width,
            "height": height,
            "mark": {"type": "line", "point": True, "tooltip": True, "strokeWidth": 2},
            "encoding": {
                "x": {
                    "field": x_col,
                    "type": "quantitative",
                    "title": x_col.replace("_", " ").title(),
                    "axis": {
                        "labelAngle": -45,
                        "labelFontSize": 11,
                        "titleFontSize": 12,
                    },
                },
                "y": {
                    "field": y_col,
                    "type": "quantitative",
                    "title": y_col.replace("_", " ").title(),
                    "scale": {"zero": False},
                    "axis": {"labelFontSize": 11, "titleFontSize": 12},
                },
                "color": {
                    "field": series_col,
                    "type": "nominal",
                    "scale": {"range": VegaLiteChartBuilder.PROFESSIONAL_COLORS},
                    "legend": {"columns": 2, "labelFontSize": 11, "titleFontSize": 12},
                },
                "tooltip": [
                    {
                        "field": series_col,
                        "type": "nominal",
                        "title": series_col.replace("_", " ").title(),
                    },
                    {
                        "field": x_col,
                        "type": "quantitative",
                        "title": x_col.replace("_", " ").title(),
                    },
                    {
                        "field": y_col,
                        "type": "quantitative",
                        "title": y_col.replace("_", " ").title(),
                        "format": ".2f",
                    },
                ],
            },
            "selection": {
                "grid": {"type": "interval", "bind": "scales"},
                "highlight": {
                    "type": "single",
                    "on": "mouseover",
                    "fields": [series_col],
                },
            },
            "config": {
                "mark": {"tooltip": True},
                "axis": {"grid": True, "gridOpacity": 0.1},
                "title": {"fontSize": 14, "fontWeight": "bold"},
            },
        }

        return spec

    @staticmethod
    def build_bar_chart(
        data: pd.DataFrame,
        category_col: str,
        value_col: str,
        title: str = "",
        height: int = 400,
        width: int = 800,
    ) -> Dict[str, Any]:
        """Build bar chart specification."""

        filtered_data = data.dropna(subset=[category_col, value_col]).copy()
        # Limit to top 20 categories
        if len(filtered_data) > 20:
            filtered_data = filtered_data.nlargest(20, value_col)

        spec = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": title,
            "data": {"values": filtered_data.to_dict(orient="records")},
            "width": width,
            "height": height,
            "mark": {"type": "bar", "tooltip": True},
            "encoding": {
                "x": {
                    "field": category_col,
                    "type": "nominal",
                    "axis": {"labelAngle": -45, "labelFontSize": 11},
                },
                "y": {
                    "field": value_col,
                    "type": "quantitative",
                    "axis": {"labelFontSize": 11},
                },
                "color": {
                    "field": value_col,
                    "type": "quantitative",
                    "scale": {"scheme": "blues"},
                },
                "tooltip": [
                    {"field": category_col, "type": "nominal"},
                    {"field": value_col, "type": "quantitative", "format": ".2f"},
                ],
            },
        }

        return spec

    @staticmethod
    def build_scatter_chart(
        data: pd.DataFrame,
        x_col: str,
        y_col: str,
        series_col: Optional[str] = None,
        title: str = "",
        height: int = 450,
        width: int = 800,
    ) -> Dict[str, Any]:
        """Build scatter plot specification."""

        filtered_data = data.dropna(subset=[x_col, y_col])
        if series_col:
            filtered_data = filtered_data.dropna(subset=[series_col])

        encoding = {
            "x": {
                "field": x_col,
                "type": "quantitative",
                "axis": {"labelFontSize": 11, "titleFontSize": 12},
            },
            "y": {
                "field": y_col,
                "type": "quantitative",
                "axis": {"labelFontSize": 11, "titleFontSize": 12},
            },
            "tooltip": [
                {"field": x_col, "type": "quantitative", "format": ".2f"},
                {"field": y_col, "type": "quantitative", "format": ".2f"},
            ],
        }

        if series_col:
            encoding["color"] = {
                "field": series_col,
                "type": "nominal",
                "scale": {"range": VegaLiteChartBuilder.PROFESSIONAL_COLORS},
            }
            encoding["tooltip"].insert(0, {"field": series_col, "type": "nominal"})

        spec = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": title,
            "data": {"values": filtered_data.to_dict(orient="records")},
            "width": width,
            "height": height,
            "mark": {"type": "point", "size": 100, "tooltip": True},
            "encoding": encoding,
            "selection": {"grid": {"type": "interval", "bind": "scales"}},
        }

        return spec


class ChartDataPreparator:
    """Prepare and normalize data for charting."""

    @staticmethod
    def prepare_preview_data(rows: List[Dict], columns: List[str]) -> pd.DataFrame:
        """
        Convert preview data to DataFrame.

        Args:
            rows: List of data rows
            columns: List of column names

        Returns:
            Prepared DataFrame
        """
        df = pd.DataFrame(rows, columns=columns)

        # Auto-convert numeric strings
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            except:
                pass

        return df

    @staticmethod
    def get_series_info(
        df: pd.DataFrame, series_col: str = "country"
    ) -> Dict[str, Any]:
        """
        Get information about available series.

        Returns:
            Dict with series count, list, and numeric columns
        """
        unique_series = sorted(df[series_col].unique())
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

        return {
            "total_series": len(unique_series),
            "series": unique_series,
            "numeric_columns": numeric_cols,
            "total_rows": len(df),
        }

    @staticmethod
    def get_top_series(
        df: pd.DataFrame,
        series_col: str = "country",
        value_col: Optional[str] = None,
        limit: int = 8,
    ) -> List[str]:
        """
        Get top series by latest value or by frequency.

        Args:
            df: DataFrame
            series_col: Series column name
            value_col: Value column to sort by (optional)
            limit: Number of series to return

        Returns:
            List of top series
        """
        if value_col and value_col in df.columns:
            # Sort by latest value (highest year/date first)
            latest = (
                df.sort_values(
                    [col for col in df.columns if col not in [series_col, value_col]][
                        0
                    ],
                    ascending=False,
                )
                .groupby(series_col)[value_col]
                .first()
                .nlargest(limit)
            )
            return latest.index.tolist()
        else:
            # Sort by frequency
            return df[series_col].value_counts().head(limit).index.tolist()


class ChartExporter:
    """Export charts to various formats."""

    @staticmethod
    def spec_to_json(spec: Dict[str, Any]) -> str:
        """Convert Vega-Lite spec to JSON string."""
        return json.dumps(spec, indent=2)

    @staticmethod
    def get_vega_embed_html(spec: Dict[str, Any], container_id: str = "chart") -> str:
        """
        Generate HTML snippet for embedding chart with vega-embed.

        Returns:
            HTML string ready for embedding
        """
        spec_json = json.dumps(spec)

        return f"""
        <div id="{container_id}"></div>
        <script type="module">
          import vegaEmbed from 'https://cdn.jsdelivr.net/npm/vega-embed@6';
          const spec = {spec_json};
          vegaEmbed('#{container_id}', spec, {{
            actions: {{
              export: true,
              source: false,
              compiled: false,
              editor: false
            }}
          }});
        </script>
        </script>
        """

# Initialize branded colors if available
VegaLiteChartBuilder._load_brand_colors()

"""Browse available data sources and indicators screen."""

from textual.widgets import Static
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from .base import BaseScreen
from ..data.available_manager import AvailableDataManager


class BrowseAvailableScreen(BaseScreen):
    """Browse available indicators from all sources."""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("h", "show_help", "Help"),
        ("tab", "focus_next", "Next"),
        ("shift+tab", "focus_previous", "Prev"),
        ("up", "handle_up", "Up"),
        ("down", "handle_down", "Down"),
        ("left", "handle_left", "Left"),
        ("right", "handle_right", "Right"),
    ]

    CSS = """
    BrowseAvailableScreen {
        background: $surface;
    }

    #content {
        height: 1fr;
        overflow-y: auto;
    }
    """

    def __init__(self, app_ref=None, **kwargs):
        super().__init__(app_ref, **kwargs)
        self.data_manager = AvailableDataManager()
        self.selected_source = None
        self.selected_indicator = None
        self.selected_source_idx = 0
        self.all_sources = []

    def get_screen_id(self) -> str:
        return "browse_available"

    def refresh_data(self) -> None:
        """Load available data sources and indicators."""
        self.all_sources = self.data_manager.get_sources()
        self.data["sources"] = self.all_sources
        self.data["all_indicators"] = self.data_manager.get_all_indicators()
        self.selected_source_idx = min(self.selected_source_idx, len(self.all_sources) - 1) if self.all_sources else 0

    def get_content(self) -> Static:
        """Build the browse available content."""
        content = Static(id="content")
        content.render = self._render_content
        return content

    def _render_content(self) -> Panel:
        """Render the browse available interface."""
        content_text = Text()

        # Title
        content_text.append("📥 Browse Available Data\n\n", style="bold cyan")

        sources = self.data.get("sources", [])

        if not sources:
            content_text.append(
                "No data sources configured. Check indicators.yaml\n",
                style="yellow",
            )
            return Panel(
                content_text,
                title="Browse Available Data",
                border_style="cyan",
                expand=True,
            )

        # Sources list
        content_text.append("🌐 Data Sources:\n", style="bold cyan")
        for i, source in enumerate(sources):
            indicators = self.data_manager.get_indicators_by_source(source)
            source_info = self.data_manager.get_source_info(source)

            is_selected = i == self.selected_source_idx
            indicator = " ▶ " if is_selected else "   "
            style = "bold yellow on blue" if is_selected else "cyan"

            content_text.append(f"{indicator}{i+1}. {source} ({len(indicators)})\n", style=style)

        content_text.append("\n")

        # Show indicators for selected source
        if self.selected_source:
            indicators = self.data_manager.get_indicators_by_source(self.selected_source)
            source_info = self.data_manager.get_source_info(self.selected_source)

            content_text.append(
                f"📊 Indicators from '{self.selected_source}':\n\n",
                style="bold green",
            )

            for ind in indicators[:15]:  # Show first 15
                content_text.append(f"• {ind['name']}\n", style="green")
                if ind.get("description"):
                    content_text.append(
                        f"  {ind['description'][:60]}...\n",
                        style="dim green",
                    )
                content_text.append(
                    f"  Topic: {ind.get('topic', 'N/A')} | Years: {ind.get('years_available', 'N/A')}\n\n",
                    style="dim",
                )

            if len(indicators) > 15:
                content_text.append(
                    f"  ... and {len(indicators) - 15} more indicators\n",
                    style="dim",
                )

        content_text.append("\n")
        content_text.append(
            "Controls: [Tab/↓] Next source | [Shift+Tab/↑] Previous | [Enter] Details\n",
            style="dim",
        )

        return Panel(
            content_text,
            title="Browse Available Data",
            border_style="cyan",
            expand=True,
        )

    def action_focus_next(self) -> None:
        """Move to next source with Tab."""
        if self.all_sources:
            self.selected_source_idx = (self.selected_source_idx + 1) % len(self.all_sources)
            self.selected_source = self.all_sources[self.selected_source_idx]
            self.update_display()

    def action_focus_previous(self) -> None:
        """Move to previous source with Shift+Tab."""
        if self.all_sources:
            self.selected_source_idx = (self.selected_source_idx - 1) % len(self.all_sources)
            self.selected_source = self.all_sources[self.selected_source_idx]
            self.update_display()

    def action_handle_down(self) -> None:
        """Move down with arrow key."""
        self.action_focus_next()

    def action_handle_up(self) -> None:
        """Move up with arrow key."""
        self.action_focus_previous()

    def action_handle_right(self) -> None:
        """Expand current source."""
        pass

    def action_handle_left(self) -> None:
        """Collapse current source."""
        pass

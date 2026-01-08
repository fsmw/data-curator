"""Search indicators screen with filtering."""

from textual.widgets import Static, Input
from textual.containers import Vertical
from rich.panel import Panel
from rich.text import Text
from .base import BaseScreen
from ..data.available_manager import AvailableDataManager


class SearchScreen(BaseScreen):
    """Search indicators across sources with filters."""

    CSS = """
    SearchScreen {
        background: $surface;
    }

    #content {
        height: 1fr;
        overflow-y: auto;
    }

    #search_input {
        margin: 1;
        border: solid $primary;
    }
    """

    def __init__(self, app_ref=None, **kwargs):
        super().__init__(app_ref, **kwargs)
        self.data_manager = AvailableDataManager()
        self.search_query = ""
        self.filter_source = "All"
        self.filter_topic = "All"
        self.search_results = []

    def get_screen_id(self) -> str:
        return "search"

    def refresh_data(self) -> None:
        """Load search data."""
        self.data["sources"] = self.data_manager.get_sources()
        self.data["all_indicators"] = self.data_manager.get_all_indicators()
        self._perform_search()

    def _perform_search(self):
        """Execute search with current filters."""
        if not self.search_query:
            self.search_results = self.data.get("all_indicators", [])
        else:
            self.search_results = self.data_manager.search_indicators(self.search_query)

        # Apply source filter
        if self.filter_source != "All":
            self.search_results = [
                ind for ind in self.search_results
                if ind.get("source") == self.filter_source
            ]

        # Apply topic filter
        if self.filter_topic != "All":
            self.search_results = [
                ind for ind in self.search_results
                if ind.get("topic") == self.filter_topic
            ]

    def get_content(self) -> Static:
        """Build the search screen content."""
        content = Static(id="content")
        content.render = self._render_search
        return content

    def _render_search(self) -> Panel:
        """Render the search interface."""
        content_text = Text()

        # Title
        content_text.append("🔍 Search Indicators\n\n", style="bold cyan")

        # Search box
        content_text.append("Search: ", style="cyan")
        content_text.append(
            f"[{self.search_query or 'type to search...'}]\n\n",
            style="yellow" if self.search_query else "dim",
        )

        # Filters
        content_text.append("Filters:\n", style="bold cyan")
        content_text.append(
            f"  Source: {self.filter_source} | Topic: {self.filter_topic}\n\n",
            style="cyan",
        )

        # Results
        results = self.search_results
        if not results:
            content_text.append(
                "No results found. Try different search terms.\n",
                style="yellow",
            )
        else:
            content_text.append(
                f"Results ({len(results)} total):\n\n", style="bold green"
            )

            for i, indicator in enumerate(results[:20], 1):  # Show first 20
                # Status indicator
                status = "✓"  # Placeholder for downloaded status
                content_text.append(f"{i}. {indicator['name']}\n", style="green")
                content_text.append(
                    f"   Source: {indicator.get('source', 'N/A')} | "
                    f"Topic: {indicator.get('topic', 'N/A')}\n",
                    style="dim",
                )

                if indicator.get("description"):
                    desc = indicator["description"][:70]
                    content_text.append(f"   {desc}\n\n", style="dim green")
                else:
                    content_text.append("\n", style="dim")

            if len(results) > 20:
                content_text.append(
                    f"... and {len(results) - 20} more results\n", style="dim"
                )

        content_text.append("\n")
        content_text.append(
            "Controls: [Type] Search | [F] Filters | [↑↓] Navigate | [D] Download | [/] Toggle Search\n",
            style="dim",
        )

        return Panel(
            content_text,
            title="Search Indicators",
            border_style="cyan",
            expand=True,
        )

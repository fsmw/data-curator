"""Download manager screen for initiating data downloads."""

from textual.widgets import Static, Button, Select, Input
from textual.containers import Vertical, Horizontal, Container
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from .base import BaseScreen
from ..data.available_manager import AvailableDataManager
from ..data.download_coordinator import DownloadCoordinator
from ..widgets import InputDialog, SelectDialog, ConfirmDialog, AlertDialog, FilterDialog


class DownloadScreen(BaseScreen):
    """Manage downloads and configure parameters."""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("h", "show_help", "Help"),
        ("s", "start_downloads", "Start"),
        ("x", "cancel_downloads", "Cancel"),
        ("r", "remove_from_queue", "Remove"),
        ("c", "clear_queue", "Clear"),
        ("p", "show_preview", "Preview"),
        ("shift+s", "action_select_source", "Source"),
        ("shift+c", "action_select_countries", "Countries"),
        ("shift+y", "action_select_year_range", "Years"),
        ("tab", "focus_next", "Next"),
        ("shift+tab", "focus_previous", "Prev"),
        ("up", "handle_up", "Up"),
        ("down", "handle_down", "Down"),
        ("left", "handle_left", "Left"),
        ("right", "handle_right", "Right"),
    ]

    CSS = """
    DownloadScreen {
        background: $surface;
    }

    #content {
        height: 1fr;
        overflow-y: auto;
    }

    #form_container {
        width: 100%;
        border: solid $primary;
        padding: 1;
    }

    #preview_container {
        width: 100%;
        border: solid $accent;
        padding: 1;
    }
    """

    def __init__(self, app_ref=None, **kwargs):
        super().__init__(app_ref, **kwargs)
        self.data_manager = AvailableDataManager()
        self.coordinator = DownloadCoordinator(progress_callback=self._on_progress)
        
        # Form state
        self.selected_source = "oecd"
        self.selected_indicator = None
        self.selected_topic = "salarios_reales"
        self.selected_coverage = "latam"
        self.year_start = 2010
        self.year_end = 2024
        self.selected_countries = []
        self.is_downloading = False
        
        # Navigation state
        self.focused_field = "source"  # source, indicator, topic, coverage, years, countries
        self.field_order = ["source", "indicator", "topic", "coverage", "years", "countries"]

    def get_screen_id(self) -> str:
        return "download"

    def refresh_data(self) -> None:
        """Load available sources and indicators."""
        self.data["sources"] = self.data_manager.get_sources()
        self.data["all_indicators"] = self.data_manager.get_all_indicators()

    def get_content(self) -> Static:
        """Build the download manager content."""
        content = Static(id="content")
        content.render = self._render_download
        return content

    def _render_download(self) -> Panel:
        """Render the download manager interface."""
        content_text = Text()

        # Title
        content_text.append("⬇️  Download Manager\n\n", style="bold cyan")

        # Form section
        content_text.append("DOWNLOAD FORM\n", style="bold green")
        content_text.append("─" * 70 + "\n\n", style="green")

        # Helper to show focused field
        def field_style(field_name):
            if field_name == self.focused_field:
                return "bold yellow on blue"
            return "cyan"

        # Source selector
        sources = self.data.get("sources", [])
        sources_list = " | ".join(sources) if sources else "No sources available"
        content_text.append(f"Source:\n", style=field_style("source"))
        content_text.append(f"  [{self.selected_source}]\n", style="yellow" if self.focused_field == "source" else "cyan")
        content_text.append(f"  Available: {sources_list}\n", style="dim")
        content_text.append("  Use [Shift+S] to change | [Tab] next field\n\n", style="dim" if self.focused_field != "source" else "bold")

        # Indicator selector
        available_inds = self.data_manager.get_indicators_by_source(self.selected_source)
        content_text.append(f"Indicator ({len(available_inds)} available):\n", style=field_style("indicator"))
        if available_inds:
            for i, ind in enumerate(available_inds[:5], 1):
                is_selected = (
                    self.selected_indicator == ind["id"] if self.selected_indicator else False
                )
                marker = " ▶ " if is_selected else "   "
                content_text.append(f"{marker}{i}. {ind['name']}\n", style="green" if is_selected else "dim")
            if len(available_inds) > 5:
                content_text.append(f"   ... and {len(available_inds) - 5} more\n", style="dim")
        else:
            content_text.append("  No indicators for this source\n", style="yellow")
        content_text.append("  Use arrow keys to select | [Enter] to confirm\n\n", style="dim" if self.focused_field != "indicator" else "bold")

        # Topic
        content_text.append(f"Topic:\n", style=field_style("topic"))
        content_text.append(f"  [{self.selected_topic}]\n", style="yellow" if self.focused_field == "topic" else "cyan")
        content_text.append("  Use arrow keys or type topic name\n\n", style="dim" if self.focused_field != "topic" else "bold")

        # Coverage
        content_text.append(f"Coverage:\n", style=field_style("coverage"))
        content_text.append(f"  [{self.selected_coverage}]\n", style="yellow" if self.focused_field == "coverage" else "cyan")
        content_text.append("  Use arrow keys or type coverage\n\n", style="dim" if self.focused_field != "coverage" else "bold")

        # Year range
        content_text.append(f"Year Range:\n", style=field_style("years"))
        content_text.append(f"  {self.year_start} - {self.year_end}\n", style="yellow" if self.focused_field == "years" else "cyan")
        content_text.append("  Use [Shift+Y] to change years\n\n", style="dim" if self.focused_field != "years" else "bold")

        # Countries
        countries = [
            "ARG", "BRA", "CHL", "COL", "MEX", "PER", "URY",
            "ECU", "BOL", "VEN", "GUY", "SUR", "PRY"
        ]
        content_text.append(f"Countries ({len(self.selected_countries)} selected):\n", style=field_style("countries"))
        if self.selected_countries:
            content_text.append(
                f"  {', '.join(self.selected_countries)}\n", style="yellow" if self.focused_field == "countries" else "green"
            )
        else:
            content_text.append("  [Click to select countries]\n", style="yellow" if self.focused_field == "countries" else "dim")
        content_text.append(f"  Available: {', '.join(countries)}\n", style="dim")
        content_text.append("  Use [Shift+C] to select | [Tab] to navigate\n\n", style="dim" if self.focused_field != "countries" else "bold")

        # Buttons
        content_text.append("─" * 70 + "\n\n", style="green")
        content_text.append("[P] Preview | [+] Add to Queue | [C] Clear\n\n", style="bold green")

        # Queue section
        content_text.append("DOWNLOAD QUEUE\n", style="bold cyan")
        content_text.append("─" * 70 + "\n\n", style="cyan")

        queue = self.coordinator.get_queue()
        if queue:
            for i, item in enumerate(queue, 1):
                content_text.append(
                    f"{i}. {item['source']} - {item['indicator']} ({item['coverage']})\n",
                    style="yellow"
                )
            content_text.append(f"\nTotal queued: {len(queue)}\n", style="dim")
            
            if self.is_downloading:
                content_text.append("[B] Running... | [X] Cancel\n\n", style="red")
            else:
                content_text.append("[S] Start Downloads | [R] Remove Item\n\n", style="yellow")
        else:
            content_text.append("Queue is empty\n", style="dim")
            content_text.append("Add indicators to download queue above\n\n", style="dim")

        # Info
        content_text.append("─" * 70 + "\n", style="cyan")
        content_text.append("Use [Tab] to jump between fields | [Arrow keys] to navigate\n", style="bold yellow")

        return Panel(
            content_text,
            title="Download Manager",
            border_style="cyan",
            expand=True,
        )

    def action_select_countries(self) -> None:
        """Show country selection dialog."""
        countries = [
            "ARG", "BRA", "CHL", "COL", "MEX", "PER", "URY",
            "ECU", "BOL", "VEN", "GUY", "SUR", "PRY"
        ]
        
        def on_filter(selected: list[str]):
            self.selected_countries = selected
        
        dialog = FilterDialog(
            title="Select Countries",
            options=countries,
            on_filter=on_filter
        )
        self.app.mount(dialog)

    def action_select_source(self) -> None:
        """Show source selection dialog."""
        sources = self.data.get("sources", [])
        if not sources:
            self._show_alert("No sources", "No data sources available")
            return
        
        def on_select(source: str):
            self.selected_source = source
        
        dialog = SelectDialog(
            title="Select Data Source",
            items=sources,
            on_select=on_select
        )
        self.app.mount(dialog)

    def action_select_year_range(self) -> None:
        """Show year range input dialog."""
        def on_submit(value: str):
            try:
                parts = value.split("-")
                if len(parts) == 2:
                    start, end = int(parts[0].strip()), int(parts[1].strip())
                    if start <= end:
                        self.year_start = start
                        self.year_end = end
                    else:
                        self._show_alert("Invalid", "Start year must be <= end year", "error")
                else:
                    self._show_alert("Invalid", "Format: YYYY-YYYY", "error")
            except ValueError:
                self._show_alert("Invalid", "Please enter valid years", "error")
        
        dialog = InputDialog(
            title="Year Range",
            prompt="Enter year range (format: YYYY-YYYY)",
            default_value=f"{self.year_start}-{self.year_end}",
            on_submit=on_submit
        )
        self.app.mount(dialog)

    def action_add_to_queue(self) -> None:
        """Add download to queue."""
        if not self.selected_indicator:
            self._show_alert("No indicator", "Please select an indicator first", "warning")
            return
        
        item = {
            "source": self.selected_source,
            "indicator": self.selected_indicator,
            "topic": self.selected_topic,
            "coverage": self.selected_coverage,
            "start_year": self.year_start,
            "end_year": self.year_end,
            "countries": self.selected_countries
        }
        
        if self.coordinator.add_to_queue(item):
            self._show_alert("Added", f"Added to queue ({self.coordinator.get_queue_size()} total)")
        else:
            self._show_alert("Error", "Could not add to queue", "error")

    def action_clear_queue(self) -> None:
        """Clear download queue."""
        if not self.coordinator.get_queue():
            self._show_alert("Empty", "Queue is already empty", "info")
            return
        
        def confirm():
            self.coordinator.clear_queue()
            self._show_alert("Cleared", "Download queue cleared")
        
        dialog = ConfirmDialog(
            title="Clear Queue",
            message="Clear all items from download queue?",
            on_confirm=confirm
        )
        self.app.mount(dialog)

    def action_start_downloads(self) -> None:
        """Start processing the download queue."""
        queue = self.coordinator.get_queue()
        if not queue:
            self._show_alert("Empty Queue", "Add items before starting", "warning")
            return
        
        if self.is_downloading:
            self._show_alert("Already Running", "Downloads are already in progress", "warning")
            return
        
        self.is_downloading = True
        
        def on_complete():
            self.is_downloading = False
            self._show_alert(
                "Complete",
                f"Downloaded {len(queue)} indicator(s)",
                "success"
            )
        
        self.coordinator.start_queue(on_complete=on_complete)

    def action_cancel_downloads(self) -> None:
        """Cancel ongoing downloads."""
        if not self.is_downloading:
            return
        
        self.coordinator.cancel()
        self.is_downloading = False
        self._show_alert("Cancelled", "Download cancelled")

    def action_remove_from_queue(self) -> None:
        """Remove the last item from queue."""
        queue = self.coordinator.get_queue()
        if queue:
            self.coordinator.remove_from_queue(len(queue) - 1)
            self._show_alert("Removed", "Last item removed from queue")
        else:
            self._show_alert("Empty", "Queue is empty", "info")

    def action_show_preview(self) -> None:
        """Show download preview."""
        if not self.selected_indicator:
            self._show_alert("No Selection", "Select an indicator first", "warning")
            return
        
        message = f"""Source: {self.selected_source}
Indicator: {self.selected_indicator}
Topic: {self.selected_topic}
Coverage: {self.selected_coverage}
Year Range: {self.year_start} - {self.year_end}
Countries: {', '.join(self.selected_countries) if self.selected_countries else 'All'}"""
        
        self._show_alert("Download Preview", message, "info")

    def _on_progress(self, step: str, percent: int) -> None:
        """Callback from coordinator for progress updates."""
        # This would update the progress screen
        if self.app and hasattr(self.app, "get_screen"):
            try:
                progress_screen = self.app.get_screen("progress")
                if hasattr(progress_screen, "update_step_progress"):
                    progress_screen.update_step_progress(step, percent)
            except Exception:
                pass

    def action_focus_next(self) -> None:
        """Move to next field with Tab."""
        try:
            current_idx = self.field_order.index(self.focused_field)
            next_idx = (current_idx + 1) % len(self.field_order)
            self.focused_field = self.field_order[next_idx]
            self.update_display()
        except (ValueError, IndexError):
            self.focused_field = "source"

    def action_focus_previous(self) -> None:
        """Move to previous field with Shift+Tab."""
        try:
            current_idx = self.field_order.index(self.focused_field)
            prev_idx = (current_idx - 1) % len(self.field_order)
            self.focused_field = self.field_order[prev_idx]
            self.update_display()
        except (ValueError, IndexError):
            self.focused_field = "source"

    def action_handle_down(self) -> None:
        """Handle down arrow - navigate to next field."""
        self.action_focus_next()

    def action_handle_up(self) -> None:
        """Handle up arrow - navigate to previous field."""
        self.action_focus_previous()

    def action_handle_right(self) -> None:
        """Handle right arrow - depends on context."""
        # Can be used to expand options or select items
        pass

    def action_handle_left(self) -> None:
        """Handle left arrow - depends on context."""
        # Can be used to collapse options
        pass

    def _show_alert(self, title: str, message: str, alert_type: str = "info") -> None:
        """Show alert modal."""
        modal = AlertDialog(title=title, message=message, alert_type=alert_type)
        self.app.mount(modal)

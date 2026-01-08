"""Browse downloaded datasets screen."""

from textual.widgets import Static
from textual.containers import Vertical, Horizontal
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from .base import BaseScreen
from ..data.local_manager import LocalDataManager
from ..widgets import MetadataModal, ConfirmDialog, AlertDialog


class BrowseLocalScreen(BaseScreen):
    """Browse downloaded datasets organized by topic."""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("h", "show_help", "Help"),
        ("m", "view_metadata", "Metadata"),
        ("d", "delete_dataset", "Delete"),
        ("tab", "focus_next", "Next"),
        ("shift+tab", "focus_previous", "Prev"),
        ("up", "handle_up", "Up"),
        ("down", "handle_down", "Down"),
        ("left", "handle_left", "Left"),
        ("right", "handle_right", "Right"),
    ]

    CSS = """
    BrowseLocalScreen {
        background: $surface;
    }

    #content {
        height: 1fr;
        overflow: hidden;
    }

    #tree_container {
        width: 40%;
        border-right: solid $primary;
        height: 1fr;
    }

    #details_container {
        width: 60%;
        height: 1fr;
        overflow-y: auto;
    }
    """

    def __init__(self, app_ref=None, **kwargs):
        super().__init__(app_ref, **kwargs)
        self.data_manager = LocalDataManager()
        self.selected_dataset = None
        self.selected_file = None  # Track selected file for deletion
        self.selected_topic_idx = 0  # For navigation
        self.all_topics = []

    def get_screen_id(self) -> str:
        return "browse_local"

    def refresh_data(self) -> None:
        """Load local datasets."""
        self.all_topics = self.data_manager.get_topics()
        self.data["topics"] = self.all_topics
        self.selected_topic_idx = min(self.selected_topic_idx, len(self.all_topics) - 1) if self.all_topics else 0
        self.data["all_datasets"] = self.data_manager.get_all_datasets()

    def get_content(self) -> Static:
        """Build the browse local content with tree view and details."""
        container = Static(id="content")
        container.render = self._render_content
        return container

    def _render_content(self) -> Panel:
        """Render the browse local interface."""
        content_text = Text()

        # Title
        content_text.append("📂 Browse Local Data\n\n", style="bold cyan")

        # Build tree view
        topics = self.data.get("topics", [])

        if not topics:
            content_text.append(
                "No datasets found. Use Download to add data.\n",
                style="yellow",
            )
            return Panel(
                content_text,
                title="Browse Local Datasets",
                border_style="cyan",
                expand=True,
            )

        # Topics list
        content_text.append("Topics:\n", style="bold cyan")
        for i, topic in enumerate(topics):
            datasets = self.data_manager.get_datasets_by_topic(topic)
            is_selected = topic == self.selected_dataset
            indicator = " ▶ " if is_selected else "   "
            style = "bold yellow on blue" if is_selected else "cyan"
            content_text.append(
                f"{indicator}{i+1}. {topic} ({len(datasets)} datasets)\n",
                style=style,
            )

        content_text.append("\nNavigation:\n", style="dim")
        content_text.append("  [Tab] / [↓] Next topic | [Shift+Tab] / [↑] Previous\n", style="dim")
        content_text.append("  [M] View metadata | [D] Delete | [Esc] Cancel\n\n", style="dim")

        content_text.append("\n")

        # Show details for selected topic
        if self.selected_dataset:
            datasets = self.data_manager.get_datasets_by_topic(self.selected_dataset)
            content_text.append(
                f"📊 Datasets in '{self.selected_dataset}':\n\n", style="bold green"
            )

            for dataset in datasets[:10]:  # Show first 10
                content_text.append(f"• {dataset['name']}\n", style="green")
                content_text.append(
                    f"  Size: {dataset['size_readable']} | Rows: {dataset['rows']}\n",
                    style="dim",
                )
                content_text.append(
                    f"  Modified: {dataset['modified_readable']}\n\n",
                    style="dim",
                )

            if len(datasets) > 10:
                content_text.append(
                    f"  ... and {len(datasets) - 10} more datasets\n",
                    style="dim",
                )

        content_text.append("\n")
        content_text.append(
            "Controls: [↑↓] Navigate | [Enter] Select | [M] View Metadata | [D] Delete\n",
            style="dim",
        )

        return Panel(
            content_text,
            title="Browse Local Datasets",
            border_style="cyan",
            expand=True,
        )

    def action_view_metadata(self) -> None:
        """Show metadata modal for selected dataset."""
        if not self.selected_dataset:
            self._show_alert("No dataset selected", "Please select a dataset first")
            return

        datasets = self.data_manager.get_datasets_by_topic(self.selected_dataset)
        if not datasets:
            return

        dataset = datasets[0]
        
        # Build metadata content
        metadata_text = f"""
Dataset: {dataset['name']}
Topic: {self.selected_dataset}

File Information:
  Size: {dataset['size_readable']}
  Rows: {dataset['rows']}
  Modified: {dataset['modified_readable']}
  Path: {dataset['path']}

Statistics:
  Records: {dataset['rows']:,}
  Columns: {dataset.get('columns', 'N/A')}
  
Source: {dataset.get('source', 'Unknown')}
Coverage: {dataset.get('coverage', 'N/A')}
""".strip()

        modal = MetadataModal(
            title=f"📋 Metadata: {dataset['name']}",
            content=metadata_text
        )
        self.app.mount(modal)

    def action_delete_dataset(self) -> None:
        """Show confirmation dialog for deletion."""
        if not self.selected_dataset:
            self._show_alert("No dataset selected", "Please select a dataset first")
            return

        datasets = self.data_manager.get_datasets_by_topic(self.selected_dataset)
        if not datasets:
            return

        dataset = datasets[0]
        
        def confirm_delete():
            try:
                import os
                os.remove(dataset['path'])
                self.refresh_data()
                self._show_alert("Success", f"Deleted {dataset['name']}")
            except Exception as e:
                self._show_alert("Error", f"Failed to delete: {e}", "error")

        modal = ConfirmDialog(
            title="Delete Dataset",
            message=f"Are you sure you want to delete\n'{dataset['name']}'?\n\nThis cannot be undone.",
            on_confirm=confirm_delete,
            on_cancel=lambda: None
        )
        self.app.mount(modal)

    def _show_alert(self, title: str, message: str, alert_type: str = "info") -> None:
        """Show alert modal."""
        modal = AlertDialog(title=title, message=message, alert_type=alert_type)
        self.app.mount(modal)

    def action_focus_next(self) -> None:
        """Move to next topic with Tab."""
        if self.all_topics:
            self.selected_topic_idx = (self.selected_topic_idx + 1) % len(self.all_topics)
            self.selected_dataset = self.all_topics[self.selected_topic_idx]
            self.update_display()

    def action_focus_previous(self) -> None:
        """Move to previous topic with Shift+Tab."""
        if self.all_topics:
            self.selected_topic_idx = (self.selected_topic_idx - 1) % len(self.all_topics)
            self.selected_dataset = self.all_topics[self.selected_topic_idx]
            self.update_display()

    def action_handle_down(self) -> None:
        """Move down with arrow key."""
        self.action_focus_next()

    def action_handle_up(self) -> None:
        """Move up with arrow key."""
        self.action_focus_previous()

    def action_handle_right(self) -> None:
        """Expand current topic."""
        if self.selected_dataset:
            pass  # Could implement expand/collapse

    def action_handle_left(self) -> None:
        """Collapse current topic."""
        if self.selected_dataset:
            pass  # Could implement collapse

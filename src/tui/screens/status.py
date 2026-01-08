"""Status dashboard screen."""

from textual.widgets import Static, Label
from textual.containers import Vertical, Horizontal, ScrollableContainer
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from pathlib import Path
from .base import BaseScreen
from ..config import DATA_DIR, METADATA_DIR, RAW_DATA_DIR


class StatusScreen(BaseScreen):
    """Display project status and statistics."""

    CSS = """
    StatusScreen {
        background: $surface;
    }

    #content {
        height: 1fr;
        overflow: auto;
    }
    """

    def get_screen_id(self) -> str:
        return "status"

    def refresh_data(self) -> None:
        """Gather project statistics."""
        self.data = {
            "datasets": self._count_datasets(),
            "metadata": self._count_metadata(),
            "raw_data_size": self._get_raw_data_size(),
            "topics": self._get_topics(),
        }

    def _count_datasets(self) -> int:
        """Count cleaned datasets."""
        count = 0
        if DATA_DIR.exists():
            for file in DATA_DIR.rglob("*.csv"):
                count += 1
        return count

    def _count_metadata(self) -> int:
        """Count metadata files."""
        count = 0
        if METADATA_DIR.exists():
            for file in METADATA_DIR.glob("*.md"):
                count += 1
        return count

    def _get_raw_data_size(self) -> str:
        """Get total size of raw data."""
        if not RAW_DATA_DIR.exists():
            return "0 B"

        total_bytes = sum(
            f.stat().st_size for f in RAW_DATA_DIR.rglob("*") if f.is_file()
        )

        for unit in ["B", "KB", "MB", "GB"]:
            if total_bytes < 1024:
                return f"{total_bytes:.1f} {unit}"
            total_bytes /= 1024
        return f"{total_bytes:.1f} TB"

    def _get_topics(self) -> list:
        """Get list of topics."""
        if not DATA_DIR.exists():
            return []
        return [d.name for d in DATA_DIR.iterdir() if d.is_dir()]

    def get_content(self) -> Static:
        """Build the status dashboard content."""
        content = Static(id="content")
        content.render = self._render_status
        return content

    def _render_status(self) -> Panel:
        """Render the status dashboard."""
        status_text = Text()

        # Title
        status_text.append("📊 Project Status\n\n", style="bold cyan")

        # Stats table
        stats = Table(title="📈 Statistics", show_header=False, box=None)
        stats.add_row("Total Datasets:", f"{self.data['datasets']}")
        stats.add_row("Metadata Files:", f"{self.data['metadata']}")
        stats.add_row("Raw Data Size:", f"{self.data['raw_data_size']}")
        stats.add_row("Active Topics:", f"{len(self.data['topics'])}")

        status_text.append(str(stats) + "\n\n", style="cyan")

        # Topics
        if self.data["topics"]:
            status_text.append("📂 Topics:\n", style="bold green")
            for topic in sorted(self.data["topics"]):
                status_text.append(f"  • {topic}\n", style="green")
        else:
            status_text.append(
                "No datasets found. Use Download to add data.\n", style="yellow"
            )

        status_text.append("\n")
        status_text.append("Quick Actions:\n", style="bold cyan")
        status_text.append("[2] Browse Local Data\n", style="cyan")
        status_text.append("[3] Browse Available Data\n", style="cyan")
        status_text.append("[4] Search Indicators\n", style="cyan")
        status_text.append("[5] Download Data\n", style="cyan")

        return Panel(
            status_text,
            title="Status Dashboard",
            border_style="cyan",
            expand=True,
        )

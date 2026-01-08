"""Progress monitoring screen for active downloads."""

from textual.widgets import Static, ProgressBar
from textual.containers import Vertical, Container
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress as RichProgress, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
from .base import BaseScreen
from ..data.download_coordinator import DownloadCoordinator
from pathlib import Path
import time


class ProgressScreen(BaseScreen):
    """Monitor active downloads with progress tracking."""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("h", "show_help", "Help"),
        ("c", "cancel_download", "Cancel"),
        ("e", "export_logs", "Export"),
    ]

    CSS = """
    ProgressScreen {
        background: $surface;
    }

    #content {
        height: 1fr;
        overflow-y: auto;
    }
    """

    def __init__(self, app_ref=None, **kwargs):
        super().__init__(app_ref, **kwargs)
        self.downloads = []
        self.current_download = None
        self.log_buffer = []
        self.is_downloading = False
        self.coordinator = None

    def get_screen_id(self) -> str:
        return "progress"

    def refresh_data(self) -> None:
        """Load progress data."""
        self.data["downloads"] = self.downloads
        self.data["current"] = self.current_download
        self.data["logs"] = self.log_buffer

    def get_content(self) -> Static:
        """Build the progress monitor content."""
        content = Static(id="content")
        content.render = self._render_progress
        return content

    def _render_progress(self) -> Panel:
        """Render the progress monitoring interface."""
        content_text = Text()

        # Title
        content_text.append("📈 Progress Monitor\n\n", style="bold cyan")

        if not self.is_downloading:
            content_text.append(
                "No active downloads.\n\n",
                style="yellow",
            )
            content_text.append(
                "Use the Download Manager [5] to queue and start downloads.\n",
                style="dim",
            )
            content_text.append(
                "Downloads will appear here when they start.\n\n",
                style="dim",
            )
            content_text.append(
                "Features:\n", style="bold cyan"
            )
            content_text.append(
                "• 3-step progress tracking (Ingest → Clean → Document)\n",
                style="cyan"
            )
            content_text.append(
                "• Real-time logs with detailed output\n",
                style="cyan"
            )
            content_text.append(
                "• Cancel button to abort downloads\n",
                style="cyan"
            )
            content_text.append(
                "• Background mode to continue browsing\n",
                style="cyan"
            )
            return Panel(
                content_text,
                title="Progress Monitor",
                border_style="cyan",
                expand=True,
            )

        # Current download
        if self.current_download:
            content_text.append(
                f"Current: {self.current_download['source']} → {self.current_download['indicator']}\n",
                style="bold green",
            )
            content_text.append("\n")

            # Progress bars for each step
            steps = [
                ("Ingest (Download)", self.current_download.get("ingest_progress", 0)),
                ("Clean (Transform)", self.current_download.get("clean_progress", 0)),
                ("Document (Metadata)", self.current_download.get("document_progress", 0)),
            ]

            for step_name, progress in steps:
                bar_length = 30
                filled = int((progress / 100) * bar_length)
                bar = "█" * filled + "░" * (bar_length - filled)
                content_text.append(f"{step_name}\n", style="cyan")
                content_text.append(
                    f"[{bar}] {progress}%\n\n",
                    style="green" if progress == 100 else "yellow",
                )

            # Time info
            elapsed = self.current_download.get("elapsed_time", 0)
            eta = self.current_download.get("eta", "calculating...")
            content_text.append(
                f"Elapsed: {elapsed}s | ETA: {eta}\n\n",
                style="dim",
            )

            # Controls
            content_text.append("─" * 70 + "\n", style="cyan")
            content_text.append(
                "[B] Run in Background | [C] Cancel Download | [P] Pause\n",
                style="yellow"
            )
            content_text.append("\n\n")

        # Logs section
        content_text.append("📋 Logs (latest first)\n", style="bold cyan")
        content_text.append("─" * 70 + "\n", style="cyan")

        if self.log_buffer:
            for log_entry in self.log_buffer[-20:]:  # Show last 20 logs
                timestamp = log_entry.get("timestamp", "")
                level = log_entry.get("level", "INFO")
                message = log_entry.get("message", "")

                level_style = {
                    "INFO": "cyan",
                    "SUCCESS": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                }.get(level, "white")

                content_text.append(
                    f"[{timestamp}] {level:8} {message}\n",
                    style=level_style,
                )
        else:
            content_text.append("No logs yet\n", style="dim")

        content_text.append("\n")
        content_text.append(
            "[↑↓] Scroll logs | [C] Clear logs | [E] Export\n",
            style="dim",
        )

        return Panel(
            content_text,
            title="Progress Monitor",
            border_style="cyan",
            expand=True,
        )

    def start_download(self, download_item: dict) -> None:
        """Start tracking a download."""
        self.is_downloading = True
        self.current_download = {
            **download_item,
            "ingest_progress": 0,
            "clean_progress": 0,
            "document_progress": 0,
            "elapsed_time": 0,
            "eta": "calculating...",
        }
        self.log_buffer = []
        self.add_log("INFO", "Download started")

    def add_log(self, level: str, message: str) -> None:
        """Add a log entry."""
        from datetime import datetime

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_buffer.append({
            "timestamp": timestamp,
            "level": level,
            "message": message,
        })
        # Keep only last 1000 logs
        if len(self.log_buffer) > 1000:
            self.log_buffer = self.log_buffer[-1000:]

    def update_step_progress(self, step: str, progress: int) -> None:
        """Update progress for a specific step."""
        if self.current_download:
            if step == "ingest":
                self.current_download["ingest_progress"] = progress
            elif step == "clean":
                self.current_download["clean_progress"] = progress
            elif step == "document":
                self.current_download["document_progress"] = progress

    def finish_download(self, success: bool = True) -> None:
        """Mark download as finished."""
        if success:
            self.add_log("SUCCESS", "Download completed successfully")
        else:
            self.add_log("ERROR", "Download failed")
        self.is_downloading = False
    def set_coordinator(self, coordinator: DownloadCoordinator) -> None:
        """Set the coordinator reference."""
        self.coordinator = coordinator

    def action_cancel_download(self) -> None:
        """Cancel ongoing download."""
        if self.coordinator and self.is_downloading:
            self.coordinator.cancel()
            self.is_downloading = False
            self.add_log("WARNING", "Download cancelled by user")

    def action_export_logs(self) -> None:
        """Export logs to file."""
        try:
            from datetime import datetime
            filename = f"download_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            filepath = Path.home() / "Downloads" / filename
            
            with open(filepath, "w") as f:
                for entry in self.log_buffer:
                    f.write(f"[{entry['timestamp']}] {entry['level']:8} {entry['message']}\n")
            
            self.add_log("SUCCESS", f"Logs exported to {filepath}")
        except Exception as e:
            self.add_log("ERROR", f"Failed to export logs: {str(e)}")
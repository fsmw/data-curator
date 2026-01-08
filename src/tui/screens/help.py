"""Help screen with keyboard shortcuts and documentation."""

from textual.widgets import Static
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from .base import BaseScreen


class HelpScreen(BaseScreen):
    """Display help and keyboard shortcuts."""

    def get_screen_id(self) -> str:
        return "help"

    def get_content(self) -> Static:
        """Build the help screen content."""
        content = Static(id="content")
        content.render = self._render_help
        return content

    def _render_help(self) -> Panel:
        """Render the help panel."""
        help_text = Text()

        # Global shortcuts
        help_text.append("⌨️  Global Keyboard Shortcuts\n\n", style="bold cyan")

        shortcuts = Table(title="Navigation", show_header=False, box=None)
        shortcuts.add_row("[1-7]", "Jump to screen")
        shortcuts.add_row("[Q]", "Quit application")
        shortcuts.add_row("[H]", "Show this help")
        shortcuts.add_row("[/]", "Open search")
        shortcuts.add_row("[Tab]", "Next field")
        shortcuts.add_row("[Shift+Tab]", "Previous field")
        shortcuts.add_row("[Esc]", "Back / Cancel")

        help_text.append(str(shortcuts) + "\n\n", style="cyan")

        # Screen shortcuts
        screens_shortcuts = Table(title="Screen Actions", show_header=False, box=None)
        screens_shortcuts.add_row("[1] Status", "View project overview")
        screens_shortcuts.add_row("[2] Browse Local", "View downloaded datasets")
        screens_shortcuts.add_row("[3] Browse Available", "Explore available data sources")
        screens_shortcuts.add_row("[4] Search", "Search indicators by keyword")
        screens_shortcuts.add_row("[5] Download", "Download new data")
        screens_shortcuts.add_row("[6] Progress", "Monitor active downloads")

        help_text.append(str(screens_shortcuts) + "\n\n", style="cyan")

        # Tips
        help_text.append("💡 Tips\n\n", style="bold green")
        help_text.append(
            "• Use the sidebar on the left to navigate between screens\n", style="green"
        )
        help_text.append(
            "• Keyboard shortcuts (1-7) provide quick access to main screens\n",
            style="green",
        )
        help_text.append(
            "• Press Enter/Space to select items in lists\n", style="green"
        )
        help_text.append(
            "• Arrow keys navigate lists and tree views\n", style="green"
        )

        return Panel(
            help_text,
            title="Help & Documentation",
            border_style="green",
            expand=True,
        )

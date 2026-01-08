"""Base screen class for all TUI screens."""

from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static
from rich.text import Text
from ..widgets.sidebar import SidebarNavigation


class BaseScreen(Screen):
    """Base class for all application screens."""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("h", "show_help", "Help"),
        ("/", "show_search", "Search"),
        ("m", "view_metadata", "Metadata"),
        ("d", "delete_dataset", "Delete"),
        ("1", "go_status", "Status"),
        ("2", "go_browse_local", "Local"),
        ("3", "go_browse_available", "Available"),
        ("4", "go_search", "Search"),
        ("5", "go_download", "Download"),
        ("6", "go_progress", "Progress"),
        ("7", "go_help", "Help"),
        ("tab", "focus_next", "Next"),
        ("shift+tab", "focus_previous", "Prev"),
        ("up", "handle_up", "Up"),
        ("down", "handle_down", "Down"),
        ("left", "handle_left", "Left"),
        ("right", "handle_right", "Right"),
    ]

    def __init__(self, app_ref=None, **kwargs):
        super().__init__(**kwargs)
        self.app_ref = app_ref
        self.data = {}
        self.focused_index = 0
        self.focusable_elements = []

    def compose(self):
        """Compose the screen layout with sidebar."""
        with Horizontal():
            yield SidebarNavigation(id="sidebar")
            with Vertical(id="main_content"):
                yield Header(show_clock=False)
                # Subclasses override this region
                yield self.get_content()
                yield Footer()

    def get_content(self) -> Static:
        """Get the main content widget. Override in subclasses."""
        content = Static("Screen content goes here")
        content.id = "content"
        return content

    def on_mount(self) -> None:
        """Initialize screen on mount."""
        self.refresh_data()
        self.update_sidebar()

    def refresh_data(self) -> None:
        """Refresh screen data. Override in subclasses."""
        pass

    def update_sidebar(self) -> None:
        """Update sidebar active indicator."""
        screen_id = self.get_screen_id()
        sidebar = self.query_one(SidebarNavigation)
        sidebar.update_active(screen_id)

    def update_display(self) -> None:
        """Update the display after state changes."""
        try:
            content = self.query_one("#content", Static)
            content.update()
        except Exception:
            pass

    def get_screen_id(self) -> str:
        """Get the ID of this screen. Override in subclasses."""
        return "unknown"

    def action_quit(self) -> None:
        """Handle quit action."""
        self.app.exit()

    def action_show_help(self) -> None:
        """Switch to help screen."""
        self.app.switch_screen("help")

    def action_show_search(self) -> None:
        """Switch to search screen."""
        self.app.switch_screen("search")

    def action_view_metadata(self) -> None:
        """View metadata. Override in subclasses if needed."""
        pass

    def action_delete_dataset(self) -> None:
        """Delete dataset. Override in subclasses if needed."""
        pass

    def action_focus_next(self) -> None:
        """Move focus to next element. Override in subclasses."""
        pass

    def action_focus_previous(self) -> None:
        """Move focus to previous element. Override in subclasses."""
        pass

    def action_handle_up(self) -> None:
        """Handle up arrow key. Override in subclasses."""
        pass

    def action_handle_down(self) -> None:
        """Handle down arrow key. Override in subclasses."""
        pass

    def action_handle_left(self) -> None:
        """Handle left arrow key. Override in subclasses."""
        pass

    def action_handle_right(self) -> None:
        """Handle right arrow key. Override in subclasses."""
        pass

    def action_go_search(self) -> None:
        """Go to search screen."""
        if hasattr(self.app, "switch_screen"):
            self.app.switch_screen("search")

    def action_go_download(self) -> None:
        """Go to download screen."""
        if hasattr(self.app, "switch_screen"):
            self.app.switch_screen("download")

    def action_go_progress(self) -> None:
        """Go to progress screen."""
        if hasattr(self.app, "switch_screen"):
            self.app.switch_screen("progress")

    def action_go_help(self) -> None:
        """Go to help screen."""
        if hasattr(self.app, "switch_screen"):
            self.app.switch_screen("help")

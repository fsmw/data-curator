"""Main Textual application for MISES Data Curation Tool."""

from textual.app import ComposeResult, App
from textual.containers import Container
from textual.theme import Theme
from textual.screen import Screen
from .screens import (
    StatusScreen,
    HelpScreen,
    BrowseLocalScreen,
    BrowseAvailableScreen,
    SearchScreen,
    DownloadScreen,
    ProgressScreen,
)
from .config import TITLE, SUBTITLE


class MisesApp(App):
    """Main TUI application for MISES Data Curation Tool."""

    TITLE = TITLE
    SUB_TITLE = SUBTITLE

    CSS = """
    Screen {
        background: $surface;
        color: $text;
    }

    Header {
        background: $primary 30%;
        color: $text;
        dock: top;
    }

    Footer {
        background: $primary 30%;
        color: $text;
        dock: bottom;
    }

    #main_content {
        width: 1fr;
        height: 1fr;
    }

    #content {
        width: 1fr;
        height: 1fr;
        border: solid $primary;
    }
    """

    SCREENS = {
        "status": StatusScreen,
        "help": HelpScreen,
        "browse_local": BrowseLocalScreen,
        "browse_available": BrowseAvailableScreen,
        "search": SearchScreen,
        "download": DownloadScreen,
        "progress": ProgressScreen,
    }

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("h", "show_help", "Help"),
    ]

    def on_mount(self) -> None:
        """Initialize the application on mount."""
        # Use call_later to switch screens after app is fully mounted
        # This prevents IndexError in result callback handling
        self.call_later(self._init_screens)

    def _init_screens(self) -> None:
        """Initialize screen switching safely."""
        try:
            # Get current screen (the default screen)
            if len(self._screen_stack) > 0:
                current_screen = self._screen_stack[-1]
                # Ensure result callbacks list is not empty
                if hasattr(current_screen, '_result_callbacks'):
                    if len(current_screen._result_callbacks) == 0:
                        # Add a dummy callback to prevent pop from empty list
                        current_screen._result_callbacks.append(None)
            
            # Now switch to status screen
            self.switch_screen("status")
            
            # Initialize coordinator sharing between screens
            self._setup_coordinator_sharing()
        except Exception as e:
            # Fallback: if something goes wrong, just continue
            print(f"Warning: Could not initialize screens: {e}")

    def _setup_coordinator_sharing(self) -> None:
        """Share coordinator between Download and Progress screens."""
        try:
            download_screen = self.get_screen("download")
            progress_screen = self.get_screen("progress")
            
            if hasattr(download_screen, "coordinator"):
                progress_screen.set_coordinator(download_screen.coordinator)
        except Exception as e:
            print(f"Warning: Could not setup coordinator sharing: {e}")


    def action_show_help(self) -> None:
        """Navigate to help screen."""
        self.switch_screen("help")

"""Navigation sidebar widget for the TUI."""

from textual.widgets import Static
from textual.containers import Container
from textual.reactive import reactive
from rich.text import Text
from rich.panel import Panel


class SidebarNavigation(Static):
    """Navigation sidebar with menu items."""

    can_focus = True  # Allow sidebar to receive keyboard input

    BINDINGS = [
        ("up", "move_up", "Up"),
        ("down", "move_down", "Down"),
        ("enter", "select_item", "Select"),
    ]

    DEFAULT_CSS = """
    SidebarNavigation {
        width: 22;
        background: $primary 5%;
        border-right: solid $primary;
        overflow: hidden;
    }

    SidebarNavigation:focus {
        border-right: solid $accent;
    }

    SidebarNavigation > Container {
        height: 100%;
        overflow-y: auto;
    }
    """

    MENU_ITEMS = [
        ("📊 Status", "status", "5"),
        ("📂 Browse Local", "browse_local", "2"),
        ("📥 Browse Available", "browse_available", "3"),
        ("🔍 Search", "search", "4"),
        ("⬇️  Download", "download", "5"),
        ("ℹ️ Help", "help", "7"),
    ]

    active_screen = reactive("status")
    selected_index = reactive(0)

    def render(self) -> Panel:
        """Render the sidebar menu."""
        menu_text = Text()
        menu_text.append("\n Navigation\n", style="bold cyan")
        menu_text.append(" " + "━" * 18 + "\n", style="dim cyan")

        for idx, (label, screen_id, key) in enumerate(self.MENU_ITEMS):
            is_active = self.active_screen == screen_id
            is_selected = idx == self.selected_index
            
            # Determine style and prefix
            if is_active and is_selected:
                style = "bold white on blue"
                prefix = "▶ "
            elif is_selected:
                style = "bold white on blue"
                prefix = "▶ "
            elif is_active:
                style = "bold white on blue"
                prefix = "  "
            else:
                style = "cyan"
                prefix = "  "
            
            menu_text.append(f"{prefix}{label}\n", style=style)

        menu_text.append(" " + "━" * 18 + "\n", style="dim cyan")
        menu_text.append(f"\n [Active: {self.active_screen}]\n\n", style="dim")

        # Add help text
        menu_text.append("Keys:\n", style="bold dim cyan")
        menu_text.append("↑↓ Navigate | Enter=Go | Q=Quit\n", style="dim")

        return Panel(
            menu_text,
            title="NAVIGATION",
            style="cyan",
            expand=False,
        )

    def update_active(self, screen_id: str) -> None:
        """Update the active screen indicator."""
        self.active_screen = screen_id

    def action_move_up(self) -> None:
        """Move selection up and switch to that screen."""
        self.selected_index = (self.selected_index - 1) % len(self.MENU_ITEMS)
        self.action_select_item()

    def action_move_down(self) -> None:
        """Move selection down and switch to that screen."""
        self.selected_index = (self.selected_index + 1) % len(self.MENU_ITEMS)
        self.action_select_item()

    def action_select_item(self) -> None:
        """Navigate to the selected menu item."""
        if 0 <= self.selected_index < len(self.MENU_ITEMS):
            _, screen_id, _ = self.MENU_ITEMS[self.selected_index]
            self.app.switch_screen(screen_id)

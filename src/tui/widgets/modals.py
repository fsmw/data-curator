"""Modal dialogs and popup widgets for the TUI.

This module provides modal dialogs for:
- Confirmation dialogs (delete, destructive operations)
- Metadata viewing (dataset details)
- Input dialogs (search, filters)
- Alert dialogs (notifications)
"""

from typing import Callable, Optional
from textual.widgets import Static, Button, Input, TextArea
from textual.containers import Horizontal, Vertical, Container
from textual.binding import Binding
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.console import RenderableType


class ModalBase(Container):
    """Base class for modal dialogs."""

    BINDINGS = [
        Binding("escape", "close", "Close", show=True),
    ]

    def __init__(self, title: str = "Dialog", width: int = 60, height: int = 20):
        super().__init__()
        self.modal_title = title
        self.modal_width = width
        self.modal_height = height
        self.styles.width = width
        self.styles.height = height
        self.styles.border = ("solid", "cyan")
        self.styles.align = ("center", "middle")

    def action_close(self) -> None:
        """Close the modal."""
        self.remove()


class ConfirmDialog(ModalBase):
    """Confirmation dialog for destructive operations.
    
    Displays a confirmation message with Yes/No buttons.
    """

    def __init__(
        self,
        title: str,
        message: str,
        on_confirm: Optional[Callable] = None,
        on_cancel: Optional[Callable] = None,
    ):
        super().__init__(title=title, width=70, height=15)
        self.message = message
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel

    def compose(self):
        """Compose dialog with message and buttons."""
        with Vertical():
            yield Static(self.message, classes="modal-message")
            with Horizontal(classes="modal-buttons"):
                yield Button("Yes, Delete", id="confirm-btn", variant="error")
                yield Button("Cancel", id="cancel-btn", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "confirm-btn":
            if self.on_confirm:
                self.on_confirm()
        elif event.button.id == "cancel-btn":
            if self.on_cancel:
                self.on_cancel()
        self.remove()


class MetadataModal(ModalBase):
    """Modal for viewing dataset metadata.
    
    Displays formatted metadata about a dataset with
    scrollable content area.
    """

    def __init__(self, title: str, content: str):
        super().__init__(title=title, width=80, height=25)
        self.modal_content = content

    def compose(self):
        """Compose modal with metadata content."""
        with Vertical():
            # Title
            yield Static(self.modal_title, classes="modal-header")
            
            # Content area (scrollable)
            content_text = Text(self.modal_content)
            yield Static(content_text, classes="modal-content")
            
            # Footer with close hint
            yield Static("[Esc] Close", classes="modal-footer")

    def on_mount(self) -> None:
        """Set up modal styling."""
        self.styles.border = ("solid", "cyan")
        self.styles.background = "$boost"


class InputDialog(ModalBase):
    """Input dialog for user input.
    
    Accepts single-line text input for filtering,
    searching, or other user queries.
    """

    def __init__(
        self,
        title: str,
        prompt: str,
        default_value: str = "",
        on_submit: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(title=title, width=70, height=12)
        self.prompt = prompt
        self.default_value = default_value
        self.on_submit = on_submit
        self.input_field: Optional[Input] = None

    def compose(self):
        """Compose dialog with input field and buttons."""
        with Vertical():
            yield Static(self.prompt, classes="modal-label")
            self.input_field = Input(value=self.default_value)
            yield self.input_field
            
            with Horizontal(classes="modal-buttons"):
                yield Button("Submit", id="submit-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "submit-btn":
            if self.input_field and self.on_submit:
                self.on_submit(self.input_field.value)
        self.remove()

    def on_mount(self) -> None:
        """Auto-focus input field."""
        if self.input_field:
            self.input_field.focus()


class AlertDialog(ModalBase):
    """Alert dialog for notifications and messages.
    
    Shows a message with an OK button.
    """

    def __init__(self, title: str, message: str, alert_type: str = "info"):
        """
        Initialize alert dialog.
        
        Args:
            title: Dialog title
            message: Alert message
            alert_type: Type of alert - 'info', 'warning', 'error'
        """
        super().__init__(title=title, width=70, height=12)
        self.alert_message = message
        self.alert_type = alert_type
        
        # Set border color based on alert type
        if alert_type == "error":
            self.styles.border = ("solid", "red")
        elif alert_type == "warning":
            self.styles.border = ("solid", "yellow")
        else:
            self.styles.border = ("solid", "blue")

    def compose(self):
        """Compose alert dialog."""
        with Vertical():
            yield Static(self.alert_message, classes="modal-message")
            with Horizontal(classes="modal-buttons"):
                yield Button("OK", id="ok-btn", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle OK button."""
        self.remove()


class FilterDialog(ModalBase):
    """Filter dialog for data filtering options.
    
    Allows user to select filter criteria.
    """

    def __init__(
        self,
        title: str,
        options: list[str],
        on_filter: Optional[Callable[[list[str]], None]] = None,
    ):
        """
        Initialize filter dialog.
        
        Args:
            title: Dialog title
            options: List of filter options to display
            on_filter: Callback with selected filters
        """
        super().__init__(title=title, width=60, height=20)
        self.filter_options = options
        self.on_filter = on_filter
        self.selected_filters: set[str] = set()

    def compose(self):
        """Compose filter selection dialog."""
        with Vertical():
            yield Static("Select filters:", classes="modal-label")
            
            # Create checkboxes for each option
            for option in self.filter_options:
                with Horizontal():
                    yield Static(f"[ ] {option}", id=f"filter-{option}")
            
            with Horizontal(classes="modal-buttons"):
                yield Button("Apply", id="apply-btn", variant="primary")
                yield Button("Clear", id="clear-btn", variant="default")
                yield Button("Cancel", id="cancel-btn", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "apply-btn":
            if self.on_filter:
                self.on_filter(list(self.selected_filters))
        elif event.button.id == "clear-btn":
            self.selected_filters.clear()
        self.remove()


class ProgressDialog(ModalBase):
    """Modal for showing progress of operations.
    
    Displays progress bar and status messages.
    """

    def __init__(self, title: str, message: str = "Processing..."):
        super().__init__(title=title, width=70, height=10)
        self.status_message = message
        self.progress = 0

    def compose(self):
        """Compose progress dialog."""
        with Vertical():
            yield Static(self.status_message, id="progress-msg")
            yield Static("█████░░░░░░░░░░░░░░ 25%", id="progress-bar")

    def update_progress(self, current: int, total: int) -> None:
        """Update progress bar.
        
        Args:
            current: Current progress count
            total: Total count
        """
        self.progress = (current / total) * 100 if total > 0 else 0
        
        # Create progress bar
        filled = int(20 * (self.progress / 100))
        bar = "█" * filled + "░" * (20 - filled)
        
        progress_bar = self.query_one("#progress-bar", Static)
        progress_bar.update(f"{bar} {self.progress:.0f}%")

    def set_message(self, message: str) -> None:
        """Update status message.
        
        Args:
            message: New status message
        """
        msg_widget = self.query_one("#progress-msg", Static)
        msg_widget.update(message)


class SelectDialog(ModalBase):
    """Selection dialog for choosing from a list.
    
    Allows user to select one item from a list.
    """

    def __init__(
        self,
        title: str,
        items: list[str],
        on_select: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize selection dialog.
        
        Args:
            title: Dialog title
            items: List of items to choose from
            on_select: Callback with selected item
        """
        super().__init__(title=title, width=60, height=min(20, len(items) + 5))
        self.items = items
        self.on_select = on_select
        self.selected_index = 0

    def compose(self):
        """Compose selection dialog."""
        with Vertical():
            for i, item in enumerate(self.items):
                marker = "→" if i == self.selected_index else " "
                yield Static(f"{marker} {item}", id=f"select-{i}")
            
            with Horizontal(classes="modal-buttons"):
                yield Button("Select", id="select-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "select-btn":
            if self.on_select:
                self.on_select(self.items[self.selected_index])
        self.remove()

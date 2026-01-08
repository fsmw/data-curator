"""Color theme and styling for the TUI."""

# Primary colors
PRIMARY = "cyan"
SUCCESS = "green"
WARNING = "yellow"
ERROR = "red"
SECONDARY = "bright_blue"

# Neutral colors
DARK_BG = "#1e1e1e"
LIGHT_TEXT = "white"
DIM_TEXT = "gray"
ACCENT = "bright_cyan"

# Status colors
STATUS_READY = "green"
STATUS_PENDING = "yellow"
STATUS_WORKING = "bright_cyan"
STATUS_ERROR = "red"

# Theme definition
THEME = {
    "primary": PRIMARY,
    "secondary": SECONDARY,
    "success": SUCCESS,
    "warning": WARNING,
    "error": ERROR,
    "accent": ACCENT,
}

# CSS variables for Textual
CSS_COLORS = f"""
primary: {PRIMARY};
secondary: {SECONDARY};
success: {SUCCESS};
warning: {WARNING};
error: {ERROR};
accent: {ACCENT};
"""

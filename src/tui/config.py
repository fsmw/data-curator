"""TUI configuration settings."""

from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "02_Datasets_Limpios"
METADATA_DIR = PROJECT_ROOT / "03_Metadata_y_Notas"
RAW_DATA_DIR = PROJECT_ROOT / "01_Raw_Data_Bank"
CONFIG_FILE = PROJECT_ROOT / "config.yaml"
INDICATORS_FILE = PROJECT_ROOT / "indicators.yaml"

# Window settings
MIN_WIDTH = 80
MIN_HEIGHT = 24
DEFAULT_SCREEN = "status"

# Navigation
DEFAULT_SIDEBAR_WIDTH = 20
DEFAULT_CONTENT_WIDTH = 60

# Behavior
CACHE_TTL_SECONDS = 3600  # 1 hour
MAX_PREVIEW_LINES = 100
REFRESH_RATE = 2.0  # Updates per second

# Messages
TITLE = "📊 MISES Data Curation Tool"
SUBTITLE = "v1.0.0 - Economic Data Manager"

# Screen transitions
SCREENS = {
    "1": "status",
    "2": "browse_local",
    "3": "browse_available",
    "4": "search",
    "5": "download",
    "6": "progress",
    "7": "help",
}

# Keyboard shortcuts
GLOBAL_SHORTCUTS = {
    "q": "quit",
    "h": "help",
    "slash": "search",
    "1": "go_status",
    "2": "go_browse_local",
    "3": "go_browse_available",
    "4": "go_search",
    "5": "go_download",
    "6": "go_progress",
    "7": "go_help",
}

# Textual TUI removed
# The Textual TUI module is deprecated. Importing this module will raise a RuntimeError
# advising users to use the CLI or Web server instead. Files are retained for history.

raise RuntimeError(
    "The Textual TUI has been removed from this distribution. "
    "Use the CLI (python -m src.cli) or the Web server (python -m src.web) instead."
)

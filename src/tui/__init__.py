"""MISES Data Curation Tool - Text User Interface (TUI).

The TUI has been removed from this distribution. Importing this package will
provide a helper function that prints an informational message.
"""

__version__ = "0.0.0-deprecated"
__author__ = "MISES Team"


def show_removed_message():
    print('The Textual TUI has been removed from this distribution.')
    print('Use the CLI: python -m src.cli')
    print('Or the Web server: python -m src.web')

__all__ = ["show_removed_message"]

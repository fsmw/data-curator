"""
Entry point to run the TUI. Use this command:

    python -m src.tui

This will launch the MISES Data Curation Tool TUI.
"""

if __name__ == "__main__":
    from src.tui import MisesApp
    app = MisesApp()
    app.run()

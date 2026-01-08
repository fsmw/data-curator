"""Entry point for running the TUI from command line."""

from .app import MisesApp


def main():
    """Run the TUI application."""
    app = MisesApp()
    app.run()


if __name__ == "__main__":
    main()

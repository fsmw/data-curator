"""Entry point for running the web interface."""

import os
from waitress import serve

from . import create_app


def _print_startup(url: str) -> None:
    print("\n" + "=" * 60)
    print("🌐 Mises Data Curator - Web Interface")
    print("=" * 60)
    print(f"\nStarting server at {url}")
    print("Use CTRL+C to quit\n")


if __name__ == "__main__":
    app = create_app()
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_RUN_PORT", "5000"))

    url = f"http://{host}:{port}"
    _print_startup(url)

    serve(app, host=host, port=port)

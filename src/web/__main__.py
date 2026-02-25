"""Entry point for running the web interface."""

import os

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
    jupyter_enabled = os.getenv("JUPYTER_ENABLE", "0").strip().lower() in {"1", "true", "yes", "on"}

    url = f"http://{host}:{port}"
    _print_startup(url)

    if jupyter_enabled:
        try:
            from gevent.pywsgi import WSGIServer
            from geventwebsocket.handler import WebSocketHandler

            WSGIServer((host, port), app, handler_class=WebSocketHandler).serve_forever()
        except ImportError:
            from waitress import serve

            print("Warning: gevent/gevent-websocket not installed; WebSocket proxy disabled.")
            serve(app, host=host, port=port)
    else:
        from waitress import serve

        serve(app, host=host, port=port)

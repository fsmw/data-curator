"""Flask proxy endpoints for embedded Jupyter routes."""

from __future__ import annotations

import threading
from typing import Dict, Optional

import requests
from flask import Blueprint, Flask, Response, current_app, request

try:
    from flask_sock import Sock
except ImportError:  # pragma: no cover - optional dependency in some environments
    Sock = None  # type: ignore[assignment]

try:
    import websocket
except ImportError:  # pragma: no cover - optional dependency in some environments
    websocket = None  # type: ignore[assignment]


HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def _filter_headers(headers: Dict[str, str]) -> Dict[str, str]:
    return {k: v for k, v in headers.items() if k.lower() not in HOP_BY_HOP_HEADERS}


def _build_upstream_ws_url(*, path: str, query_string: bytes, port: int, jupyter_base_path: str = "/jupyter/") -> str:
    """Build upstream WebSocket URL using manager's jupyter_base_path."""
    upstream_path = f"{jupyter_base_path.rstrip('/')}/{path}" if path else jupyter_base_path
    upstream_url = f"ws://127.0.0.1:{port}{upstream_path}"
    if query_string:
        upstream_url = f"{upstream_url}?{query_string.decode('utf-8')}"
    return upstream_url


def _prefix_location(location: str, script_root: str) -> str:
    if not script_root or not location.startswith("/"):
        return location
    if location.startswith("//"):
        return location
    if location.startswith(script_root + "/") or location == script_root:
        return location
    return f"{script_root.rstrip('/')}{location}"


def _websocket_closed_errors() -> tuple[type[BaseException], ...]:
    if websocket is None:
        return (OSError, ValueError)
    ws_exc = getattr(websocket, "_exceptions", None)
    closed_error = getattr(ws_exc, "WebSocketConnectionClosedException", None)
    if isinstance(closed_error, type) and issubclass(closed_error, BaseException):
        return (closed_error, OSError, ValueError)
    return (OSError, ValueError)


def _proxy_websocket_stream(manager: object, downstream_ws: object, path: str, query_string: bytes) -> None:
    if websocket is None:
        raise RuntimeError("websocket-client dependency is not installed")

    upstream_headers = _filter_headers(dict(request.headers))
    upstream_headers["Host"] = f"127.0.0.1:{manager.port}"
    upstream_headers["Origin"] = manager.base_url
    jupyter_base = getattr(manager, "jupyter_base_path", "/jupyter/")
    upstream_url = _build_upstream_ws_url(path=path, query_string=query_string, port=manager.port, jupyter_base_path=jupyter_base)
    header_list = [f"{key}: {value}" for key, value in upstream_headers.items()]
    upstream_ws = websocket.create_connection(
        upstream_url,
        header=header_list,
        timeout=30,
        enable_multithread=True,
    )
    closed_errors = _websocket_closed_errors()
    stop_event = threading.Event()

    def upstream_to_downstream() -> None:
        try:
            while not stop_event.is_set():
                message = upstream_ws.recv()
                if message is None:
                    break
                downstream_ws.send(message)
        except closed_errors:
            pass
        finally:
            stop_event.set()

    upstream_thread = threading.Thread(target=upstream_to_downstream, daemon=True)
    upstream_thread.start()
    try:
        while True:
            message = downstream_ws.receive()
            if message is None:
                break
            upstream_ws.send(message)
    except closed_errors:
        pass
    finally:
        stop_event.set()
        upstream_ws.close()
        close_fn = getattr(downstream_ws, "close", None)
        if callable(close_fn):
            close_fn()


def create_jupyter_proxy_blueprint() -> Blueprint:
    proxy_bp = Blueprint("jupyter_proxy", __name__)

    @proxy_bp.route("/jupyter/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    @proxy_bp.route("/jupyter/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    def proxy(path: str) -> Response:
        manager = current_app.extensions.get("jupyter_manager")
        if not manager or not manager.enabled:
            return Response("Jupyter integration disabled", status=503)

        if request.headers.get("Upgrade", "").lower() == "websocket":
            if Sock is None:
                return Response("WebSocket proxy dependency missing: install flask-sock", status=501)
            return Response("WebSocket upgrade must use the WS route", status=426)

        # Use manager's jupyter_base_path (includes app prefix like /misesdata/jupyter/)
        jupyter_base = getattr(manager, "jupyter_base_path", "/jupyter/")
        upstream_path = f"{jupyter_base.rstrip('/')}/{path}" if path else jupyter_base
        upstream_url = f"{manager.base_url}{upstream_path}"
        if request.query_string:
            upstream_url = f"{upstream_url}?{request.query_string.decode('utf-8')}"

        headers = _filter_headers(dict(request.headers))
        headers["Host"] = f"127.0.0.1:{manager.port}"
        body = request.get_data() if request.method in {"POST", "PUT", "PATCH"} else None

        try:
            upstream = requests.request(
                method=request.method,
                url=upstream_url,
                headers=headers,
                data=body,
                cookies=request.cookies,
                allow_redirects=False,
                timeout=30,
                stream=True,
            )
        except requests.RequestException as exc:
            return Response(f"Jupyter upstream error: {exc}", status=502)

        response_headers = _filter_headers(dict(upstream.headers))
        location = response_headers.get("Location")
        if location:
            response_headers["Location"] = _prefix_location(location, request.script_root or "")
        content = upstream.content
        return Response(content, status=upstream.status_code, headers=response_headers)

    return proxy_bp


def register_jupyter_websocket_proxy(app: Flask) -> Optional[Sock]:
    if Sock is None:
        return None

    sock = Sock(app)

    @sock.route("/jupyter/", defaults={"path": ""})
    @sock.route("/jupyter/<path:path>")
    def proxy_websocket(downstream_ws: object, path: str) -> None:
        if request.headers.get("Upgrade", "").lower() != "websocket":
            return
        manager = current_app.extensions.get("jupyter_manager")
        if not manager or not manager.enabled:
            close_fn = getattr(downstream_ws, "close", None)
            if callable(close_fn):
                close_fn()
            return
        _proxy_websocket_stream(
            manager=manager,
            downstream_ws=downstream_ws,
            path=path,
            query_string=request.query_string,
        )

    return sock

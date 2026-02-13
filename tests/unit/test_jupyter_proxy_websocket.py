from types import SimpleNamespace

from src.web import jupyter_proxy


def test_build_upstream_ws_url_with_query():
    url = jupyter_proxy._build_upstream_ws_url(
        path="api/kernels/123/channels",
        query_string=b"session_id=abc",
        port=8888,
    )
    assert url == "ws://127.0.0.1:8888/jupyter/api/kernels/123/channels?session_id=abc"


def test_prefix_location_adds_script_root():
    out = jupyter_proxy._prefix_location("/jupyter/lab", "/misesdata")
    assert out == "/misesdata/jupyter/lab"


def test_proxy_websocket_stream_relays_messages(monkeypatch):
    class FakeUpstreamSocket:
        def __init__(self):
            self.incoming = ["from-upstream", None]
            self.sent = []
            self.closed = False

        def recv(self):
            return self.incoming.pop(0)

        def send(self, message):
            self.sent.append(message)

        def close(self):
            self.closed = True

    class FakeDownstreamSocket:
        def __init__(self):
            self.incoming = ["from-downstream", None]
            self.sent = []
            self.closed = False

        def receive(self):
            return self.incoming.pop(0)

        def send(self, message):
            self.sent.append(message)

        def close(self):
            self.closed = True

    upstream = FakeUpstreamSocket()
    downstream = FakeDownstreamSocket()

    class FakeWebSocketModule:
        _exceptions = SimpleNamespace(WebSocketConnectionClosedException=RuntimeError)

        @staticmethod
        def create_connection(*args, **kwargs):
            return upstream

    monkeypatch.setattr(jupyter_proxy, "websocket", FakeWebSocketModule)

    manager = SimpleNamespace(port=8888, base_url="http://127.0.0.1:8888")
    with jupyter_proxy.Flask(__name__).test_request_context(
        "/jupyter/api/kernels/123/channels?session_id=abc",
        headers={"Upgrade": "websocket"},
    ):
        jupyter_proxy._proxy_websocket_stream(
            manager=manager,
            downstream_ws=downstream,
            path="api/kernels/123/channels",
            query_string=b"session_id=abc",
        )

    assert upstream.sent == ["from-downstream"]
    assert downstream.sent == ["from-upstream"]
    assert upstream.closed is True
    assert downstream.closed is True

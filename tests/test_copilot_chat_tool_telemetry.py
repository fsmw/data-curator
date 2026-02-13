import json


class _FakeAgent:
    async def chat_stream(self, message, session_id=None, model=None):
        yield {
            "status": "success",
            "session_id": session_id or "s1",
            "done": False,
            "fallback_used": True,
            "fallback_tool_use": {"name": "list_available_tools", "input": {"include_parameters": False}},
        }
        yield {
            "status": "success",
            "session_id": session_id or "s1",
            "done": False,
            "tool_use": {"name": "trend_analyzer", "input": {"dataset_id": 1}},
        }
        yield {
            "status": "success",
            "session_id": session_id or "s1",
            "done": False,
            "tool_result": {"status": "success"},
        }
        yield {
            "status": "success",
            "session_id": session_id or "s1",
            "done": True,
            "tools_called": ["trend_analyzer", "convergence_analyzer"],
        }


def _parse_sse_payload(raw_bytes: bytes):
    events = []
    for line in raw_bytes.decode("utf-8").splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: ") :]))
    return events


def test_copilot_stream_emits_tool_telemetry(client, auth_user, monkeypatch):
    from src.web.api import copilot as copilot_api

    monkeypatch.setattr(copilot_api, "create_copilot_agent", lambda: _FakeAgent())
    monkeypatch.setattr(copilot_api, "COPILOT_AVAILABLE", True)

    resp = client.post(
        "/api/copilot/stream",
        json={"message": "analiza mis datasets", "session_id": "sess-1"},
    )
    assert resp.status_code == 200

    events = _parse_sse_payload(resp.data)
    assert any("fallback_tool_use" in e for e in events)
    assert any(e.get("tool_use", {}).get("name") == "trend_analyzer" for e in events)
    done = [e for e in events if e.get("done") is True]
    assert done
    assert "trend_analyzer" in done[-1].get("tools_called", [])

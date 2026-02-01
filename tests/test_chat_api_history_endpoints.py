import os
import tempfile
import shutil
import json
import pytest
from pathlib import Path
from src.web import create_app
from src.chat_history import ChatHistory


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Create app and test client
    app = create_app()
    app.config["TESTING"] = True

    # Ensure .chat_history is created in tmp_path for isolation
    hist_root = tmp_path / "chat_history_root"
    hist_root.mkdir()

    # Monkeypatch _get_history_store to point to our tmp path by forcing session value
    def _get_history_store_override():
        # Use a fixed user id dir inside tmp_path
        user_dir = hist_root / "testuser"
        return ChatHistory(user_dir)

    # Patch the function in routes module
    import src.web.routes as routes_mod

    monkeypatch.setattr(routes_mod, "_get_history_store", _get_history_store_override)

    with app.test_client() as client:
        yield client


def test_history_endpoints_crud(client):
    # Start with listing (empty)
    resp = client.get('/api/chat/history')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'success'
    assert isinstance(data['history'], list)

    # Create a chat via /api/chat (we'll pass a message and rely on patched history store)
    payload = {
        "message": "Test message for history",
        "conversation_history": [{"role":"user","content":"Test message for history"}],
        "provider": "ollama",
        "model": "gpt-oss:1b"
    }

    resp = client.post('/api/chat', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'success'
    history_id = data.get('history_id')
    assert history_id

    # List again should include the new entry
    resp = client.get('/api/chat/history')
    data = resp.get_json()
    assert any(h['id'] == history_id for h in data['history'])

    # Get the session
    resp = client.get(f'/api/chat/history/{history_id}')
    assert resp.status_code == 200
    d = resp.get_json()
    assert d['status'] == 'success'
    session = d['session']
    assert session['id'] == history_id

    # Rename
    resp = client.post(f'/api/chat/history/{history_id}/rename', data=json.dumps({"title":"Renamed"}), content_type='application/json')
    assert resp.status_code == 200
    d = resp.get_json()
    assert d['status'] == 'success'

    # Verify rename in list
    resp = client.get('/api/chat/history')
    d = resp.get_json()
    assert any(h['id'] == history_id and h['title'] == 'Renamed' for h in d['history'])

    # Delete
    resp = client.delete(f'/api/chat/history/{history_id}/delete')
    assert resp.status_code == 200
    d = resp.get_json()
    assert d['status'] == 'success'

    # Verify deleted
    resp = client.get(f'/api/chat/history/{history_id}')
    assert resp.status_code == 404

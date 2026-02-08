def test_copilot_threads_create_and_list(client, auth_user):
    resp = client.post("/api/copilot/threads")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    thread = data["thread"]
    assert thread["id"]
    assert thread["user_id"]
    assert thread["title"] == "New Analysis"

    resp = client.get("/api/copilot/threads")
    data = resp.get_json()
    assert any(t["id"] == thread["id"] for t in data["threads"])


def test_copilot_threads_update_and_delete(client, auth_user):
    create = client.post("/api/copilot/threads")
    thread_id = create.get_json()["thread"]["id"]

    payload = {
        "title": "My Thread",
        "messages": [{"role": "user", "content": "Hi"}],
        "charts": [{"id": "c1", "title": "Chart"}],
        "session_id": "session-123",
        "last_message": "Hi",
    }
    resp = client.put(f"/api/copilot/threads/{thread_id}", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["thread"]["last_message"] == "Hi"

    resp = client.get("/api/copilot/threads")
    data = resp.get_json()
    assert any(t["title"] == "My Thread" for t in data["threads"])

    resp = client.delete(f"/api/copilot/threads/{thread_id}")
    assert resp.status_code == 200


def test_copilot_threads_update_rejects_invalid_messages(client, auth_user):
    create = client.post("/api/copilot/threads")
    thread_id = create.get_json()["thread"]["id"]

    resp = client.put(
        f"/api/copilot/threads/{thread_id}",
        json={"messages": "not-a-list"},
    )

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert data["message"] == "Invalid messages payload"


def test_copilot_threads_update_rejects_invalid_charts(client, auth_user):
    create = client.post("/api/copilot/threads")
    thread_id = create.get_json()["thread"]["id"]

    resp = client.put(
        f"/api/copilot/threads/{thread_id}",
        json={"charts": "not-a-list"},
    )

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert data["message"] == "Invalid charts payload"


def test_copilot_threads_user_scope(client, auth_user, other_user, login):
    create = client.post("/api/copilot/threads")
    thread_id = create.get_json()["thread"]["id"]

    login("otheruser", "otherpass")
    resp = client.put(f"/api/copilot/threads/{thread_id}", json={"title": "Nope"})
    assert resp.status_code == 404


def test_copilot_threads_user_scope_delete(client, auth_user, other_user, login):
    create = client.post("/api/copilot/threads")
    thread_id = create.get_json()["thread"]["id"]

    login("otheruser", "otherpass")
    resp = client.delete(f"/api/copilot/threads/{thread_id}")
    assert resp.status_code == 404


def test_copilot_threads_clear(client, auth_user):
    client.post("/api/copilot/threads")
    client.post("/api/copilot/threads")

    resp = client.post("/api/copilot/threads/clear")
    assert resp.status_code == 200

    resp = client.get("/api/copilot/threads")
    data = resp.get_json()
    assert data["threads"] == []

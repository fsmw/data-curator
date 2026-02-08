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
    }
    resp = client.put(f"/api/copilot/threads/{thread_id}", json=payload)
    assert resp.status_code == 200

    resp = client.get("/api/copilot/threads")
    data = resp.get_json()
    assert any(t["title"] == "My Thread" for t in data["threads"])

    resp = client.delete(f"/api/copilot/threads/{thread_id}")
    assert resp.status_code == 200


def test_copilot_threads_user_scope(client, auth_user, other_user):
    create = client.post("/api/copilot/threads")
    thread_id = create.get_json()["thread"]["id"]

    other_user.login(client)
    resp = client.put(f"/api/copilot/threads/{thread_id}", json={"title": "Nope"})
    assert resp.status_code == 404

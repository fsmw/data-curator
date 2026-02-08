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

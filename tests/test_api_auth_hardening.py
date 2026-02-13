def test_datasets_versions_requires_auth(client):
    resp = client.get("/api/datasets/versions?identifier=test")
    assert resp.status_code in (302, 401)


def test_copilot_chat_requires_auth(client):
    resp = client.post("/api/copilot/chat", json={"message": "hello"})
    assert resp.status_code in (302, 401)


def test_llm_models_allowlist_for_authenticated_user(client, auth_user):
    resp = client.get("/api/llm/models")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["status"] == "success"
    assert payload["models"] == [
        "gpt-5-mini",
        "claude-haiku-4.5",
        "gemini-3-flash-preview",
        "gpt-4o",
        "gpt-4.1",
    ]


def test_status_page_requires_auth(client):
    resp = client.get("/status")
    assert resp.status_code in (302, 401)


def test_status_page_authenticated(client, auth_user):
    resp = client.get("/status")
    assert resp.status_code == 200


def test_compare_endpoint_requires_auth(client):
    resp = client.get("/api/compare/data")
    assert resp.status_code in (302, 401)


def test_analysis_endpoint_requires_auth(client):
    resp = client.post("/api/analyze/descriptive", json={"dataset_id": 1})
    assert resp.status_code in (302, 401)


def test_search_endpoint_requires_auth(client):
    resp = client.get("/api/search?q=test")
    assert resp.status_code in (302, 401)


def test_download_start_requires_auth(client):
    resp = client.post("/api/download/start", json={})
    assert resp.status_code in (302, 401)


def test_progress_poll_requires_auth(client):
    resp = client.get("/api/progress/poll")
    assert resp.status_code in (302, 401)

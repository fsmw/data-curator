def test_jupyter_health_endpoint_authenticated(client, auth_user):
    resp = client.get("/api/jupyter/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] in {"disabled", "down", "ok"}


def test_notebooks_page_authenticated(client, auth_user):
    resp = client.get("/notebooks")
    assert resp.status_code == 200
    assert b"Notebooks" in resp.data


def test_notebooks_page_renders_jupyter_iframe_url(client, auth_user):
    client.application.extensions["jupyter_manager"].enabled = True
    resp = client.get("/notebooks")
    assert resp.status_code == 200
    assert b'/jupyter/lab' in resp.data


def test_sidebar_contains_notebooks_option(client, auth_user):
    resp = client.get("/status")
    assert resp.status_code == 200
    assert b"/notebooks" in resp.data


def test_notebooks_list_endpoint_authenticated(client, auth_user):
    resp = client.get("/api/notebooks")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert isinstance(data["notebooks"], list)


def test_notebooks_create_endpoint_authenticated(client, auth_user):
    resp = client.post("/api/notebooks/create", json={"name": "smoke-notebook"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["created"] is True

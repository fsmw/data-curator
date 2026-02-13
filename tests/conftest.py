import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.web import create_app
from src.models import db, User

@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))
    app = create_app()
    app.config.update({
        "TESTING": True,
    })
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()


def _login(client, username, password):
    client.get("/auth/logout", follow_redirects=True)
    return client.post(
        "/auth/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


@pytest.fixture
def auth_user(app, client):
    with app.app_context():
        user = User(username="testuser", email="testuser@example.com")
        user.set_password("testpass")
        db.session.add(user)
        db.session.commit()

    _login(client, "testuser", "testpass")
    return user


@pytest.fixture
def other_user(app):
    with app.app_context():
        user = User(username="otheruser", email="otheruser@example.com")
        user.set_password("otherpass")
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def login(client):
    return lambda username, password: _login(client, username, password)

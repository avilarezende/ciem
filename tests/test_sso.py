"""Testes SSO CIEM → Guacamole."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["CONFIG_PATH"] = str(Path(__file__).resolve().parents[1] / "config")
os.environ["CIEM_SECRET_KEY"] = "test-secret-key"
os.environ["PYTHONPATH"] = "shared:services/core"

from app.main import app  # noqa: E402
from ciem_common.sso import create_sso_token, guacamole_client_id, verify_sso_token  # noqa: E402

ADMIN_PASSWORD = "f5VOt3nlUR7CkEYm"
OBSERVER_PASSWORD = "1XaVVzaKZq2Sa6OR"


def _auth_headers(client: TestClient, username: str, password: str) -> dict[str, str]:
    login = client.post("/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['token']}"}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth() -> dict[str, str]:
    with TestClient(app) as c:
        return _auth_headers(c, "admin", ADMIN_PASSWORD)


@pytest.fixture
def observer_auth() -> dict[str, str]:
    with TestClient(app) as c:
        return _auth_headers(c, "observador", OBSERVER_PASSWORD)


def test_create_sso_token_roundtrip() -> None:
    token = create_sso_token("admin", target_id="rtr-core-01", ttl=60)
    payload = verify_sso_token(token)
    assert payload is not None
    assert payload["user"] == "admin"
    assert payload["target"] == "rtr-core-01"


def test_expired_sso_token() -> None:
    token = create_sso_token("admin", ttl=-10)
    assert verify_sso_token(token) is None


def test_guacamole_client_id() -> None:
    cid = guacamole_client_id("Roteador Core")
    assert isinstance(cid, str)
    assert len(cid) > 10


def test_create_guacamole_sso(client: TestClient, auth: dict[str, str]) -> None:
    resp = client.post("/sso/guacamole", json={"target_id": "rtr-core-01"}, headers=auth)
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert "login_url" in data
    assert data["target_name"] == "Roteador Core"


def test_create_guacamole_sso_invalid_target(client: TestClient, auth: dict[str, str]) -> None:
    resp = client.post("/sso/guacamole", json={"target_id": "inexistente"}, headers=auth)
    assert resp.status_code == 404


def test_sso_validate_with_token(client: TestClient) -> None:
    token = create_sso_token("admin")
    resp = client.get(f"/sso/validate?token={token}")
    assert resp.status_code == 200
    assert resp.headers.get("x-ciem-user") == "admin"


def test_sso_validate_invalid(client: TestClient) -> None:
    resp = client.get("/sso/validate?token=invalid")
    assert resp.status_code == 401


def test_sso_login_redirect(client: TestClient) -> None:
    token = create_sso_token("admin", target_id="rtr-core-01")
    resp = client.get(f"/sso/guacamole/login?token={token}", follow_redirects=False)
    assert resp.status_code == 302
    assert "ciem_sso" in resp.headers.get("set-cookie", "")
    assert "/guacamole/" in resp.headers.get("location", "")


def test_sso_requires_admin(client: TestClient, observer_auth: dict[str, str]) -> None:
    resp = client.post("/sso/guacamole", json={}, headers=observer_auth)
    assert resp.status_code == 403


def test_list_targets(client: TestClient, auth: dict[str, str]) -> None:
    resp = client.get("/targets", headers=auth)
    assert resp.status_code == 200
    targets = resp.json()
    assert any(t["id"] == "rtr-core-01" for t in targets)

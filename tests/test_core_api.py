"""Testes da API Core CIEM."""

import os

import pytest
from fastapi.testclient import TestClient

os.environ["CONFIG_PATH"] = str(
    __import__("pathlib").Path(__file__).resolve().parents[1] / "config"
)
os.environ["CIEM_SECRET_KEY"] = "test-secret-key"

from app.main import app  # noqa: E402

ADMIN_PASSWORD = "f5VOt3nlUR7CkEYm"
OBSERVER_PASSWORD = "1XaVVzaKZq2Sa6OR"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "ciem-core"


def test_info(client: TestClient) -> None:
    resp = client.get("/info")
    assert resp.status_code == 200
    assert "platform" in resp.json()


def test_login_admin(client: TestClient) -> None:
    resp = client.post("/auth/login", json={"username": "admin", "password": ADMIN_PASSWORD})
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "admin"
    # token assinado: duas partes separadas por "."
    assert "." in data["token"] and not data["token"].startswith("ciem-")


def test_login_invalid(client: TestClient) -> None:
    resp = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


def test_modules_status_requires_auth(client: TestClient) -> None:
    resp = client.get("/modules/status")
    assert resp.status_code == 401


def test_modules_status_authenticated(client: TestClient) -> None:
    login = client.post("/auth/login", json={"username": "admin", "password": ADMIN_PASSWORD})
    token = login.json()["token"]
    resp = client.get("/modules/status", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    modules = resp.json()
    assert isinstance(modules, list)
    assert len(modules) >= 6


def test_config_modules(client: TestClient) -> None:
    login = client.post(
        "/auth/login",
        json={"username": "observador", "password": OBSERVER_PASSWORD},
    )
    token = login.json()["token"]
    resp = client.get("/config/modules", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "zabbix" in resp.json()


def test_session_start_admin(client: TestClient) -> None:
    login = client.post("/auth/login", json={"username": "admin", "password": ADMIN_PASSWORD})
    token = login.json()["token"]
    resp = client.post(
        "/sessions/start",
        json={"target_id": "rtr-core-01", "protocol": "ssh"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "session_id" in resp.json()


def test_session_start_observer_forbidden(client: TestClient) -> None:
    login = client.post(
        "/auth/login",
        json={"username": "observador", "password": OBSERVER_PASSWORD},
    )
    token = login.json()["token"]
    resp = client.post(
        "/sessions/start",
        json={"target_id": "rtr-core-01", "protocol": "ssh"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_metrics(client: TestClient) -> None:
    client.get("/health")
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "ciem_requests_total" in resp.text

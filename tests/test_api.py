import pytest
from fastapi.testclient import TestClient

from ciem.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "ciem"


def test_info(client: TestClient) -> None:
    response = client.get("/info")
    assert response.status_code == 200
    assert "version" in response.json()


def test_validate_environment_valid(client: TestClient) -> None:
    payload = {
        "name": "ciem-dev",
        "install": "pip install -r requirements-dev.txt",
        "repos": ["https://github.com/rodrigo-rezende/ciem"],
    }
    response = client.post("/environments/validate", json=payload)
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_validate_environment_invalid(client: TestClient) -> None:
    payload = {"name": "ciem-dev", "repos": ["invalid-repo"]}
    response = client.post("/environments/validate", json=payload)
    assert response.status_code == 200
    assert response.json()["valid"] is False


def test_get_environment(client: TestClient) -> None:
    response = client.get("/environments/ciem")
    assert response.status_code == 200
    assert response.json()["name"] == "ciem"


def test_get_environment_not_found(client: TestClient) -> None:
    response = client.get("/environments/inexistente")
    assert response.status_code == 404


def test_metrics(client: TestClient) -> None:
    client.get("/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "ciem_requests_total" in response.text

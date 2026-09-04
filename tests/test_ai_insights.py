"""Testes de configuração de IA e insights públicos."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO = Path(__file__).resolve().parents[1]
os.environ["CONFIG_PATH"] = str(REPO / "config")
os.environ["CIEM_GRAFANA_TOKEN"] = "test-grafana-token"

from app.ai_insights import clear_insights_cache  # noqa: E402
from app.main import app  # noqa: E402
from ciem_common.config_loader import clear_config_cache, load_ai_config  # noqa: E402

GRAFANA_HEADERS = {"X-Grafana-Token": "test-grafana-token"}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    login = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {login.json()['token']}"}


@pytest.fixture
def observer_headers(client: TestClient) -> dict[str, str]:
    login = client.post("/auth/login", json={"username": "observador", "password": "observer123"})
    return {"Authorization": f"Bearer {login.json()['token']}"}


@pytest.fixture
def ai_yaml_backup(tmp_path: Path):
    src = REPO / "config" / "ai.yaml"
    backup = tmp_path / "ai.yaml.bak"
    shutil.copy2(src, backup)
    clear_config_cache()
    clear_insights_cache()
    yield src
    shutil.copy2(backup, src)
    clear_config_cache()
    clear_insights_cache()


def test_observer_cannot_read_ai_config(
    client: TestClient, observer_headers: dict[str, str]
) -> None:
    resp = client.get("/config/ai", headers=observer_headers)
    assert resp.status_code == 403


def test_admin_can_configure_ai(
    client: TestClient, admin_headers: dict[str, str], ai_yaml_backup: Path
) -> None:
    resp = client.put(
        "/config/ai",
        json={
            "enabled": True,
            "base_url": "https://llm.lab.local/v1",
            "api_key": "sk-test-secret-key",
            "model": "gpt-test",
            "temperature": 0.1,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["ai"]
    assert data["enabled"] is True
    assert data["base_url"] == "https://llm.lab.local/v1"
    assert data["model"] == "gpt-test"
    assert data["api_key_set"] is True
    assert data["api_key"].endswith("key")
    assert "sk-test-secret" not in data["api_key"]

    cfg = load_ai_config()
    assert cfg.api_key == "sk-test-secret-key"
    assert cfg.enabled is True


def test_masked_api_key_does_not_overwrite(
    client: TestClient, admin_headers: dict[str, str], ai_yaml_backup: Path
) -> None:
    client.put(
        "/config/ai",
        json={"enabled": True, "api_key": "sk-real-value-1234"},
        headers=admin_headers,
    )
    resp = client.put(
        "/config/ai",
        json={"enabled": True, "api_key": "************1234", "model": "kept-model"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert load_ai_config().api_key == "sk-real-value-1234"
    assert load_ai_config().model == "kept-model"


def test_insights_visible_to_all_when_enabled(
    client: TestClient,
    admin_headers: dict[str, str],
    observer_headers: dict[str, str],
    ai_yaml_backup: Path,
) -> None:
    # desabilitado
    off = client.get("/insights", headers=observer_headers)
    assert off.status_code == 200
    assert off.json()["enabled"] is False

    client.put(
        "/config/ai",
        json={"enabled": True, "api_key": "", "model": "local-heuristic"},
        headers=admin_headers,
    )
    clear_insights_cache()

    for headers in (observer_headers, admin_headers):
        resp = client.get("/insights", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["enabled"] is True
        assert "insights" in body
        assert body["status"] == "ok"
        # sem expor segredos
        assert "api_key" not in body


def test_observer_cannot_refresh(client: TestClient, observer_headers: dict[str, str]) -> None:
    resp = client.post("/insights/refresh", headers=observer_headers)
    assert resp.status_code == 403


def test_grafana_insights_table(
    client: TestClient, admin_headers: dict[str, str], ai_yaml_backup: Path
) -> None:
    client.put("/config/ai", json={"enabled": True}, headers=admin_headers)
    clear_insights_cache()
    resp = client.get("/grafana/insights/table", headers=GRAFANA_HEADERS)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1

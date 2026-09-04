"""Testes de ativação/desativação de módulos via API."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO = Path(__file__).resolve().parents[1]
os.environ["CONFIG_PATH"] = str(REPO / "config")

from app.main import app  # noqa: E402
from ciem_common.config_loader import clear_config_cache, is_module_enabled, set_module_enabled


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
def modules_yaml_backup(tmp_path: Path):
    """Copia modules.yaml e restaura após o teste."""
    src = REPO / "config" / "modules.yaml"
    backup = tmp_path / "modules.yaml.bak"
    shutil.copy2(src, backup)
    clear_config_cache()
    yield src
    shutil.copy2(backup, src)
    clear_config_cache()


def test_set_module_enabled_roundtrip(modules_yaml_backup: Path) -> None:
    original = is_module_enabled("zabbix")
    set_module_enabled("zabbix", not original)
    assert is_module_enabled("zabbix") is (not original)
    set_module_enabled("zabbix", original)
    assert is_module_enabled("zabbix") is original
    text = modules_yaml_backup.read_text(encoding="utf-8")
    assert "zabbix:" in text
    assert "# Zabbix" in text  # comentários preservados


def test_toggle_module_api_admin(client: TestClient, admin_headers: dict[str, str], modules_yaml_backup: Path) -> None:
    before = client.get("/config/modules", headers=admin_headers).json()["zabbix"]["enabled"]
    resp = client.put(
        "/config/modules/zabbix",
        json={"enabled": not before},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["enabled"] is (not before)
    after = client.get("/config/modules", headers=admin_headers).json()["zabbix"]["enabled"]
    assert after is (not before)
    # restaura
    client.put("/config/modules/zabbix", json={"enabled": before}, headers=admin_headers)


def test_toggle_module_requires_admin(client: TestClient, observer_headers: dict[str, str]) -> None:
    resp = client.put(
        "/config/modules/zabbix",
        json={"enabled": True},
        headers=observer_headers,
    )
    assert resp.status_code == 403


def test_toggle_unknown_module(client: TestClient, admin_headers: dict[str, str]) -> None:
    resp = client.put(
        "/config/modules/naoexiste",
        json={"enabled": True},
        headers=admin_headers,
    )
    assert resp.status_code == 404

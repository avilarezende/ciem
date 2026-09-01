"""Testes dos endpoints Grafana por módulo."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["CONFIG_PATH"] = str(Path(__file__).resolve().parents[1] / "config")
os.environ["CIEM_GRAFANA_TOKEN"] = "test-grafana-token"
os.environ["PYTHONPATH"] = "shared:services/core"

from app.main import app  # noqa: E402

HDR = {"X-Grafana-Token": "test-grafana-token"}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_grafana_module_data(client: TestClient) -> None:
    resp = client.get("/grafana/modules/zabbix/data", headers=HDR)
    assert resp.status_code == 200
    data = resp.json()
    assert data["module"] == "zabbix"


def test_grafana_module_alarms(client: TestClient) -> None:
    resp = client.get("/grafana/modules/zabbix/alarms", headers=HDR)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_grafana_module_history(client: TestClient) -> None:
    resp = client.get("/grafana/modules/nagios/history", headers=HDR)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_grafana_module_not_found(client: TestClient) -> None:
    resp = client.get("/grafana/modules/invalido/alarms", headers=HDR)
    assert resp.status_code == 404


def test_grafana_modules_list(client: TestClient) -> None:
    resp = client.get("/grafana/modules-list", headers=HDR)
    assert resp.status_code == 200
    modules = resp.json()
    assert len(modules) == 6
    assert modules[0]["dashboard_uid"].startswith("ciem-mod-")

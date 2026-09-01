"""Testes dos endpoints Grafana."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["CONFIG_PATH"] = str(Path(__file__).resolve().parents[1] / "config")
os.environ["CIEM_GRAFANA_TOKEN"] = "test-grafana-token"

from app.main import app  # noqa: E402

GRAFANA_HEADERS = {"X-Grafana-Token": "test-grafana-token"}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_grafana_alarms_requires_token(client: TestClient) -> None:
    resp = client.get("/grafana/alarms")
    assert resp.status_code == 401


def test_grafana_alarms_with_token(client: TestClient) -> None:
    resp = client.get("/grafana/alarms", headers=GRAFANA_HEADERS)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_grafana_targets(client: TestClient) -> None:
    resp = client.get("/grafana/targets", headers=GRAFANA_HEADERS)
    assert resp.status_code == 200
    targets = resp.json()
    assert len(targets) >= 3
    assert targets[0]["hostname"]


def test_grafana_modules(client: TestClient) -> None:
    resp = client.get("/grafana/modules", headers=GRAFANA_HEADERS)
    assert resp.status_code == 200
    modules = resp.json()
    assert any(m["module"] == "zabbix" for m in modules)


def test_metrics_includes_ciem_gauges(client: TestClient) -> None:
    resp = client.get("/metrics")
    assert resp.status_code == 200
    text = resp.text
    assert "ciem_active_alarms" in text
    assert "ciem_module_up" in text
    assert "ciem_maintenance_targets" in text

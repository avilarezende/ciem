"""Testes de configuração LDAP e usuários locais via API."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO = Path(__file__).resolve().parents[1]
os.environ["CONFIG_PATH"] = str(REPO / "config")

from app.main import app  # noqa: E402
from ciem_common.auth import authenticate, verify_password
from ciem_common.config_loader import clear_config_cache, load_auth_config


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    login = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {login.json()['token']}"}


@pytest.fixture
def auth_yaml_backup(tmp_path: Path):
    src = REPO / "config" / "auth.yaml"
    backup = tmp_path / "auth.yaml.bak"
    shutil.copy2(src, backup)
    clear_config_cache()
    yield src
    shutil.copy2(backup, src)
    clear_config_cache()


def test_default_admin_independent_of_ldap(auth_yaml_backup: Path) -> None:
    client_api = TestClient(app)
    # habilita LDAP sem quebrar admin local
    admin = client_api.post("/auth/login", json={"username": "admin", "password": "admin123"})
    token = admin.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    resp = client_api.put(
        "/config/auth/ldap",
        json={"enabled": True, "host": "ldap.lab.local", "port": 636, "domain": "lab.local"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["ldap"]["enabled"] is True
    # admin local ainda autentica
    again = client_api.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert again.status_code == 200
    assert again.json()["role"] == "admin"


def test_get_auth_config(client: TestClient, admin_headers: dict[str, str]) -> None:
    resp = client.get("/config/auth", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "ldap" in data
    assert "local_users" in data
    usernames = [u["username"] for u in data["local_users"]]
    assert "admin" in usernames
    assert all("password_hash" not in u for u in data["local_users"])


def test_change_admin_password(client: TestClient, admin_headers: dict[str, str], auth_yaml_backup: Path) -> None:
    resp = client.put(
        "/config/auth/users/admin",
        json={"password": "novaSenhaAdmin1"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert authenticate("admin", "admin123") is None
    assert authenticate("admin", "novaSenhaAdmin1") is not None
    # restaura para não quebrar outros testes da sessão
    client.put(
        "/config/auth/users/admin",
        json={"password": "admin123"},
        headers={"Authorization": f"Bearer ciem-admin"},
    )


def test_cannot_delete_last_admin(client: TestClient, admin_headers: dict[str, str], auth_yaml_backup: Path) -> None:
    # remove observador ok
    # tenta remover admin sem outro admin
    resp = client.delete("/config/auth/users/admin", headers=admin_headers)
    assert resp.status_code == 400
    assert "último" in resp.json()["detail"].lower() or "ultimo" in resp.json()["detail"].lower() or "administrador" in resp.json()["detail"].lower()


def test_create_and_delete_user(client: TestClient, admin_headers: dict[str, str], auth_yaml_backup: Path) -> None:
    created = client.post(
        "/config/auth/users",
        json={"username": "ops1", "password": "ops-pass", "role": "observer"},
        headers=admin_headers,
    )
    assert created.status_code == 200
    assert authenticate("ops1", "ops-pass") is not None
    deleted = client.delete("/config/auth/users/ops1", headers=admin_headers)
    assert deleted.status_code == 200
    assert authenticate("ops1", "ops-pass") is None


def test_ldap_fields_persisted(client: TestClient, admin_headers: dict[str, str], auth_yaml_backup: Path) -> None:
    resp = client.put(
        "/config/auth/ldap",
        json={
            "enabled": False,
            "host": "dc01.corp.local",
            "port": 636,
            "use_ssl": True,
            "domain": "corp.local",
            "base_dn": "dc=corp,dc=local",
            "uid_attribute": "sAMAccountName",
            "user_filter": "(sAMAccountName=%s)",
            "ca_cert_path": "/etc/ciem/certs/corp-ca.crt",
            "verify_ssl": True,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    ldap = resp.json()["ldap"]
    assert ldap["host"] == "dc01.corp.local"
    assert ldap["uid_attribute"] == "sAMAccountName"
    assert ldap["ca_cert_path"] == "/etc/ciem/certs/corp-ca.crt"
    text = auth_yaml_backup.read_text(encoding="utf-8")
    assert "dc01.corp.local" in text
    assert "sAMAccountName" in text

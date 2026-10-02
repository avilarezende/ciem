"""Testes de hardening OWASP (política de senha, SSRF, cabeçalhos)."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from ciem_common.password_policy import PasswordPolicyError, validate_password
from ciem_common.url_safety import UnsafeURLError, validate_outbound_url
from conftest import ADMIN_PASSWORD, ensure_test_config

ensure_test_config()
os.environ.setdefault("CIEM_SECRET_KEY", "test-secret-key-for-ci-only")

from app.main import app  # noqa: E402


def test_password_policy_accepts_strong() -> None:
    validate_password("SeguraDemais1", username="admin")


def test_password_policy_rejects_short() -> None:
    with pytest.raises(PasswordPolicyError):
        validate_password("Ab1")


def test_password_policy_rejects_common() -> None:
    with pytest.raises(PasswordPolicyError):
        validate_password("admin123")


def test_password_policy_rejects_username_match() -> None:
    with pytest.raises(PasswordPolicyError):
        validate_password("MeuUsuario1", username="MeuUsuario1")


def test_ssrf_blocks_localhost() -> None:
    with pytest.raises(UnsafeURLError):
        validate_outbound_url("https://127.0.0.1/llm")
    with pytest.raises(UnsafeURLError):
        validate_outbound_url("https://localhost/llm")
    with pytest.raises(UnsafeURLError):
        validate_outbound_url("https://169.254.169.254/latest/meta-data")


def test_ssrf_blocks_http() -> None:
    with pytest.raises(UnsafeURLError):
        validate_outbound_url("http://example.com/v1")


def test_ssrf_allows_https_public_literal_when_resolvable() -> None:
    # example.com é público; se DNS falhar no ambiente, marca skip.
    try:
        assert validate_outbound_url("https://example.com/v1").startswith("https://")
    except UnsafeURLError as exc:
        if "resolver" in str(exc).lower() or "resolve" in str(exc).lower():
            pytest.skip(str(exc))
        raise


def test_security_headers_on_health() -> None:
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("Referrer-Policy") == "no-referrer"
    assert "X-Request-ID" in resp.headers
    assert "frame-ancestors" in (resp.headers.get("Content-Security-Policy") or "")


def test_weak_password_rejected_on_create_user() -> None:
    client = TestClient(app)
    login = client.post("/auth/login", json={"username": "admin", "password": ADMIN_PASSWORD})
    headers = {"Authorization": f"Bearer {login.json()['token']}"}
    resp = client.post(
        "/config/auth/users",
        json={"username": "weakuser", "password": "admin123", "role": "observer"},
        headers=headers,
    )
    assert resp.status_code == 400

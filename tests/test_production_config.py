"""Production must reject development settings without exposing credentials."""

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASE_ENV = {
    "CIEM_ENV": "production",
    "CIEM_SECRET_KEY": "fixture-secret",
    "CIEM_TRUSTED_HOSTS": "ciem.example.invalid",
    "CIEM_CORS_ORIGINS": "https://ciem.example.invalid",
    "CIEM_RATE_LIMIT_ENABLED": "1",
    "CIEM_DOCS_ENABLED": "0",
}


def load_config(overrides):
    env = os.environ.copy()
    env.update(BASE_ENV)
    credential = hashlib.sha256(b"production-config-fixture").hexdigest()
    for name in ("ENGINE_API_TOKEN", "CIEM_SECRET_KEY", "PORTAL_SESSION_SECRET"):
        if name in BASE_ENV:
            env[name] = credential
    if "DATABASE_URL" in BASE_ENV:
        env["DATABASE_URL"] = "postgresql+asyncpg://app:" + credential + "@db:5432/app"
    env.update(overrides)
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "services/core"), str(ROOT / "shared")])
    result = subprocess.run(
        [sys.executable, "-c", "import app.config"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert credential not in result.stderr
    return result


def test_production_accepts_explicit_secure_configuration():
    result = load_config({})
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "overrides",
    [
        {"CIEM_SECRET_KEY": "test-secret-key-for-ci-only"},
        {"CIEM_TRUSTED_HOSTS": "*"},
        {"CIEM_CORS_ORIGINS": "*"},
        {"CIEM_DOCS_ENABLED": "1"},
        {"CIEM_RATE_LIMIT_ENABLED": "0"},
    ],
)
def test_production_rejects_development_configuration(overrides):
    assert load_config(overrides).returncode != 0

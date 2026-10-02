"""Testes de autenticação e configuração."""

import os
from pathlib import Path

from conftest import ADMIN_PASSWORD, OBSERVER_PASSWORD, ensure_test_config

ensure_test_config()

from ciem_common.auth import authenticate, hash_password, verify_password  # noqa: E402
from ciem_common.config_loader import (  # noqa: E402
    is_module_enabled,
    load_main_config,
    load_modules_config,
)


def test_hash_and_verify_password() -> None:
    hashed = hash_password("teste123")
    assert verify_password("teste123", hashed)
    assert not verify_password("errado", hashed)


def test_authenticate_admin() -> None:
    user = authenticate("admin", ADMIN_PASSWORD)
    assert user is not None
    assert user.role.value == "admin"


def test_authenticate_observer() -> None:
    user = authenticate("observador", OBSERVER_PASSWORD)
    assert user is not None
    assert user.role.value == "observer"


def test_authenticate_invalid() -> None:
    assert authenticate("admin", "wrong") is None


def test_load_main_config() -> None:
    cfg = load_main_config()
    assert cfg.platform_name == "CIEM"


def test_load_modules_config() -> None:
    cfg = load_modules_config()
    assert "zabbix" in cfg.modules


def test_module_disabled_by_default() -> None:
    assert is_module_enabled("zabbix") is False


def test_config_path_is_isolated() -> None:
    """Garante que os testes não escrevem no config/ versionado."""
    cfg = Path(os.environ["CONFIG_PATH"]).resolve()
    repo_config = Path(__file__).resolve().parents[1] / "config"
    assert cfg != repo_config.resolve()

"""Testes de provisionamento Guacamole."""

import os
import sys
from pathlib import Path

import pytest

os.environ["CONFIG_PATH"] = str(Path(__file__).resolve().parents[1] / "config")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "guacamole"))

from provision import generate_guacamole_properties, generate_user_mapping

from ciem_common.config_loader import clear_config_cache
from ciem_common.targets_loader import clear_targets_cache, load_targets_config


@pytest.fixture(autouse=True)
def _clear_caches():
    clear_config_cache()
    clear_targets_cache()
    yield
    clear_config_cache()
    clear_targets_cache()


def test_load_targets_config() -> None:
    cfg = load_targets_config()
    assert len(cfg.targets) >= 3
    enabled = cfg.enabled_targets()
    assert all(t.enabled for t in enabled)
    assert "srv-win-ad" not in [t.id for t in enabled]


def test_generate_user_mapping_contains_connections() -> None:
    xml = generate_user_mapping()
    assert "<user-mapping>" in xml
    assert "protocol>ssh</protocol>" in xml
    assert "Roteador Core" in xml
    assert "Switch Distribuição 01" in xml
    assert 'authorize username="admin"' in xml


def test_generate_user_mapping_disabled_target_excluded() -> None:
    xml = generate_user_mapping()
    assert "Controlador de Domínio" not in xml


def test_generate_guacamole_properties() -> None:
    props = generate_guacamole_properties()
    assert "HttpHeaderAuthenticationProvider" in props
    assert "X-CIEM-User" in props
    assert "user-mapping.xml" in props


def test_ssh_recording_params() -> None:
    xml = generate_user_mapping()
    assert "recording-path" in xml
    assert "typescript-path" in xml

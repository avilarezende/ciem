"""Testes do CIEM — bootstrap de ambiente, senhas de fixture e CONFIG_PATH isolado.

As senhas abaixo são **apenas para a suíte de testes** (baixa entropia, sem valor
em produção). Os hashes correspondentes são gravados num diretório temporário
copiado de ``config/``, para que ``auth.yaml`` do repositório não precise
expor plaintext e o gitleaks não acione falso positivo nos testes.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

# Rate limiting desativado nos testes (evita limites de IP durante a suíte).
os.environ.setdefault("CIEM_RATE_LIMIT_ENABLED", "0")
os.environ.setdefault("CIEM_SECRET_KEY", "test-secret-key-for-ci-only")
os.environ.setdefault("CIEM_GRAFANA_TOKEN", "test-grafana-token")

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "shared"))
sys.path.insert(0, str(REPO / "services" / "core"))

# Senhas de fixture (baixa entropia, com letra+dígito — não usar em produção).
ADMIN_PASSWORD = "test-admin-pass1"
OBSERVER_PASSWORD = "test-observer-pass1"

_TEST_CONFIG: Path | None = None


def _rewrite_auth_hashes(auth_yaml: Path) -> None:
    from ciem_common.auth import hash_password

    admin_hash = hash_password(ADMIN_PASSWORD)
    observer_hash = hash_password(OBSERVER_PASSWORD)
    text = auth_yaml.read_text(encoding="utf-8")
    lines = text.splitlines(True)
    out: list[str] = []
    current: str | None = None
    for line in lines:
        if re.search(r"username:\s*admin\b", line):
            current = "admin"
        elif re.search(r"username:\s*observador\b", line):
            current = "observador"
        if current and line.strip().startswith("password_hash:"):
            digest = admin_hash if current == "admin" else observer_hash
            indent = line[: len(line) - len(line.lstrip())]
            out.append(f'{indent}password_hash: "{digest}"\n')
            current = None
            continue
        out.append(line)
    auth_yaml.write_text("".join(out), encoding="utf-8")


def ensure_test_config() -> Path:
    """Garante um CONFIG_PATH temporário com senhas de fixture conhecidas."""
    global _TEST_CONFIG
    if _TEST_CONFIG is not None and _TEST_CONFIG.is_dir():
        os.environ["CONFIG_PATH"] = str(_TEST_CONFIG)
        return _TEST_CONFIG

    tmp = Path(tempfile.mkdtemp(prefix="ciem-test-config-"))
    src = REPO / "config"
    for item in src.iterdir():
        if item.is_file():
            shutil.copy2(item, tmp / item.name)
    _rewrite_auth_hashes(tmp / "auth.yaml")
    os.environ["CONFIG_PATH"] = str(tmp)
    _TEST_CONFIG = tmp

    try:
        from ciem_common.config_loader import clear_config_cache

        clear_config_cache()
    except Exception:
        pass
    return tmp


# Executa na importação do conftest (antes dos módulos de teste sobrescreverem env).
ensure_test_config()


def pytest_configure(config) -> None:  # noqa: ARG001
    ensure_test_config()

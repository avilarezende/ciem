"""Carregamento de configuração YAML dos módulos coletores."""

import os
from pathlib import Path
from typing import Any

import yaml


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Carrega o arquivo YAML de configuração do módulo."""
    config_path = Path(path or os.getenv("CONFIG_PATH", "/app/config.yaml"))
    if not config_path.exists():
        return {}
    with config_path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data or {}

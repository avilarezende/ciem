"""Carrega YAML de configuração (clientes, módulos, fontes)."""

from pathlib import Path
from typing import Any

import yaml

from app.config import settings


def load_yaml(name: str) -> dict[str, Any]:
    path = settings.config_dir / name
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_clients() -> list[dict[str, Any]]:
    data = load_yaml("clients.yaml")
    return data.get("instituicoes", [])


def find_institution(query: str) -> dict[str, Any] | None:
    q = query.strip().lower()
    for inst in get_clients():
        if inst.get("sigla", "").lower() == q:
            return inst
        if inst.get("nome", "").lower() == q:
            return inst
        for alias in inst.get("aliases", []):
            if alias.lower() in q or q in alias.lower():
                return inst
    return None

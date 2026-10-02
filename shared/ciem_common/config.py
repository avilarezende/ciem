"""Carregamento de configuração YAML dos módulos coletores."""

import os
from pathlib import Path
from typing import Any

import yaml


def _load_yaml_file(config_file: Path) -> dict[str, Any]:
    with config_file.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data or {}


def _extract_module_options(full: dict[str, Any], module_name: str) -> dict[str, Any]:
    """Extrai ``options`` do módulo a partir de um YAML na forma ``modules.<nome>``.

    A função também aceita YAML já achatado (formato antigo ``config.yaml``
    de cada módulo), em que as chaves estão no topo.
    """
    modules = full.get("modules")
    if isinstance(modules, dict) and module_name in modules:
        entry = modules[module_name]
        if isinstance(entry, dict):
            return dict(entry.get("options") or {})
    return dict(full)


def load_config(path: str | Path | None = None, module_name: str | None = None) -> dict[str, Any]:
    """Carrega a configuração do módulo a partir de ``CONFIG_PATH``.

    Suporta dois layouts de ``CONFIG_PATH``:

    - **Arquivo** (ex.: ``/app/config.yaml``): carrega o YAML diretamente.
    - **Diretório** (ex.: ``/app/config``): procura ``modules.yaml`` (ou o
      primeiro ``*.yaml``/``*.yml``) e extrai ``modules.<module_name>.options``.

    Quando ``module_name`` é informado e o YAML está no formato
    ``modules.<nome>.options``, retorna apenas as opções do módulo — mesmo
    comportamento do antigo ``config.yaml`` de cada módulo.
    """
    raw = path if path is not None else os.getenv("CONFIG_PATH", "/app/config.yaml")
    config_path = Path(raw)

    if not config_path.exists():
        return {}

    if config_path.is_dir():
        candidates = [
            config_path / "modules.yaml",
            config_path / "config.yaml",
            config_path / "config.yml",
        ]
        existing = [c for c in candidates if c.is_file()]
        if not existing:
            # Fallback: qualquer *.yaml/*.yml no diretório
            existing = sorted(config_path.glob("*.yaml")) + sorted(config_path.glob("*.yml"))
        if not existing:
            return {}

        # modules.yaml tem precedência; demais arquivos são apenas fallback.
        full: dict[str, Any] = {}
        for f in existing:
            full = {**full, **_load_yaml_file(f)}

        if module_name:
            return _extract_module_options(full, module_name)
        return full

    return _load_yaml_file(config_path)
"""Registro de auditoria de sessões de manutenção em arquivo JSON Lines."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

from ciem_common.config_loader import load_main_config
from ciem_common.interfaces import SessionRecord

_write_lock = Lock()


def _audit_log_path(override: str | Path | None = None) -> Path:
    """Resolve o caminho do arquivo de auditoria.

    Prioridade:
    1. Parâmetro ``override`` explícito.
    2. Variável de ambiente ``AUDIT_LOG_PATH``.
    3. Valor ``audit_log_path`` em ``config/main.yaml``.
    """
    if override is not None:
        return Path(override).expanduser().resolve()
    env_path = os.environ.get("AUDIT_LOG_PATH")
    if env_path:
        return Path(env_path).expanduser().resolve()
    return Path(load_main_config().audit_log_path).expanduser().resolve()


def _serialize_record(record: SessionRecord) -> dict[str, Any]:
    """Converte :class:`SessionRecord` para dicionário JSON-serializável."""
    return {
        "session_id": record.session_id,
        "user": record.user,
        "target_host": record.target_host,
        "protocol": record.protocol,
        "started_at": record.started_at.astimezone(UTC).isoformat(),
        "ended_at": record.ended_at.astimezone(UTC).isoformat() if record.ended_at else None,
        "commands": record.commands,
        "duration_seconds": record.duration_seconds,
        "logged_at": datetime.now(UTC).isoformat(),
    }


def log_session(
    record: SessionRecord,
    *,
    audit_log_path: str | Path | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    """Grava um registro de sessão em formato JSON Lines (uma linha por evento).

    O diretório pai do arquivo é criado automaticamente se não existir.

    Args:
        record: Dados da sessão auditada.
        audit_log_path: Caminho opcional do arquivo; padrão via config/env.
        extra: Campos adicionais mesclados ao JSON (ex.: ``source_module``, ``client_ip``).

    Returns:
        Caminho absoluto do arquivo onde o registro foi gravado.
    """
    path = _audit_log_path(audit_log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = _serialize_record(record)
    if extra:
        payload.update(extra)

    line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    with _write_lock:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    return path


def read_sessions(
    *,
    audit_log_path: str | Path | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Lê registros de auditoria do arquivo JSON Lines.

    Args:
        audit_log_path: Caminho opcional do arquivo.
        limit: Número máximo de registros retornados (mais recentes por ordem de leitura).

    Returns:
        Lista de dicionários parseados; linhas inválidas são ignoradas.
    """
    path = _audit_log_path(audit_log_path)
    if not path.is_file():
        return []

    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if limit is not None and limit > 0:
        return records[-limit:]
    return records

"""Registro estruturado de eventos de segurança (OWASP A09)."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("ciem.security")


def security_event(event: str, *, level: int = logging.INFO, **fields: Any) -> None:
    """Emite um evento de segurança em JSON (sem senhas/tokens)."""
    payload = {
        "ts": datetime.now(UTC).isoformat(),
        "event": event,
        **{k: v for k, v in fields.items() if v is not None},
    }
    logger.log(level, json.dumps(payload, ensure_ascii=False, default=str))

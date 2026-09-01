"""Estado em memória das sessões de manutenção ativas."""

from __future__ import annotations

from typing import Any

from ciem_common.interfaces import SessionRecord

_active_sessions: dict[str, dict[str, Any]] = {}


def start_session_record(session_id: str, record: SessionRecord) -> None:
    _active_sessions[session_id] = {"record": record, "commands": []}


def pop_session(session_id: str) -> dict[str, Any] | None:
    return _active_sessions.pop(session_id, None)


def active_session_count() -> int:
    return len(_active_sessions)

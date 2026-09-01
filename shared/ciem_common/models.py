"""Modelos normalizados de resposta dos coletores CIEM."""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ActiveAlarm(BaseModel):
    """Alarme ou problema ativo detectado na fonte monitorada."""

    id: str
    severity: str
    message: str
    source: str
    timestamp: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class HistoryEvent(BaseModel):
    """Evento histórico ou informativo coletado da fonte."""

    id: str
    event_type: str
    message: str
    timestamp: str
    metadata: dict[str, Any] = Field(default_factory=dict)


CollectStatus = Literal["ok", "degraded", "error"]


class CollectResponse(BaseModel):
    """Resposta padronizada do endpoint POST /collect."""

    module: str
    timestamp: str
    status: CollectStatus
    active_alarms: list[ActiveAlarm] = Field(default_factory=list)
    history_events: list[HistoryEvent] = Field(default_factory=list)

    @classmethod
    def build(
        cls,
        module: str,
        status: CollectStatus,
        active_alarms: list[ActiveAlarm] | None = None,
        history_events: list[HistoryEvent] | None = None,
    ) -> "CollectResponse":
        return cls(
            module=module,
            timestamp=datetime.now(UTC).isoformat(),
            status=status,
            active_alarms=active_alarms or [],
            history_events=history_events or [],
        )

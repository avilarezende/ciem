"""Coletor CIEM para TOPdesk API (tickets/incidentes)."""

import os
from datetime import UTC, datetime
from typing import Any

import httpx

from ciem_common import (
    ActiveAlarm,
    CollectResponse,
    CollectorModule,
    HistoryEvent,
    create_collector_app,
    load_config,
)

MODULE_NAME = "topdesk"


class TopdeskCollector(CollectorModule):
    name = MODULE_NAME

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def _auth(self) -> tuple[str, str]:
        username = self.config.get("username") or os.getenv("TOPDESK_USERNAME", "")
        password = self.config.get("password") or os.getenv("TOPDESK_PASSWORD", "")
        return username, password

    async def _collect_live(self) -> CollectResponse:
        url = self.config.get("url", "").strip().rstrip("/")
        username, password = self._auth()
        if not all([url, username, password]):
            raise ValueError("url, username e password são obrigatórios")

        timeout = float(self.config.get("timeout", 60))
        verify = bool(self.config.get("verify_ssl", True))
        ticket_limit = int(self.config.get("ticket_limit", 50))
        status_filter = self.config.get("status_filter", "")

        active_alarms: list[ActiveAlarm] = []
        history_events: list[HistoryEvent] = []

        params: dict[str, Any] = {"page_size": ticket_limit}
        if status_filter:
            params["query"] = f"processingStatus.name=in=({status_filter})"

        async with httpx.AsyncClient(timeout=timeout, verify=verify, auth=(username, password)) as client:
            response = await client.get(f"{url}/incidents", params=params)
            response.raise_for_status()
            tickets = response.json()

            if isinstance(tickets, dict):
                tickets = tickets.get("items", tickets.get("incidents", []))

            if isinstance(tickets, list):
                for ticket in tickets[:ticket_limit]:
                    number = ticket.get("number") or ticket.get("id", "sem-numero")
                    brief = ticket.get("briefDescription") or ticket.get("shortDescription", "Sem descrição")
                    status = (
                        ticket.get("processingStatus", {}).get("name")
                        if isinstance(ticket.get("processingStatus"), dict)
                        else ticket.get("status", "desconhecido")
                    )
                    priority = (
                        ticket.get("priority", {}).get("name")
                        if isinstance(ticket.get("priority"), dict)
                        else str(ticket.get("priority", "normal"))
                    )
                    creation = ticket.get("creationDate") or ticket.get("requestDate") or datetime.now(UTC).isoformat()

                    history_events.append(
                        HistoryEvent(
                            id=f"topdesk-ticket-{number}",
                            event_type="ticket",
                            message=f"Chamado TOPdesk #{number}: {brief}",
                            timestamp=str(creation),
                            metadata={
                                "number": number,
                                "status": status,
                                "priority": priority,
                            },
                        )
                    )

                    if str(status).lower() not in ("resolved", "closed", "fechado", "resolvido"):
                        active_alarms.append(
                            ActiveAlarm(
                                id=f"topdesk-alarm-{number}",
                                severity=str(priority).lower(),
                                message=f"Chamado aberto #{number}: {brief}",
                                source=MODULE_NAME,
                                timestamp=str(creation),
                                metadata={"number": number, "status": status, "priority": priority},
                            )
                        )

        return CollectResponse.build(MODULE_NAME, "ok", active_alarms=active_alarms, history_events=history_events)

    def _mock_response(self) -> CollectResponse:
        now = datetime.now(UTC).isoformat()
        return CollectResponse.build(
            MODULE_NAME,
            "degraded",
            active_alarms=[
                ActiveAlarm(
                    id="topdesk-mock-alarm-1",
                    severity="high",
                    message="[MOCK] Chamado aberto #INC-2026-001: Indisponibilidade do portal",
                    source=MODULE_NAME,
                    timestamp=now,
                    metadata={"mock": True, "number": "INC-2026-001"},
                )
            ],
            history_events=[
                HistoryEvent(
                    id="topdesk-mock-ticket-1",
                    event_type="ticket",
                    message="[MOCK] Chamado TOPdesk #INC-2026-001: Indisponibilidade do portal",
                    timestamp=now,
                    metadata={"mock": True},
                )
            ],
        )

    async def collect(self) -> CollectResponse:
        try:
            return await self._collect_live()
        except Exception:
            if self.config.get("use_mock_on_failure", True):
                return self._mock_response()
            return CollectResponse.build(MODULE_NAME, "error")


config = load_config()
collector = TopdeskCollector(config)
app = create_collector_app(collector)

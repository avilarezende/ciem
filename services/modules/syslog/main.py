"""Coletor CIEM para eventos Syslog (API REST ou arquivo local)."""

import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from ciem_common import (
    ActiveAlarm,
    CollectorModule,
    CollectResponse,
    HistoryEvent,
    create_collector_app,
    load_config,
)

MODULE_NAME = "syslog"


class SyslogCollector(CollectorModule):
    name = MODULE_NAME

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def _parse_line(self, line: str) -> dict[str, str] | None:
        pattern = self.config.get(
            "syslog_pattern",
            r"^(?P<timestamp>\S+\s+\d+\s+\S+)\s+(?P<hostname>\S+)\s+(?P<app>\S+):\s+(?P<message>.+)$",
        )
        match = re.match(pattern, line.strip())
        if not match:
            return None
        return match.groupdict()

    def _classify_severity(self, message: str) -> str:
        lowered = message.lower()
        for level in (
            "emerg",
            "alert",
            "crit",
            "critical",
            "error",
            "warning",
            "notice",
            "info",
            "debug",
        ):
            if level in lowered:
                return level
        return "info"

    def _is_alarm(self, severity: str) -> bool:
        alarm_levels = {
            s.lower()
            for s in self.config.get("alarm_severities", ["error", "critical", "alert", "emerg"])
        }
        return severity.lower() in alarm_levels

    async def _collect_from_api(self) -> CollectResponse:
        api_url = self.config.get("api_url", "").strip().rstrip("/")
        endpoint = self.config.get("events_endpoint", "/events")
        token = self.config.get("token") or os.getenv("SYSLOG_TOKEN", "")
        if not api_url:
            raise ValueError("api_url é obrigatória no modo api")

        timeout = float(self.config.get("timeout", 60))
        verify = bool(self.config.get("verify_ssl", True))
        event_limit = int(self.config.get("event_limit", 100))
        query = self.config.get("query", "")

        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        active_alarms: list[ActiveAlarm] = []
        history_events: list[HistoryEvent] = []

        params: dict[str, Any] = {"limit": event_limit}
        if query:
            params["q"] = query

        async with httpx.AsyncClient(timeout=timeout, verify=verify, headers=headers) as client:
            response = await client.get(f"{api_url}{endpoint}", params=params)
            response.raise_for_status()
            payload = response.json()
            events = payload.get("events", payload) if isinstance(payload, dict) else payload

            if not isinstance(events, list):
                raise RuntimeError("Resposta da API syslog não contém lista de eventos")

            for index, event in enumerate(events[:event_limit]):
                if isinstance(event, str):
                    parsed = self._parse_line(event) or {
                        "message": event,
                        "hostname": "unknown",
                        "app": "syslog",
                    }
                    ts = datetime.now(UTC).isoformat()
                elif isinstance(event, dict):
                    parsed = {
                        "message": event.get("message", ""),
                        "hostname": event.get("host") or event.get("hostname", "unknown"),
                        "app": event.get("app") or event.get("facility", "syslog"),
                    }
                    ts = str(
                        event.get("timestamp")
                        or event.get("@timestamp")
                        or datetime.now(UTC).isoformat()
                    )
                else:
                    continue

                message = parsed.get("message", "")
                severity = self._classify_severity(message)
                event_id = f"syslog-api-{index}"

                history_events.append(
                    HistoryEvent(
                        id=event_id,
                        event_type="syslog",
                        message=f"[{parsed.get('hostname')}] {message}",
                        timestamp=ts,
                        metadata={
                            "hostname": parsed.get("hostname"),
                            "app": parsed.get("app"),
                            "severity": severity,
                        },
                    )
                )

                if self._is_alarm(severity):
                    active_alarms.append(
                        ActiveAlarm(
                            id=f"syslog-alarm-{index}",
                            severity=severity,
                            message=message,
                            source=MODULE_NAME,
                            timestamp=ts,
                            metadata={"hostname": parsed.get("hostname"), "app": parsed.get("app")},
                        )
                    )

        return CollectResponse.build(
            MODULE_NAME, "ok", active_alarms=active_alarms, history_events=history_events
        )

    async def _collect_from_file(self) -> CollectResponse:
        file_path = Path(self.config.get("file_path", "/var/log/syslog"))
        tail_lines = int(self.config.get("file_tail_lines", 200))
        event_limit = int(self.config.get("event_limit", 100))

        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo syslog não encontrado: {file_path}")

        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()[-tail_lines:]

        active_alarms: list[ActiveAlarm] = []
        history_events: list[HistoryEvent] = []

        for index, line in enumerate(lines[-event_limit:]):
            parsed = self._parse_line(line)
            if not parsed:
                continue
            message = parsed.get("message", line)
            severity = self._classify_severity(message)
            ts = parsed.get("timestamp", datetime.now(UTC).isoformat())
            event_id = f"syslog-file-{index}"

            history_events.append(
                HistoryEvent(
                    id=event_id,
                    event_type="syslog",
                    message=f"[{parsed.get('hostname')}] {message}",
                    timestamp=ts,
                    metadata={
                        "hostname": parsed.get("hostname"),
                        "app": parsed.get("app"),
                        "severity": severity,
                    },
                )
            )

            if self._is_alarm(severity):
                active_alarms.append(
                    ActiveAlarm(
                        id=f"syslog-alarm-file-{index}",
                        severity=severity,
                        message=message,
                        source=MODULE_NAME,
                        timestamp=ts,
                        metadata={"hostname": parsed.get("hostname"), "app": parsed.get("app")},
                    )
                )

        return CollectResponse.build(
            MODULE_NAME, "ok", active_alarms=active_alarms, history_events=history_events
        )

    def _mock_response(self) -> CollectResponse:
        now = datetime.now(UTC).isoformat()
        return CollectResponse.build(
            MODULE_NAME,
            "degraded",
            active_alarms=[
                ActiveAlarm(
                    id="syslog-mock-alarm-1",
                    severity="error",
                    message="[MOCK] kernel: NIC link down on eth0",
                    source=MODULE_NAME,
                    timestamp=now,
                    metadata={"mock": True, "hostname": "fw-01"},
                )
            ],
            history_events=[
                HistoryEvent(
                    id="syslog-mock-event-1",
                    event_type="syslog",
                    message="[MOCK] [fw-01] sshd: Accepted publickey for admin",
                    timestamp=now,
                    metadata={"mock": True, "severity": "info"},
                )
            ],
        )

    async def collect(self) -> CollectResponse:
        try:
            mode = self.config.get("mode", "api")
            if mode == "file":
                return await self._collect_from_file()
            return await self._collect_from_api()
        except Exception:
            if self.config.get("use_mock_on_failure", True):
                return self._mock_response()
            return CollectResponse.build(MODULE_NAME, "error")


config = load_config()
collector = SyslogCollector(config)
app = create_collector_app(collector)

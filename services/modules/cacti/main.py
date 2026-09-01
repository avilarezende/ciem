"""Coletor CIEM para Cacti (graphs, devices)."""

import os
import re
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

MODULE_NAME = "cacti"


class CactiCollector(CollectorModule):
    name = MODULE_NAME

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    async def _login(self, client: httpx.AsyncClient, base_url: str) -> bool:
        login_page = await client.get(f"{base_url}/index.php")
        login_page.raise_for_status()
        csrf_match = re.search(r'name="__csrf_magic"\s+value="([^"]+)"', login_page.text)
        csrf_val = csrf_match.group(1) if csrf_match else ""

        response = await client.post(
            f"{base_url}/index.php",
            data={
                "action": "login",
                "login_username": self.config.get("username") or os.getenv("CACTI_USERNAME", ""),
                "login_password": self.config.get("password") or os.getenv("CACTI_PASSWORD", ""),
                "__csrf_magic": csrf_val,
            },
            follow_redirects=True,
        )
        return "logout" in response.text.lower()

    def _parse_hosts(self, html: str, limit: int) -> list[HistoryEvent]:
        events: list[HistoryEvent] = []
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.DOTALL | re.IGNORECASE)
        for row in rows[:limit]:
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.DOTALL | re.IGNORECASE)
            if len(cells) < 2:
                continue
            hostname = re.sub(r"<[^>]+>", "", cells[1]).strip()
            status = re.sub(r"<[^>]+>", "", cells[-1]).strip()
            if not hostname or hostname.lower() in ("description", "hostname"):
                continue
            host_id_match = re.search(r"host_id=(\d+)", row)
            host_id = host_id_match.group(1) if host_id_match else hostname
            events.append(
                HistoryEvent(
                    id=f"cacti-host-{host_id}",
                    event_type="device",
                    message=f"Dispositivo Cacti: {hostname} (status: {status or 'desconhecido'})",
                    timestamp=datetime.now(UTC).isoformat(),
                    metadata={"host_id": host_id, "status": status},
                )
            )
        return events

    def _parse_graphs(self, html: str, limit: int) -> list[HistoryEvent]:
        events: list[HistoryEvent] = []
        links = re.findall(
            r'<a[^>]+href="[^"]*graph_id=(\d+)[^"]*"[^>]*>(.*?)</a>',
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        for graph_id, title_html in links[:limit]:
            title = re.sub(r"<[^>]+>", "", title_html).strip() or f"Gráfico {graph_id}"
            events.append(
                HistoryEvent(
                    id=f"cacti-graph-{graph_id}",
                    event_type="graph",
                    message=f"Gráfico Cacti: {title}",
                    timestamp=datetime.now(UTC).isoformat(),
                    metadata={"graph_id": graph_id},
                )
            )
        return events

    async def _collect_live(self) -> CollectResponse:
        url = self.config.get("url", "").strip().rstrip("/")
        username = self.config.get("username") or os.getenv("CACTI_USERNAME", "")
        password = self.config.get("password") or os.getenv("CACTI_PASSWORD", "")
        if not all([url, username, password]):
            raise ValueError("url, username e password são obrigatórios")

        timeout = float(self.config.get("timeout", 60))
        verify = bool(self.config.get("verify_ssl", True))
        host_limit = int(self.config.get("host_limit", 80))
        graph_limit = int(self.config.get("graph_limit", 30))

        active_alarms: list[ActiveAlarm] = []
        history_events: list[HistoryEvent] = []

        async with httpx.AsyncClient(timeout=timeout, verify=verify, follow_redirects=True) as client:
            if not await self._login(client, url):
                raise RuntimeError("Falha no login Cacti")

            host_response = await client.get(f"{url}/host.php", params={"filter": "", "page": "1"})
            host_response.raise_for_status()
            history_events.extend(self._parse_hosts(host_response.text, host_limit))

            graph_response = await client.get(f"{url}/graph_view.php")
            if graph_response.status_code == 200:
                history_events.extend(self._parse_graphs(graph_response.text, graph_limit))

            for event in history_events:
                if event.event_type == "device" and event.metadata.get("status", "").lower() in (
                    "down",
                    "error",
                    "failed",
                ):
                    active_alarms.append(
                        ActiveAlarm(
                            id=f"cacti-alarm-{event.metadata.get('host_id', event.id)}",
                            severity="high",
                            message=f"Dispositivo com falha: {event.message}",
                            source=MODULE_NAME,
                            timestamp=event.timestamp,
                            metadata=event.metadata,
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
                    id="cacti-mock-alarm-1",
                    severity="high",
                    message="[MOCK] Dispositivo router-core-01 indisponível",
                    source=MODULE_NAME,
                    timestamp=now,
                    metadata={"mock": True, "host_id": "42"},
                )
            ],
            history_events=[
                HistoryEvent(
                    id="cacti-mock-host-1",
                    event_type="device",
                    message="[MOCK] Dispositivo Cacti: switch-access-01",
                    timestamp=now,
                    metadata={"mock": True},
                ),
                HistoryEvent(
                    id="cacti-mock-graph-1",
                    event_type="graph",
                    message="[MOCK] Gráfico Cacti: Tráfego WAN",
                    timestamp=now,
                    metadata={"mock": True, "graph_id": "101"},
                ),
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
collector = CactiCollector(config)
app = create_collector_app(collector)

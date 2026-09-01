"""Coletor CIEM para Nagios / Nagios XI API."""

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

MODULE_NAME = "nagios"


class NagiosCollector(CollectorModule):
    name = MODULE_NAME

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def _headers(self, api_key: str) -> dict[str, str]:
        return {"Accept": "application/json", "X-API-Key": api_key}

    async def _get_json(self, client: httpx.AsyncClient, endpoint: str, api_key: str) -> Any:
        base_url = self.config["url"].rstrip("/")
        response = await client.get(
            f"{base_url}/api/v1/{endpoint.lstrip('/')}",
            headers=self._headers(api_key),
            params={"apikey": api_key},
        )
        response.raise_for_status()
        return response.json()

    async def _collect_live(self) -> CollectResponse:
        url = self.config.get("url", "").strip()
        api_key = self.config.get("api_key") or os.getenv("NAGIOS_API_KEY", "")
        if not all([url, api_key]):
            raise ValueError("url e api_key são obrigatórios")

        timeout = float(self.config.get("timeout", 60))
        verify = bool(self.config.get("verify_ssl", True))
        service_limit = int(self.config.get("service_limit", 100))
        flavor = self.config.get("flavor", "nagiosxi")

        active_alarms: list[ActiveAlarm] = []
        history_events: list[HistoryEvent] = []

        async with httpx.AsyncClient(timeout=timeout, verify=verify) as client:
            if flavor == "nagiosxi":
                hosts_data = await self._get_json(client, "objects/hosts", api_key)
                hosts = hosts_data.get("hosts", hosts_data) if isinstance(hosts_data, dict) else hosts_data
                if isinstance(hosts, list):
                    for host in hosts[:service_limit]:
                        host_name = host.get("host_name") or host.get("name", "desconhecido")
                        state = str(host.get("current_state", host.get("state", "unknown")))
                        history_events.append(
                            HistoryEvent(
                                id=f"nagios-host-{host_name}",
                                event_type="host",
                                message=f"Host Nagios: {host_name} (estado: {state})",
                                timestamp=datetime.now(UTC).isoformat(),
                                metadata={"host_name": host_name, "state": state},
                            )
                        )
                        if state in ("1", "2", "CRITICAL", "DOWN"):
                            active_alarms.append(
                                ActiveAlarm(
                                    id=f"nagios-alarm-host-{host_name}",
                                    severity="critical" if state in ("2", "CRITICAL") else "high",
                                    message=f"Host {host_name} em estado crítico ou indisponível",
                                    source=MODULE_NAME,
                                    timestamp=datetime.now(UTC).isoformat(),
                                    metadata={"host_name": host_name, "state": state},
                                )
                            )

                services_data = await self._get_json(client, "objects/services", api_key)
                services = (
                    services_data.get("services", services_data)
                    if isinstance(services_data, dict)
                    else services_data
                )
                if isinstance(services, list):
                    for service in services[:service_limit]:
                        host_name = service.get("host_name", "unknown")
                        service_desc = service.get("service_description") or service.get("description", "serviço")
                        state = str(service.get("current_state", service.get("state", "unknown")))
                        history_events.append(
                            HistoryEvent(
                                id=f"nagios-service-{host_name}-{service_desc}",
                                event_type="service",
                                message=f"Serviço {service_desc} em {host_name} (estado: {state})",
                                timestamp=datetime.now(UTC).isoformat(),
                                metadata={
                                    "host_name": host_name,
                                    "service_description": service_desc,
                                    "state": state,
                                },
                            )
                        )
                        if state in ("1", "2", "WARNING", "CRITICAL"):
                            active_alarms.append(
                                ActiveAlarm(
                                    id=f"nagios-alarm-svc-{host_name}-{service_desc}",
                                    severity="critical" if state in ("2", "CRITICAL") else "warning",
                                    message=f"Serviço {service_desc} em {host_name} com alerta",
                                    source=MODULE_NAME,
                                    timestamp=datetime.now(UTC).isoformat(),
                                    metadata={
                                        "host_name": host_name,
                                        "service_description": service_desc,
                                        "state": state,
                                    },
                                )
                            )
            else:
                status_data = await self._get_json(client, "system/status", api_key)
                history_events.append(
                    HistoryEvent(
                        id="nagios-system-status",
                        event_type="system",
                        message=f"Status Nagios Core: {status_data}",
                        timestamp=datetime.now(UTC).isoformat(),
                        metadata={"raw": status_data},
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
                    id="nagios-mock-alarm-1",
                    severity="critical",
                    message="[MOCK] Serviço HTTP em web-01 em estado CRITICAL",
                    source=MODULE_NAME,
                    timestamp=now,
                    metadata={"mock": True, "host_name": "web-01"},
                )
            ],
            history_events=[
                HistoryEvent(
                    id="nagios-mock-host-1",
                    event_type="host",
                    message="[MOCK] Host Nagios: db-01 (estado: UP)",
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
collector = NagiosCollector(config)
app = create_collector_app(collector)

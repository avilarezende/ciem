"""Coletor CIEM para Zabbix API (hosts, triggers, problems)."""

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

MODULE_NAME = "zabbix"


class ZabbixCollector(CollectorModule):
    name = MODULE_NAME

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    async def _rpc(
        self,
        client: httpx.AsyncClient,
        method: str,
        params: dict[str, Any] | list[Any],
        auth: str | None = None,
    ) -> Any:
        payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
        if auth:
            payload["auth"] = auth
        response = await client.post(f"{self.config['url'].rstrip('/')}/api_jsonrpc.php", json=payload)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            message = data["error"].get("data") or data["error"].get("message", "Erro Zabbix API")
            raise RuntimeError(message)
        return data.get("result")

    async def _collect_live(self) -> CollectResponse:
        url = self.config.get("url", "").strip()
        username = self.config.get("username") or os.getenv("ZABBIX_USERNAME", "")
        password = self.config.get("password") or os.getenv("ZABBIX_PASSWORD", "")
        if not all([url, username, password]):
            raise ValueError("url, username e password são obrigatórios")

        timeout = float(self.config.get("timeout", 60))
        verify = bool(self.config.get("verify_ssl", True))
        problem_limit = int(self.config.get("problem_limit", 50))

        active_alarms: list[ActiveAlarm] = []
        history_events: list[HistoryEvent] = []

        async with httpx.AsyncClient(timeout=timeout, verify=verify) as client:
            auth = await self._rpc(client, "user.login", {"username": username, "password": password})
            if not isinstance(auth, str):
                raise RuntimeError("Falha na autenticação Zabbix")

            hosts = await self._rpc(
                client,
                "host.get",
                {"output": ["hostid", "host", "name", "status"], "selectTriggers": ["triggerid", "description", "priority"]},
                auth=auth,
            )
            if isinstance(hosts, list):
                for host in hosts[:100]:
                    host_name = host.get("name") or host.get("host", "desconhecido")
                    history_events.append(
                        HistoryEvent(
                            id=f"zabbix-host-{host.get('hostid')}",
                            event_type="host",
                            message=f"Host monitorado: {host_name}",
                            timestamp=datetime.now(UTC).isoformat(),
                            metadata={
                                "hostid": host.get("hostid"),
                                "status": host.get("status"),
                                "trigger_count": len(host.get("triggers", [])),
                            },
                        )
                    )

            problems = await self._rpc(
                client,
                "problem.get",
                {
                    "output": ["eventid", "name", "severity", "clock", "objectid"],
                    "recent": True,
                    "sortfield": ["eventid"],
                    "sortorder": "DESC",
                    "limit": problem_limit,
                },
                auth=auth,
            )
            if isinstance(problems, list):
                for problem in problems:
                    clock = int(problem.get("clock", 0))
                    ts = datetime.fromtimestamp(clock, tz=UTC).isoformat() if clock else datetime.now(UTC).isoformat()
                    active_alarms.append(
                        ActiveAlarm(
                            id=f"zabbix-problem-{problem.get('eventid')}",
                            severity=str(problem.get("severity", "unknown")),
                            message=problem.get("name", "Problema sem descrição"),
                            source=MODULE_NAME,
                            timestamp=ts,
                            metadata={"eventid": problem.get("eventid"), "objectid": problem.get("objectid")},
                        )
                    )

            triggers = await self._rpc(
                client,
                "trigger.get",
                {
                    "output": ["triggerid", "description", "priority", "value", "lastchange"],
                    "only_true": True,
                    "sortfield": "lastchange",
                    "sortorder": "DESC",
                    "limit": problem_limit,
                },
                auth=auth,
            )
            if isinstance(triggers, list):
                for trigger in triggers:
                    last_change = int(trigger.get("lastchange", 0))
                    ts = (
                        datetime.fromtimestamp(last_change, tz=UTC).isoformat()
                        if last_change
                        else datetime.now(UTC).isoformat()
                    )
                    active_alarms.append(
                        ActiveAlarm(
                            id=f"zabbix-trigger-{trigger.get('triggerid')}",
                            severity=str(trigger.get("priority", "unknown")),
                            message=trigger.get("description", "Trigger ativo"),
                            source=MODULE_NAME,
                            timestamp=ts,
                            metadata={"triggerid": trigger.get("triggerid"), "value": trigger.get("value")},
                        )
                    )

            await self._rpc(client, "user.logout", [], auth=auth)

        return CollectResponse.build(MODULE_NAME, "ok", active_alarms=active_alarms, history_events=history_events)

    def _mock_response(self) -> CollectResponse:
        now = datetime.now(UTC).isoformat()
        return CollectResponse.build(
            MODULE_NAME,
            "degraded",
            active_alarms=[
                ActiveAlarm(
                    id="zabbix-mock-problem-1",
                    severity="4",
                    message="[MOCK] Alta utilização de CPU em srv-app-01",
                    source=MODULE_NAME,
                    timestamp=now,
                    metadata={"mock": True},
                )
            ],
            history_events=[
                HistoryEvent(
                    id="zabbix-mock-host-1",
                    event_type="host",
                    message="[MOCK] Host monitorado: srv-app-01",
                    timestamp=now,
                    metadata={"mock": True, "hostid": "10001"},
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
collector = ZabbixCollector(config)
app = create_collector_app(collector)

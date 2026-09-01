"""Agregação de dados dos módulos coletores."""

from __future__ import annotations

from typing import Any

import httpx

from ciem_common.config_loader import is_module_enabled

MODULE_URLS: dict[str, str] = {
    "zabbix": "http://module-zabbix:8080",
    "cacti": "http://module-cacti:8080",
    "nagios": "http://module-nagios:8080",
    "topdesk": "http://module-topdesk:8080",
    "inventory": "http://module-inventory:8080",
    "syslog": "http://module-syslog:8080",
}

SEVERITY_ORDER = {"critical": 0, "high": 1, "warning": 2, "info": 3}


async def aggregate_alarms(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    alarms: list[dict[str, Any]] = []
    for name, url in MODULE_URLS.items():
        if not is_module_enabled(name):
            continue
        try:
            resp = await client.post(f"{url}/collect")
            if resp.status_code == 200:
                for alarm in resp.json().get("active_alarms", []):
                    alarm["source_module"] = name
                    alarms.append(alarm)
        except httpx.HTTPError:
            continue
    alarms.sort(key=lambda a: SEVERITY_ORDER.get(a.get("severity", "info"), 99))
    return alarms


async def aggregate_history(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for name, url in MODULE_URLS.items():
        if not is_module_enabled(name):
            continue
        try:
            resp = await client.post(f"{url}/collect")
            if resp.status_code == 200:
                for event in resp.json().get("history_events", []):
                    event["source_module"] = name
                    events.append(event)
        except httpx.HTTPError:
            continue
    events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return events


async def aggregate_modules(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for name, url in MODULE_URLS.items():
        enabled = is_module_enabled(name)
        info: dict[str, Any] = {"module": name, "enabled": enabled, "url": url}
        if enabled:
            try:
                resp = await client.get(f"{url}/health")
                info["health"] = resp.json() if resp.status_code == 200 else {"status": "error"}
            except httpx.HTTPError:
                info["health"] = {"status": "unreachable"}
        results.append(info)
    return results

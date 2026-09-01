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

async def collect_module_data(
    module_name: str,
    client: httpx.AsyncClient,
) -> dict[str, Any]:
    """Coleta dados de um módulo específico."""
    if module_name not in MODULE_URLS:
        raise ValueError(f"Módulo desconhecido: {module_name}")
    enabled = is_module_enabled(module_name)
    result: dict[str, Any] = {
        "module": module_name,
        "enabled": enabled,
        "status": "disabled",
        "active_alarms": [],
        "history_events": [],
    }
    if not enabled:
        return result

    url = MODULE_URLS[module_name]
    try:
        health = await client.get(f"{url}/health")
        result["health"] = health.json() if health.status_code == 200 else {"status": "error"}
    except httpx.HTTPError:
        result["health"] = {"status": "unreachable"}
        result["status"] = "error"
        return result

    try:
        resp = await client.post(f"{url}/collect")
        if resp.status_code == 200:
            data = resp.json()
            result["status"] = data.get("status", "ok")
            result["active_alarms"] = data.get("active_alarms", [])
            result["history_events"] = data.get("history_events", [])
        else:
            result["status"] = "error"
    except httpx.HTTPError:
        result["status"] = "error"
    return result


MODULE_LABELS: dict[str, str] = {
    "zabbix": "Zabbix",
    "cacti": "Cacti",
    "nagios": "Nagios / Nagios XI",
    "topdesk": "TOPdesk",
    "inventory": "Inventário",
    "syslog": "Syslog",
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

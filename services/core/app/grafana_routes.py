"""Endpoints e métricas Prometheus para dashboards Grafana."""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import APIRouter, Header, HTTPException, status
from prometheus_client import Gauge

from ciem_common.audit import read_sessions
from ciem_common.config_loader import load_main_config
from ciem_common.targets_loader import load_targets_config

from .aggregators import (
    MODULE_LABELS,
    MODULE_URLS,
    aggregate_alarms,
    aggregate_history,
    aggregate_modules,
    collect_module_data,
)
from .sessions_store import active_session_count

GRAFANA_TOKEN = os.environ.get("CIEM_GRAFANA_TOKEN", "ciem-grafana-internal")


def _grafana_token() -> str:
    return os.environ.get("CIEM_GRAFANA_TOKEN", GRAFANA_TOKEN)


ALARMS_GAUGE = Gauge(
    "ciem_active_alarms",
    "Alarmes ativos agregados dos módulos CIEM",
    ["severity"],
)
MODULES_GAUGE = Gauge(
    "ciem_module_up",
    "Status de saúde dos módulos (1=ok, 0=down/desabilitado)",
    ["module"],
)
TARGETS_GAUGE = Gauge(
    "ciem_maintenance_targets",
    "Alvos de manutenção configurados",
    ["status"],
)
SESSIONS_GAUGE = Gauge("ciem_active_sessions", "Sessões de manutenção ativas")

router = APIRouter(prefix="/grafana", tags=["grafana"])


def _verify_grafana_token(x_grafana_token: str | None = Header(default=None)) -> None:
    if x_grafana_token != _grafana_token():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Grafana inválido",
        )


async def refresh_prometheus_metrics() -> None:
    """Atualiza gauges Prometheus com dados agregados."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            alarms = await aggregate_alarms(client)
            modules = await aggregate_modules(client)
    except Exception:
        alarms = []
        modules = []

    by_severity: dict[str, int] = {}
    for alarm in alarms:
        sev = alarm.get("severity", "info")
        by_severity[sev] = by_severity.get(sev, 0) + 1
    for sev in ("critical", "high", "warning", "info"):
        ALARMS_GAUGE.labels(severity=sev).set(by_severity.get(sev, 0))

    for mod in modules:
        name = mod["module"]
        if not mod.get("enabled"):
            MODULES_GAUGE.labels(module=name).set(0)
        elif mod.get("health", {}).get("status") == "ok":
            MODULES_GAUGE.labels(module=name).set(1)
        else:
            MODULES_GAUGE.labels(module=name).set(0)

    targets = load_targets_config()
    enabled = len(targets.enabled_targets())
    disabled = len(targets.targets) - enabled
    TARGETS_GAUGE.labels(status="enabled").set(enabled)
    TARGETS_GAUGE.labels(status="disabled").set(disabled)

    SESSIONS_GAUGE.set(active_session_count())


@router.get("/alarms")
async def grafana_alarms(
    x_grafana_token: str | None = Header(default=None),
) -> list[dict[str, Any]]:
    _verify_grafana_token(x_grafana_token)
    async with httpx.AsyncClient(timeout=60.0) as client:
        return await aggregate_alarms(client)


@router.get("/history")
async def grafana_history(
    limit: int = 100,
    x_grafana_token: str | None = Header(default=None),
) -> list[dict[str, Any]]:
    _verify_grafana_token(x_grafana_token)
    async with httpx.AsyncClient(timeout=60.0) as client:
        events = await aggregate_history(client)
    return events[:limit]


@router.get("/modules")
async def grafana_modules(
    x_grafana_token: str | None = Header(default=None),
) -> list[dict[str, Any]]:
    _verify_grafana_token(x_grafana_token)
    async with httpx.AsyncClient(timeout=30.0) as client:
        return await aggregate_modules(client)


@router.get("/sessions")
async def grafana_sessions(
    limit: int = 50,
    x_grafana_token: str | None = Header(default=None),
) -> list[dict[str, Any]]:
    _verify_grafana_token(x_grafana_token)
    main = load_main_config()
    return read_sessions(audit_log_path=main.audit_log_path, limit=limit)


@router.get("/targets")
async def grafana_targets(
    x_grafana_token: str | None = Header(default=None),
) -> list[dict[str, Any]]:
    _verify_grafana_token(x_grafana_token)
    cfg = load_targets_config()
    return [
        {
            "id": t.id,
            "name": t.name,
            "hostname": t.hostname,
            "port": t.port,
            "protocol": t.protocol,
            "enabled": t.enabled,
            "tags": ",".join(t.tags),
            "description": t.description,
        }
        for t in cfg.targets
    ]


@router.get("/insights")
async def grafana_insights(
    x_grafana_token: str | None = Header(default=None),
) -> dict[str, Any]:
    """Pacote completo de insights de IA para painéis Grafana."""
    _verify_grafana_token(x_grafana_token)
    from .ai_insights import get_insights_public

    return await get_insights_public(force=False)


@router.get("/insights/table")
async def grafana_insights_table(
    x_grafana_token: str | None = Header(default=None),
) -> list[dict[str, Any]]:
    """Insights achatados (tabela) para o datasource Infinity."""
    _verify_grafana_token(x_grafana_token)
    from .ai_insights import get_insights_public

    data = await get_insights_public(force=False)
    if not data.get("enabled"):
        return [
            {
                "title": "IA desabilitada",
                "severity": "info",
                "detail": data.get("message") or "Ative Insights de IA na Configuração (admin).",
                "recommendation": "",
                "summary": "",
                "generated_at": "",
                "mode": "disabled",
            }
        ]
    rows = []
    for item in data.get("insights") or []:
        rows.append(
            {
                "title": item.get("title"),
                "severity": item.get("severity"),
                "detail": item.get("detail"),
                "recommendation": item.get("recommendation"),
                "summary": data.get("summary"),
                "generated_at": data.get("generated_at"),
                "mode": data.get("mode"),
            }
        )
    if not rows:
        rows.append(
            {
                "title": "Sem insights",
                "severity": "info",
                "detail": data.get("summary") or "Nenhum padrão identificado.",
                "recommendation": "",
                "summary": data.get("summary"),
                "generated_at": data.get("generated_at"),
                "mode": data.get("mode"),
            }
        )
    return rows


@router.get("/insights/charts")
async def grafana_insights_charts(
    x_grafana_token: str | None = Header(default=None),
) -> list[dict[str, Any]]:
    """Séries de gráficos gerados pela IA (labels/values achatados)."""
    _verify_grafana_token(x_grafana_token)
    from .ai_insights import get_insights_public

    data = await get_insights_public(force=False)
    rows: list[dict[str, Any]] = []
    for chart in data.get("charts") or []:
        labels = chart.get("labels") or []
        values = chart.get("values") or []
        for index, label in enumerate(labels):
            rows.append(
                {
                    "chart_id": chart.get("id"),
                    "chart_title": chart.get("title"),
                    "chart_type": chart.get("type"),
                    "label": label,
                    "value": values[index] if index < len(values) else 0,
                    "generated_at": data.get("generated_at"),
                }
            )
    return rows


def _check_module(module_name: str) -> None:
    if module_name not in MODULE_URLS:
        raise HTTPException(status_code=404, detail=f"Módulo '{module_name}' não encontrado")


@router.get("/modules/{module_name}/data")
async def grafana_module_data(
    module_name: str,
    x_grafana_token: str | None = Header(default=None),
) -> dict[str, Any]:
    _verify_grafana_token(x_grafana_token)
    _check_module(module_name)
    async with httpx.AsyncClient(timeout=60.0) as client:
        return await collect_module_data(module_name, client)


@router.get("/modules/{module_name}/alarms")
async def grafana_module_alarms(
    module_name: str,
    x_grafana_token: str | None = Header(default=None),
) -> list[dict[str, Any]]:
    _verify_grafana_token(x_grafana_token)
    _check_module(module_name)
    async with httpx.AsyncClient(timeout=60.0) as client:
        data = await collect_module_data(module_name, client)
    return data.get("active_alarms", [])


@router.get("/modules/{module_name}/history")
async def grafana_module_history(
    module_name: str,
    limit: int = 100,
    x_grafana_token: str | None = Header(default=None),
) -> list[dict[str, Any]]:
    _verify_grafana_token(x_grafana_token)
    _check_module(module_name)
    async with httpx.AsyncClient(timeout=60.0) as client:
        data = await collect_module_data(module_name, client)
    return data.get("history_events", [])[:limit]


@router.get("/modules-list")
async def grafana_modules_list(
    x_grafana_token: str | None = Header(default=None),
) -> list[dict[str, str]]:
    _verify_grafana_token(x_grafana_token)
    return [
        {
            "module": name,
            "label": MODULE_LABELS.get(name, name),
            "dashboard_uid": f"ciem-mod-{name}",
        }
        for name in MODULE_URLS
    ]

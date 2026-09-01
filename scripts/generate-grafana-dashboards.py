#!/usr/bin/env python3
"""Gera dashboards Grafana por módulo coletor."""

import json
from pathlib import Path

MODULES = {
    "zabbix": {"label": "Zabbix", "desc": "Hosts, triggers e problemas ativos"},
    "cacti": {"label": "Cacti", "desc": "Dispositivos e gráficos de performance"},
    "nagios": {"label": "Nagios / Nagios XI", "desc": "Status de hosts e serviços"},
    "topdesk": {"label": "TOPdesk", "desc": "Chamados e incidentes de suporte"},
    "inventory": {"label": "Inventário", "desc": "Ativos de rede via API REST"},
    "syslog": {"label": "Syslog", "desc": "Eventos de syslog centralizado"},
}

OUT = Path(__file__).resolve().parents[1] / "grafana" / "dashboards"


def build_dashboard(module: str, meta: dict) -> dict:
    label = meta["label"]
    uid = f"ciem-mod-{module}"
    return {
        "annotations": {"list": []},
        "editable": False,
        "graphTooltip": 1,
        "links": [
            {"title": "← Visão Geral NOC", "url": "/grafana/d/ciem-overview", "type": "link"},
            {"title": "Todos os Módulos", "url": "/grafana/d/ciem-modules", "type": "link"},
        ],
        "panels": [
            {
                "type": "text",
                "gridPos": {"h": 2, "w": 24, "x": 0, "y": 0},
                "id": 1,
                "options": {
                    "mode": "markdown",
                    "content": f"# CIEM — {label}\n{meta['desc']}",
                },
            },
            {
                "type": "stat",
                "title": f"Alarmes Ativos ({label})",
                "gridPos": {"h": 4, "w": 8, "x": 0, "y": 2},
                "id": 2,
                "datasource": {"type": "yesoreyeram-infinity-datasource", "uid": "ciem-api"},
                "options": {"colorMode": "background", "reduceOptions": {"calcs": ["count"]}},
                "fieldConfig": {
                    "defaults": {
                        "thresholds": {
                            "steps": [
                                {"color": "green", "value": None},
                                {"color": "red", "value": 1},
                            ]
                        }
                    }
                },
                "targets": [{
                    "refId": "A",
                    "type": "json",
                    "source": "url",
                    "url": f"/grafana/modules/{module}/alarms",
                    "url_options": {"method": "GET"},
                    "root_selector": "",
                    "columns": [],
                }],
            },
            {
                "type": "stat",
                "title": "Status do Módulo",
                "gridPos": {"h": 4, "w": 8, "x": 8, "y": 2},
                "id": 3,
                "datasource": {"type": "prometheus", "uid": "ciem-prometheus"},
                "fieldConfig": {
                    "defaults": {
                        "mappings": [
                            {"type": "value", "options": {"0": {"text": "OFFLINE"}, "1": {"text": "ONLINE"}}}
                        ],
                        "thresholds": {
                            "steps": [
                                {"color": "red", "value": None},
                                {"color": "green", "value": 1},
                            ]
                        },
                    }
                },
                "targets": [{
                    "expr": f'ciem_module_up{{module="{module}"}} or vector(0)',
                    "refId": "A",
                }],
            },
            {
                "type": "stat",
                "title": "Eventos no Histórico",
                "gridPos": {"h": 4, "w": 8, "x": 16, "y": 2},
                "id": 4,
                "datasource": {"type": "yesoreyeram-infinity-datasource", "uid": "ciem-api"},
                "options": {"reduceOptions": {"calcs": ["count"]}},
                "targets": [{
                    "refId": "A",
                    "type": "json",
                    "source": "url",
                    "url": f"/grafana/modules/{module}/history?limit=200",
                    "url_options": {"method": "GET"},
                    "columns": [],
                }],
            },
            {
                "type": "table",
                "title": f"⚠ Alarmes Ativos — {label}",
                "gridPos": {"h": 10, "w": 24, "x": 0, "y": 6},
                "id": 5,
                "datasource": {"type": "yesoreyeram-infinity-datasource", "uid": "ciem-api"},
                "fieldConfig": {
                    "overrides": [{
                        "matcher": {"id": "byName", "options": "severity"},
                        "properties": [{
                            "id": "mappings",
                            "value": [
                                {"type": "value", "options": {"critical": {"color": "red", "text": "CRÍTICO"}}},
                                {"type": "value", "options": {"warning": {"color": "yellow", "text": "AVISO"}}},
                            ],
                        }],
                    }]
                },
                "targets": [{
                    "refId": "A",
                    "type": "json",
                    "source": "url",
                    "url": f"/grafana/modules/{module}/alarms",
                    "url_options": {"method": "GET"},
                    "columns": [
                        {"selector": "severity", "text": "Severidade", "type": "string"},
                        {"selector": "message", "text": "Alarme", "type": "string"},
                        {"selector": "id", "text": "ID", "type": "string"},
                        {"selector": "timestamp", "text": "Horário", "type": "timestamp"},
                    ],
                }],
            },
            {
                "type": "table",
                "title": f"Histórico — {label}",
                "gridPos": {"h": 10, "w": 24, "x": 0, "y": 16},
                "id": 6,
                "datasource": {"type": "yesoreyeram-infinity-datasource", "uid": "ciem-api"},
                "targets": [{
                    "refId": "A",
                    "type": "json",
                    "source": "url",
                    "url": f"/grafana/modules/{module}/history?limit=100",
                    "url_options": {"method": "GET"},
                    "columns": [
                        {"selector": "timestamp", "text": "Data/Hora", "type": "timestamp"},
                        {"selector": "event_type", "text": "Tipo", "type": "string"},
                        {"selector": "message", "text": "Evento", "type": "string"},
                        {"selector": "id", "text": "ID", "type": "string"},
                    ],
                }],
            },
        ],
        "refresh": "30s",
        "schemaVersion": 39,
        "tags": ["ciem", "modulo", module],
        "time": {"from": "now-6h", "to": "now"},
        "title": f"CIEM — {label}",
        "uid": uid,
        "version": 1,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for module, meta in MODULES.items():
        path = OUT / f"ciem-module-{module}.json"
        path.write_text(json.dumps(build_dashboard(module, meta), indent=2), encoding="utf-8")
        print(f"Gerado: {path}")


if __name__ == "__main__":
    main()

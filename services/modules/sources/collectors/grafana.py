"""Coletor Grafana via HTTP API (alertas e anotações)."""

import os
from datetime import datetime, timedelta, timezone

import httpx

GRAFANA_URL = os.getenv("GRAFANA_URL", "").rstrip("/")
GRAFANA_API_KEY = os.getenv("GRAFANA_API_KEY", "")
ANNOTATION_DAYS = int(os.getenv("GRAFANA_ANNOTATION_DAYS", "30"))


async def collect_grafana(cfg: dict) -> list[dict]:
    if not all([GRAFANA_URL, GRAFANA_API_KEY]):
        print("[grafana] GRAFANA_URL e GRAFANA_API_KEY são obrigatórios")
        return []

    headers = {"Authorization": f"Bearer {GRAFANA_API_KEY}", "Content-Type": "application/json"}
    docs: list[dict] = []
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    from_ms = int((datetime.now(timezone.utc) - timedelta(days=ANNOTATION_DAYS)).timestamp() * 1000)

    async with httpx.AsyncClient(timeout=60.0, verify=True) as client:
        # Anotações (manutenções, eventos operacionais)
        ann_resp = await client.get(
            f"{GRAFANA_URL}/api/annotations",
            headers=headers,
            params={"from": from_ms, "to": now_ms + 86400000 * ANNOTATION_DAYS, "limit": 100},
        )
        if ann_resp.status_code == 200:
            for ann in ann_resp.json():
                text = (
                    f"Anotação Grafana: {ann.get('text', '')}\n"
                    f"Tags: {', '.join(ann.get('tags', []))}\n"
                    f"Início: {ann.get('time')}\n"
                    f"Término: {ann.get('timeEnd', 'N/A')}"
                )
                docs.append(
                    {
                        "id": f"grafana-ann-{ann.get('id')}",
                        "text": text,
                        "metadata": {"source": "grafana", "type": "annotation", "annotation_id": ann.get("id")},
                    }
                )

        # Alertas em estado firing (Grafana Unified Alerting)
        alert_resp = await client.get(
            f"{GRAFANA_URL}/api/alertmanager/grafana/api/v2/alerts",
            headers=headers,
        )
        if alert_resp.status_code == 200:
            alerts = alert_resp.json()
            if isinstance(alerts, list):
                for alert in alerts[:50]:
                    labels = alert.get("labels", {})
                    annotations = alert.get("annotations", {})
                    text = (
                        f"Alerta Grafana: {labels.get('alertname', 'sem nome')}\n"
                        f"Status: {alert.get('status', {}).get('state', 'unknown')}\n"
                        f"Instância: {labels.get('instance', labels.get('host', 'N/A'))}\n"
                        f"Resumo: {annotations.get('summary', annotations.get('description', ''))}"
                    )
                    fingerprint = alert.get("fingerprint", labels.get("alertname", "unknown"))
                    docs.append(
                        {
                            "id": f"grafana-alert-{fingerprint}",
                            "text": text,
                            "metadata": {"source": "grafana", "type": "alert"},
                        }
                    )

    return docs

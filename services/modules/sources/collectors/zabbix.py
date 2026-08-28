"""Coletor Zabbix via JSON-RPC API."""

import os
from datetime import datetime, timedelta, timezone

import httpx

ZABBIX_URL = os.getenv("ZABBIX_URL", "").rstrip("/")
ZABBIX_USER = os.getenv("ZABBIX_USER", "")
ZABBIX_PASSWORD = os.getenv("ZABBIX_PASSWORD", "")
MAINTENANCE_DAYS = int(os.getenv("ZABBIX_MAINTENANCE_DAYS", "30"))


async def _rpc(client: httpx.AsyncClient, method: str, params: dict, auth: str | None = None) -> dict:
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    if auth:
        payload["auth"] = auth
    resp = await client.post(f"{ZABBIX_URL}/api_jsonrpc.php", json=payload)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(data["error"].get("data", data["error"].get("message", "Zabbix API error")))
    return data.get("result", {})


async def collect_zabbix(cfg: dict) -> list[dict]:
    if not all([ZABBIX_URL, ZABBIX_USER, ZABBIX_PASSWORD]):
        print("[zabbix] ZABBIX_URL, ZABBIX_USER e ZABBIX_PASSWORD são obrigatórios")
        return []

    docs: list[dict] = []
    async with httpx.AsyncClient(timeout=60.0, verify=True) as client:
        auth = await _rpc(
            client,
            "user.login",
            {"username": ZABBIX_USER, "password": ZABBIX_PASSWORD},
        )
        if not isinstance(auth, str):
            raise RuntimeError("Falha na autenticação Zabbix")

        now = int(datetime.now(timezone.utc).timestamp())
        future = int((datetime.now(timezone.utc) + timedelta(days=MAINTENANCE_DAYS)).timestamp())

        maintenances = await _rpc(
            client,
            "maintenance.get",
            {
                "output": "extend",
                "selectHosts": ["host", "name"],
                "time_from": now,
                "time_till": future,
            },
            auth=auth,
        )
        if isinstance(maintenances, list):
            for m in maintenances:
                hosts = ", ".join(h.get("name", h.get("host", "")) for h in m.get("hosts", []))
                active_from = datetime.fromtimestamp(int(m.get("active_since", 0)), tz=timezone.utc).isoformat()
                active_till = datetime.fromtimestamp(int(m.get("active_till", 0)), tz=timezone.utc).isoformat()
                text = (
                    f"Manutenção Zabbix: {m.get('name', 'sem nome')}\n"
                    f"Hosts afetados: {hosts or 'não informado'}\n"
                    f"Início: {active_from}\n"
                    f"Término previsto: {active_till}\n"
                    f"Descrição: {m.get('description', '')}"
                )
                docs.append(
                    {
                        "id": f"zabbix-maint-{m.get('maintenanceid')}",
                        "text": text,
                        "metadata": {
                            "source": "zabbix",
                            "type": "maintenance",
                            "maintenance_id": m.get("maintenanceid"),
                        },
                    }
                )

        problems = await _rpc(
            client,
            "problem.get",
            {
                "output": ["eventid", "name", "severity", "clock"],
                "recent": True,
                "sortfield": ["eventid"],
                "sortorder": "DESC",
                "limit": 50,
            },
            auth=auth,
        )
        if isinstance(problems, list):
            for p in problems:
                since = datetime.fromtimestamp(int(p.get("clock", 0)), tz=timezone.utc).isoformat()
                text = (
                    f"Problema ativo Zabbix: {p.get('name')}\n"
                    f"Severidade: {p.get('severity')}\n"
                    f"Desde: {since}"
                )
                docs.append(
                    {
                        "id": f"zabbix-problem-{p.get('eventid')}",
                        "text": text,
                        "metadata": {"source": "zabbix", "type": "problem", "event_id": p.get("eventid")},
                    }
                )

        await _rpc(client, "user.logout", [], auth=auth)

    return docs

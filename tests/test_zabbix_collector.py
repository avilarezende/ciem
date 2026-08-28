"""Testes do coletor Zabbix."""

import httpx
import pytest
import respx

from collectors.zabbix import collect_zabbix


@pytest.mark.asyncio
@respx.mock
async def test_collect_zabbix_maintenance(monkeypatch):
    monkeypatch.setenv("ZABBIX_URL", "https://zabbix.test")
    monkeypatch.setenv("ZABBIX_USER", "api")
    monkeypatch.setenv("ZABBIX_PASSWORD", "secret")

    import importlib
    import collectors.zabbix as zmod

    importlib.reload(zmod)

    def rpc_response(request: httpx.Request) -> httpx.Response:
        body = request.read().decode()
        if "user.login" in body:
            return httpx.Response(200, json={"jsonrpc": "2.0", "result": "token123", "id": 1})
        if "maintenance.get" in body:
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "result": [
                        {
                            "maintenanceid": "1",
                            "name": "Manutenção IFS",
                            "active_since": "1700000000",
                            "active_till": "1700086400",
                            "description": "Troca de fibra",
                            "hosts": [{"name": "ifs-link-principal"}],
                        }
                    ],
                    "id": 1,
                },
            )
        if "problem.get" in body:
            return httpx.Response(200, json={"jsonrpc": "2.0", "result": [], "id": 1})
        if "user.logout" in body:
            return httpx.Response(200, json={"jsonrpc": "2.0", "result": True, "id": 1})
        return httpx.Response(200, json={"jsonrpc": "2.0", "result": [], "id": 1})

    respx.post("https://zabbix.test/api_jsonrpc.php").mock(side_effect=rpc_response)

    docs = await zmod.collect_zabbix({})
    assert len(docs) >= 1
    assert "Manutenção IFS" in docs[0]["text"]

"""Coletor CIEM para sistema de inventário via API REST genérica."""

import os
from datetime import UTC, datetime
from typing import Any

import httpx

from ciem_common import (
    ActiveAlarm,
    CollectorModule,
    CollectResponse,
    HistoryEvent,
    create_collector_app,
    load_config,
)

MODULE_NAME = "inventory"


def _resolve_path(data: Any, path: str) -> Any:
    if not path:
        return data
    current = data
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


class InventoryCollector(CollectorModule):
    name = MODULE_NAME

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def _build_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        auth_type = self.config.get("auth_type", "none")
        if auth_type == "bearer":
            token = self.config.get("token") or os.getenv("INVENTORY_TOKEN", "")
            if token:
                headers["Authorization"] = f"Bearer {token}"
        elif auth_type == "api_key":
            token = self.config.get("token") or os.getenv("INVENTORY_API_KEY", "")
            header_name = self.config.get("api_key_header", "X-API-Key")
            if token:
                headers[header_name] = token
        return headers

    def _build_auth(self) -> httpx.Auth | None:
        if self.config.get("auth_type") == "basic":
            username = self.config.get("username") or os.getenv("INVENTORY_USERNAME", "")
            password = self.config.get("password") or os.getenv("INVENTORY_PASSWORD", "")
            if username and password:
                return httpx.BasicAuth(username, password)
        return None

    async def _collect_live(self) -> CollectResponse:
        url = self.config.get("url", "").strip().rstrip("/")
        endpoint = self.config.get("assets_endpoint", "/assets")
        if not url:
            raise ValueError("url é obrigatória")

        timeout = float(self.config.get("timeout", 60))
        verify = bool(self.config.get("verify_ssl", True))
        item_limit = int(self.config.get("item_limit", 100))
        mapping = self.config.get("field_mapping", {})

        active_alarms: list[ActiveAlarm] = []
        history_events: list[HistoryEvent] = []

        async with httpx.AsyncClient(
            timeout=timeout,
            verify=verify,
            headers=self._build_headers(),
            auth=self._build_auth(),
        ) as client:
            response = await client.get(f"{url}{endpoint}")
            response.raise_for_status()
            payload = response.json()
            items = _resolve_path(payload, self.config.get("items_path", "")) or payload

            if not isinstance(items, list):
                raise RuntimeError("Resposta da API de inventário não contém uma lista de itens")

            for item in items[:item_limit]:
                if not isinstance(item, dict):
                    continue
                item_id = str(item.get(mapping.get("id", "id"), "unknown"))
                name = str(item.get(mapping.get("name", "name"), "Ativo sem nome"))
                status = str(item.get(mapping.get("status", "status"), "unknown"))
                location = str(item.get(mapping.get("location", "location"), ""))

                history_events.append(
                    HistoryEvent(
                        id=f"inventory-asset-{item_id}",
                        event_type="asset",
                        message=f"Ativo de inventário: {name} (status: {status})",
                        timestamp=datetime.now(UTC).isoformat(),
                        metadata={"asset_id": item_id, "status": status, "location": location},
                    )
                )

                if status.lower() in ("offline", "down", "retired", "missing", "faulty"):
                    active_alarms.append(
                        ActiveAlarm(
                            id=f"inventory-alarm-{item_id}",
                            severity="medium",
                            message=f"Ativo {name} com status crítico: {status}",
                            source=MODULE_NAME,
                            timestamp=datetime.now(UTC).isoformat(),
                            metadata={"asset_id": item_id, "status": status, "location": location},
                        )
                    )

        return CollectResponse.build(
            MODULE_NAME, "ok", active_alarms=active_alarms, history_events=history_events
        )

    def _mock_response(self) -> CollectResponse:
        now = datetime.now(UTC).isoformat()
        return CollectResponse.build(
            MODULE_NAME,
            "degraded",
            active_alarms=[
                ActiveAlarm(
                    id="inventory-mock-alarm-1",
                    severity="medium",
                    message="[MOCK] Ativo srv-legacy-03 com status offline",
                    source=MODULE_NAME,
                    timestamp=now,
                    metadata={"mock": True, "asset_id": "A-103"},
                )
            ],
            history_events=[
                HistoryEvent(
                    id="inventory-mock-asset-1",
                    event_type="asset",
                    message="[MOCK] Ativo de inventário: switch-core-01 (status: active)",
                    timestamp=now,
                    metadata={"mock": True, "asset_id": "A-001"},
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
collector = InventoryCollector(config)
app = create_collector_app(collector)

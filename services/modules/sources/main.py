"""Orquestrador de coleta periódica das fontes RAG."""

import asyncio
import os
from pathlib import Path

import yaml

from collectors import COLLECTORS
from shared.popse_common.engine_client import ingest_rag

CONFIG_PATH = Path(os.getenv("CONFIG_PATH", "/app/config"))
INTERVAL = int(os.getenv("SOURCES_SYNC_INTERVAL", "600"))

# Mapeia fonte → coleção vetorial no Chroma
COLLECTION_MAP = {
    "popse_site": "institucional",
    "zabbix": "manutencoes",
    "cacti": "operacional",
    "grafana": "operacional",
    "mrtg": "operacional",
    "topdesk": "operacional",
}


def load_sources() -> dict:
    with (CONFIG_PATH / "sources.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


async def sync_all() -> None:
    cfg = load_sources()
    modules = yaml.safe_load((CONFIG_PATH / "modules.yaml").read_text(encoding="utf-8"))
    enabled = modules.get("fontes_rag", {})

    for name, meta in enabled.items():
        if not meta.get("enabled"):
            continue
        collector = COLLECTORS.get(name)
        if not collector:
            print(f"[sources] Coletor não implementado: {name}")
            continue
        source_cfg = cfg.get("fontes", {}).get(name, {})
        try:
            docs = await collector(source_cfg)
        except Exception as exc:
            print(f"[sources] Erro em {name}: {exc}")
            continue
        if not docs:
            print(f"[sources] {name}: nenhum documento coletado")
            continue
        collection = COLLECTION_MAP.get(name, "operacional")
        count = await ingest_rag(collection, docs)
        print(f"[sources] {name}: ingeridos {count} documentos em '{collection}'")


async def loop_forever() -> None:
    while True:
        try:
            await sync_all()
        except Exception as exc:
            print(f"[sources] Erro geral: {exc}")
        await asyncio.sleep(INTERVAL)


if __name__ == "__main__":
    asyncio.run(loop_forever())

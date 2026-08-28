"""Cliente HTTP para o engine de conversação."""

import os

import httpx

ENGINE_URL = os.getenv("ENGINE_URL", "http://engine:8000")


async def send_chat(message: str, user_id: str, channel: str) -> str:
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{ENGINE_URL}/api/v1/chat",
            json={"message": message, "user_id": user_id, "channel": channel},
        )
        resp.raise_for_status()
        return resp.json()["reply"]


async def ingest_rag(collection: str, documents: list[dict]) -> int:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{ENGINE_URL}/api/v1/rag/ingest",
            json={"collection": collection, "documents": documents},
        )
        resp.raise_for_status()
        return resp.json()["ingested"]

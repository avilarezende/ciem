"""Módulo WhatsApp — webhook para APIs compatíveis (Evolution API, etc.)."""

import os

import httpx
from fastapi import FastAPI, Request

from shared.popse_common.engine_client import send_chat

app = FastAPI(title="Conversador PoP-SE — WhatsApp")
WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL", "")
WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN", "")


@app.post("/webhook/whatsapp")
async def webhook(request: Request) -> dict:
    payload = await request.json()
    # Adaptar conforme provedor WhatsApp escolhido
    from_number = payload.get("from", payload.get("sender", "unknown"))
    text = payload.get("text", payload.get("message", ""))
    if not text:
        return {"status": "ignored"}

    user_id = f"whatsapp:{from_number}"
    reply = await send_chat(text, user_id, "whatsapp")

    if WHATSAPP_API_URL:
        async with httpx.AsyncClient() as client:
            await client.post(
                WHATSAPP_API_URL,
                headers={"Authorization": f"Bearer {WHATSAPP_API_TOKEN}"},
                json={"to": from_number, "text": reply},
            )
    return {"status": "ok", "reply": reply}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8090)

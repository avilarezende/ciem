"""Coleta e-mails Microsoft 365 via Graph API para RAG."""

import asyncio
import os
import time

import httpx
import msal

from shared.popse_common.engine_client import ingest_rag

TENANT = os.environ["MS_TENANT_ID"]
CLIENT_ID = os.environ["MS_CLIENT_ID"]
CLIENT_SECRET = os.environ["MS_CLIENT_SECRET"]
MAILBOX = os.environ.get("MS_MAILBOX", "info@pop-se.rnp.br")
INTERVAL = int(os.getenv("EMAIL_SYNC_INTERVAL", "900"))


def get_token() -> str:
    app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{TENANT}",
        client_credential=CLIENT_SECRET,
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in result:
        raise RuntimeError(result.get("error_description", "Falha ao obter token Graph"))
    return result["access_token"]


async def fetch_messages() -> list[dict]:
    token = get_token()
    url = f"https://graph.microsoft.com/v1.0/users/{MAILBOX}/messages"
    params = {
        "$top": 50,
        "$select": "id,subject,bodyPreview,receivedDateTime,from",
        "$orderby": "receivedDateTime desc",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(url, headers={"Authorization": f"Bearer {token}"}, params=params)
        resp.raise_for_status()
        items = resp.json().get("value", [])

    docs = []
    for msg in items:
        subject = msg.get("subject", "")
        preview = msg.get("bodyPreview", "")
        text = f"Assunto: {subject}\n{preview}"
        docs.append(
            {
                "id": f"email-{msg['id']}",
                "text": text,
                "metadata": {
                    "source": "email_microsoft",
                    "received": msg.get("receivedDateTime"),
                    "subject": subject,
                },
            }
        )
    return docs


async def sync_once() -> None:
    docs = await fetch_messages()
    if docs:
        count = await ingest_rag("manutencoes", docs)
        print(f"Ingeridos {count} e-mails na coleção manutencoes")


async def loop_forever() -> None:
    while True:
        try:
            await sync_once()
        except Exception as exc:
            print(f"Erro na sincronização de e-mail: {exc}")
        await asyncio.sleep(INTERVAL)


if __name__ == "__main__":
    asyncio.run(loop_forever())

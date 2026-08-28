"""Coletor Cacti via autenticação web e extração de hosts/gráficos."""

import os
import re

import httpx
from bs4 import BeautifulSoup

CACTI_URL = os.getenv("CACTI_URL", "").rstrip("/")
CACTI_USER = os.getenv("CACTI_USER", "")
CACTI_PASSWORD = os.getenv("CACTI_PASSWORD", "")


async def _login(client: httpx.AsyncClient) -> bool:
    login_page = await client.get(f"{CACTI_URL}/index.php")
    login_page.raise_for_status()
    soup = BeautifulSoup(login_page.text, "lxml")
    csrf = soup.find("input", {"name": "__csrf_magic"})
    csrf_val = csrf["value"] if csrf else ""

    resp = await client.post(
        f"{CACTI_URL}/index.php",
        data={
            "action": "login",
            "login_username": CACTI_USER,
            "login_password": CACTI_PASSWORD,
            "__csrf_magic": csrf_val,
        },
        follow_redirects=True,
    )
    return "logout" in resp.text.lower() or resp.status_code == 200


async def collect_cacti(cfg: dict) -> list[dict]:
    if not all([CACTI_URL, CACTI_USER, CACTI_PASSWORD]):
        print("[cacti] CACTI_URL, CACTI_USER e CACTI_PASSWORD são obrigatórios")
        return []

    docs: list[dict] = []
    async with httpx.AsyncClient(timeout=60.0, verify=True, follow_redirects=True) as client:
        if not await _login(client):
            print("[cacti] Falha no login")
            return []

        host_resp = await client.get(f"{CACTI_URL}/host.php", params={"filter": "", "page": "1"})
        host_resp.raise_for_status()
        soup = BeautifulSoup(host_resp.text, "lxml")

        rows = soup.select("table.cactiTable tbody tr") or soup.select("table tbody tr")
        for row in rows[:80]:
            cols = [c.get_text(" ", strip=True) for c in row.find_all("td")]
            if len(cols) < 2:
                continue
            hostname = cols[1] if len(cols) > 1 else cols[0]
            status = cols[-1] if cols else "desconhecido"
            if not hostname or hostname.lower() in ("description", "hostname"):
                continue
            text = f"Host Cacti: {hostname}\nStatus/última coleta: {status}"
            host_id_match = re.search(r"host_id=(\d+)", str(row))
            host_id = host_id_match.group(1) if host_id_match else hostname
            docs.append(
                {
                    "id": f"cacti-host-{host_id}",
                    "text": text,
                    "metadata": {"source": "cacti", "type": "host", "host_id": host_id},
                }
            )

        graph_resp = await client.get(f"{CACTI_URL}/graph_view.php")
        if graph_resp.status_code == 200:
            graph_soup = BeautifulSoup(graph_resp.text, "lxml")
            graph_links = graph_soup.select("a[href*='graph_id=']")[:30]
            for link in graph_links:
                title = link.get_text(strip=True) or "gráfico"
                graph_id_match = re.search(r"graph_id=(\d+)", link.get("href", ""))
                if not graph_id_match:
                    continue
                gid = graph_id_match.group(1)
                docs.append(
                    {
                        "id": f"cacti-graph-{gid}",
                        "text": f"Gráfico Cacti: {title} (graph_id={gid})",
                        "metadata": {"source": "cacti", "type": "graph", "graph_id": gid},
                    }
                )

    return docs

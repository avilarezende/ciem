"""Coletor do site institucional PoP-SE."""

import httpx
from bs4 import BeautifulSoup


async def collect_popse_site(cfg: dict) -> list[dict]:
    url = cfg.get("url", "https://www.pop-se.rnp.br")
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    text = soup.get_text("\n", strip=True)
    chunks = [text[i : i + 800] for i in range(0, min(len(text), 12000), 800)]
    return [
        {
            "id": f"popse-site-{i}",
            "text": chunk,
            "metadata": {"source": "popse_site", "url": url},
        }
        for i, chunk in enumerate(chunks)
    ]

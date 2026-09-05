"""Testes da wiki colaborativa (API + markup do portal)."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
PORTAL = ROOT / "services" / "portal" / "public"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    import os

    cfg = tmp_path / "config"
    cfg.mkdir()
    for name in ("main.yaml", "auth.yaml", "modules.yaml", "ai.yaml", "targets.yaml"):
        src = ROOT / "config" / name
        if src.is_file():
            (cfg / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    (cfg / "wiki.yaml").write_text(
        (
            "wiki:\n"
            "  title: Wiki teste\n"
            "  pages:\n"
            "    - id: rede\n"
            "      title: Rede\n"
            "      body: '## Rede\\n'\n"
            "      updated_by: system\n"
            "      updated_at: '2026-01-01T00:00:00Z'\n"
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CONFIG_PATH", str(cfg))
    os.environ["CONFIG_PATH"] = str(cfg)

    from ciem_common.config_loader import clear_config_cache

    clear_config_cache()

    from app.main import app

    return TestClient(app)


def _login(client: TestClient, username: str = "admin", password: str = "admin123") -> str:
    resp = client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


def test_wiki_get_requires_auth(client: TestClient):
    assert client.get("/wiki").status_code in (401, 403)


def test_wiki_crud_flow(client: TestClient):
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    got = client.get("/wiki", headers=headers)
    assert got.status_code == 200
    data = got.json()
    assert data["title"]
    assert any(p["id"] == "rede" for p in data["pages"])

    created = client.post(
        "/wiki/pages",
        headers=headers,
        json={"title": "DHCP", "body": "## DHCP\n\n- Escopo A\n"},
    )
    assert created.status_code == 200, created.text
    page = created.json()
    assert page["id"]
    assert page["title"] == "DHCP"
    assert "DHCP" in page["body"]

    updated = client.put(
        f"/wiki/pages/{page['id']}",
        headers=headers,
        json={"title": "DHCP institucional", "body": "## Atualizado\n"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "DHCP institucional"
    assert updated.json()["updated_by"] == "admin"

    deleted = client.delete(f"/wiki/pages/{page['id']}", headers=headers)
    assert deleted.status_code == 200


def test_portal_wiki_and_reminder_markup():
    html = (PORTAL / "index.html").read_text(encoding="utf-8")
    js = (PORTAL / "js" / "portal.js").read_text(encoding="utf-8")
    css = (PORTAL / "css" / "style.css").read_text(encoding="utf-8")

    for element_id in (
        "reminder-widget",
        "reminder-drag-handle",
        "wiki-tab",
        "wiki-drawer",
        "wiki-page-list",
        "wiki-editor",
        "wiki-view",
        "btn-open-wiki",
        "calendar-tab",
        "calendar-drawer",
        "btn-open-calendar",
    ):
        assert f'id="{element_id}"' in html, element_id

    assert "Lembretes / Anotações" in html
    assert "function initWikiDrawer" in js
    assert "function setWikiOpen" in js
    assert "function initReminders" in js
    assert "function initCalendarDrawer" in js
    assert ".wiki-drawer" in css
    assert ".wiki-edge-tab" in css
    assert "body.wiki-open" in css
    assert (ROOT / "config" / "wiki.yaml").is_file()

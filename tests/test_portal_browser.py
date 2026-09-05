"""Testes estáticos e de comportamento do Navegador HTML5 do portal."""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import pytest

ROOT = Path(__file__).resolve().parents[1]
PORTAL = ROOT / "services" / "portal" / "public"
INDEX = PORTAL / "index.html"
JS = PORTAL / "js" / "portal.js"
CSS = PORTAL / "css" / "style.css"

BROWSER_HOME = "ciem://home"


def normalize_browser_url(raw: str) -> str:
    """Espelho de normalizeBrowserUrl em portal.js."""
    value = str(raw or "").strip()
    if not value or value == BROWSER_HOME or value == "about:blank":
        return BROWSER_HOME
    if re.match(r"^https?://", value, re.I):
        return value
    if value.startswith("/"):
        return value
    if value.startswith("ciem://"):
        return value
    return f"https://{value}"


def is_likely_embeddable(url: str, origin: str = "https://ciem.local") -> bool:
    if not url or url == BROWSER_HOME:
        return True
    if url.startswith("/"):
        return True
    try:
        u = urlparse(url if "://" in url else f"{origin}{url}")
        o = urlparse(origin)
        return u.scheme == o.scheme and u.netloc == o.netloc
    except Exception:
        return False


@pytest.fixture(scope="module")
def index_html() -> str:
    return INDEX.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def portal_js() -> str:
    return JS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def portal_css() -> str:
    return CSS.read_text(encoding="utf-8")


def test_sidebar_has_browser_nav_for_everyone(index_html: str):
    assert 'data-panel="browser"' in index_html
    assert "Navegador" in index_html
    browser_btn = re.search(r'<button[^>]*data-panel="browser"[^>]*>', index_html)
    assert browser_btn, "botão Navegador ausente"
    assert "admin-only" not in browser_btn.group(0)


def test_browser_panel_chrome(index_html: str):
    for element_id in (
        "panel-browser",
        "browser-url-form",
        "browser-url",
        "browser-back",
        "browser-forward",
        "browser-reload",
        "browser-home",
        "browser-open-ext",
        "browser-presets",
        "browser-home-view",
        "browser-frame",
        "browser-blocked",
        "browser-blocked-open",
        "browser-home-cards",
    ):
        assert f'id="{element_id}"' in index_html, element_id


def test_iframe_present_without_restrictive_sandbox(index_html: str):
    m = re.search(r'<iframe[^>]*id="browser-frame"[^>]*>', index_html)
    assert m
    tag = m.group(0)
    if "sandbox=" in tag:
        assert "allow-scripts" in tag
        assert "allow-same-origin" in tag


def test_shortcuts_to_browser_from_dashboard_and_analysis(index_html: str):
    assert 'data-goto="browser"' in index_html
    assert 'data-browser-url="/grafana/"' in index_html
    assert "btn-guacamole-browser" in index_html or 'id="btn-guacamole-browser"' in index_html


def test_js_browser_api_surface(portal_js: str):
    for name in (
        "normalizeBrowserUrl",
        "browserNavigate",
        "browserBack",
        "browserForward",
        "browserReload",
        "openBrowserPanel",
        "refreshBrowserPresets",
        "activateBrowserPreset",
        "PAGE_META",
        "BROWSER_HOME",
    ):
        assert name in portal_js, name
    assert "browser:" in portal_js
    assert "browser-focus" in portal_js


def test_css_browser_layout(portal_css: str):
    for sel in (
        ".panel-browser",
        ".browser-chrome",
        ".browser-toolbar",
        ".browser-stage",
        ".browser-frame",
        ".browser-home",
        ".browser-focus",
    ):
        assert sel in portal_css, sel


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("", BROWSER_HOME),
        ("  ", BROWSER_HOME),
        (BROWSER_HOME, BROWSER_HOME),
        ("about:blank", BROWSER_HOME),
        ("/grafana/", "/grafana/"),
        ("https://zabbix.local/ui", "https://zabbix.local/ui"),
        ("HTTP://Example.COM", "HTTP://Example.COM"),
        ("grafana.local/dash", "https://grafana.local/dash"),
        ("ciem://custom", "ciem://custom"),
    ],
)
def test_normalize_browser_url(raw: str, expected: str):
    assert normalize_browser_url(raw) == expected


def test_embeddable_heuristics():
    assert is_likely_embeddable("/grafana/")
    assert is_likely_embeddable(BROWSER_HOME)
    assert is_likely_embeddable("https://ciem.local/guacamole/", "https://ciem.local")
    assert not is_likely_embeddable("https://zabbix.exemplo.local/", "https://ciem.local")


def test_docs_and_assets_mention_browser():
    portal_md = (ROOT / "docs" / "PORTAL.md").read_text(encoding="utf-8")
    assert "Navegador HTML5" in portal_md
    assert "ciem-portal-browser" in portal_md
    assert (ROOT / "docs" / "assets" / "ciem-portal-browser.jpg").is_file()
    assert (ROOT / "docs" / "assets" / "ciem-architecture-diagram.png").is_file()

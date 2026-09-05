"""Testes do painel de lembretes arrastável e da aba de calendário."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PORTAL = ROOT / "services" / "portal" / "public"
INDEX = PORTAL / "index.html"
JS = PORTAL / "js" / "portal.js"
CSS = PORTAL / "css" / "style.css"


@pytest.fixture(scope="module")
def index_html() -> str:
    return INDEX.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def portal_js() -> str:
    return JS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def portal_css() -> str:
    return CSS.read_text(encoding="utf-8")


def test_reminder_widget_markup(index_html: str):
    for element_id in (
        "reminder-widget",
        "reminder-drag-handle",
        "reminder-minimize",
        "reminder-close",
        "reminder-list",
        "reminder-form",
        "reminder-input",
        "reminder-reopen",
    ):
        assert f'id="{element_id}"' in index_html, element_id
    assert 'aria-label="Lembretes"' in index_html


def test_calendar_drawer_markup(index_html: str):
    for element_id in (
        "calendar-tab",
        "calendar-backdrop",
        "calendar-drawer",
        "calendar-close",
        "calendar-empty",
        "calendar-frame",
        "calendar-setup",
        "calendar-google-url",
        "calendar-ms-url",
        "calendar-clear",
        "btn-open-calendar",
    ):
        assert f'id="{element_id}"' in index_html, element_id
    assert 'data-cal-provider="google"' in index_html
    assert 'data-cal-provider="microsoft"' in index_html
    assert 'data-cal-provider="setup"' in index_html


def test_js_reminder_and_calendar_api(portal_js: str):
    for name in (
        "initReminders",
        "bindReminderDrag",
        "renderReminders",
        "addReminder",
        "initCalendarDrawer",
        "setCalendarOpen",
        "setCalendarProvider",
        "isSafeCalendarEmbedUrl",
    ):
        assert f"function {name}" in portal_js, name
    assert "ciem_reminders" in portal_js
    assert "ciem_calendar_google_url" in portal_js
    assert "calendar.google.com" in portal_js
    assert "outlook.office.com" in portal_js


def test_css_reminder_and_calendar_layout(portal_css: str):
    for sel in (
        ".reminder-widget",
        ".reminder-widget-head",
        ".reminder-widget.is-dragging",
        ".reminder-widget.is-minimized",
        ".calendar-edge-tab",
        ".calendar-drawer",
        ".calendar-drawer.is-open",
        ".calendar-backdrop",
        "body.calendar-open",
    ):
        assert sel in portal_css, sel


@pytest.mark.parametrize(
    "url,ok",
    [
        ("https://calendar.google.com/calendar/embed?src=x", True),
        ("https://outlook.office.com/calendar/published/abc", True),
        ("https://outlook.live.com/calendar/0/view", True),
        ("http://calendar.google.com/calendar/embed?src=x", False),
        ("https://evil.example/calendar", False),
        ("javascript:alert(1)", False),
    ],
)
def test_calendar_url_allowlist_mirror(url: str, ok: bool):
    """Espelho da allowlist de isSafeCalendarEmbedUrl."""
    from urllib.parse import urlparse

    try:
        u = urlparse(url)
        if u.scheme != "https":
            assert ok is False
            return
        host = (u.hostname or "").lower()
        allowed = (
            "calendar.google.com",
            "www.google.com",
            "outlook.office.com",
            "outlook.office365.com",
            "outlook.live.com",
            "calendars.office.com",
        )
        safe = any(host == h or host.endswith(f".{h}") for h in allowed)
        assert safe is ok
    except Exception:
        assert ok is False


def test_init_portal_wires_widgets(portal_js: str):
    assert re.search(r"function initPortal\([\s\S]*initReminders\(", portal_js)
    assert re.search(r"function initPortal\([\s\S]*initCalendarDrawer\(", portal_js)

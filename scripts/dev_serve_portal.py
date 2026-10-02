#!/usr/bin/env python3
"""Sobe portal estático + API core em /api (dev sem Docker/nginx)."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    os.environ.setdefault("CONFIG_PATH", str(ROOT / "config"))
    os.environ.setdefault("PYTHONPATH", f"{ROOT / 'shared'}:{ROOT / 'services' / 'core'}")
    # Garante imports do core
    import sys

    sys.path[:0] = [str(ROOT / "shared"), str(ROOT / "services" / "core")]

    from app.main import app as core_app  # noqa: E402

    app = FastAPI(title="CIEM Dev")
    app.mount("/api", core_app)
    app.mount(
        "/",
        StaticFiles(directory=str(ROOT / "services" / "portal" / "public"), html=True),
        name="portal",
    )
    host = os.environ.get("CIEM_HOST", "0.0.0.0")
    port = int(os.environ.get("CIEM_PORT", "8080"))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()

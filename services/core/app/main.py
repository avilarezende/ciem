"""Aplicação FastAPI principal do CIEM Core."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from pydantic import BaseModel, Field

from app.aggregators import MODULE_URLS, aggregate_alarms, aggregate_history, aggregate_modules
from app.config import settings
from app.deps import require_admin, require_user
from app.grafana_routes import refresh_prometheus_metrics
from app.grafana_routes import router as grafana_router
from app.sessions_store import pop_session, start_session_record
from app.sso_routes import router as sso_router
from ciem_common.audit import log_session, read_sessions
from ciem_common.auth import User, authenticate
from ciem_common.config_loader import (
    clear_config_cache,
    is_module_enabled,
    load_main_config,
    load_modules_config,
)
from ciem_common.interfaces import SessionRecord
from ciem_common.sso import guacamole_client_id
from ciem_common.targets_loader import load_targets_config

REQUEST_COUNT = Counter("ciem_requests_total", "Requisições HTTP", ["method", "endpoint"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str
    role: str
    display_name: str | None = None


class SessionStartRequest(BaseModel):
    target_id: str
    protocol: str = "ssh"


class SessionEndRequest(BaseModel):
    session_id: str
    commands: list[str] = Field(default_factory=list)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    clear_config_cache()


app = FastAPI(
    title="CIEM Core",
    description="Centro Integrado de Estatística e Manutenção — API ZTNA",
    version=settings.version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(grafana_router)
app.include_router(sso_router)


@app.middleware("http")
async def count_requests(request, call_next):
    response = await call_next(request)
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    return response


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "ciem-core", "version": settings.version}


@app.get("/info")
async def info() -> dict[str, Any]:
    main = load_main_config()
    return {
        "platform": main.platform_name,
        "version": settings.version,
        "environment": main.environment,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.post("/auth/login", response_model=LoginResponse)
async def login(body: LoginRequest) -> LoginResponse:
    user = authenticate(body.username, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
        )
    return LoginResponse(
        token=f"ciem-{user.username}",
        username=user.username,
        role=user.role.value,
        display_name=user.display_name,
    )


@app.get("/config/modules")
async def get_modules_config(user: User = Depends(require_user)) -> dict[str, Any]:
    modules_cfg = load_modules_config()
    return {
        name: {"enabled": entry.enabled, "description": entry.description, "options": entry.options}
        for name, entry in modules_cfg.modules.items()
    }


@app.get("/config/main")
async def get_main_config(user: User = Depends(require_admin)) -> dict[str, Any]:
    return load_main_config().model_dump()


@app.get("/targets")
async def list_targets(user: User = Depends(require_admin)) -> list[dict[str, Any]]:
    cfg = load_targets_config()
    return [
        {
            "id": t.id,
            "name": t.name,
            "hostname": t.hostname,
            "port": t.port,
            "protocol": t.protocol,
            "enabled": t.enabled,
            "description": t.description,
            "tags": t.tags,
        }
        for t in cfg.targets
    ]


@app.get("/modules/status")
async def modules_status(user: User = Depends(require_user)) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        return await aggregate_modules(client)


@app.post("/modules/{module_name}/collect")
async def trigger_collect(module_name: str, user: User = Depends(require_user)) -> dict[str, Any]:
    if not is_module_enabled(module_name):
        raise HTTPException(status_code=404, detail=f"Módulo '{module_name}' desabilitado")
    url = MODULE_URLS.get(module_name)
    if not url:
        raise HTTPException(status_code=404, detail=f"Módulo '{module_name}' não encontrado")
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(f"{url}/collect")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Falha na coleta: {exc}") from exc


@app.get("/alarms/active")
async def active_alarms(user: User = Depends(require_user)) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        return await aggregate_alarms(client)


@app.get("/history")
async def history(user: User = Depends(require_user), limit: int = 100) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        events = await aggregate_history(client)
    return events[:limit]


@app.post("/sessions/start")
async def start_session(
    body: SessionStartRequest,
    user: User = Depends(require_admin),
) -> dict[str, Any]:
    cfg = load_targets_config()
    target = next((t for t in cfg.targets if t.id == body.target_id), None)
    if not target or not target.enabled:
        raise HTTPException(status_code=404, detail=f"Alvo '{body.target_id}' não encontrado")

    session_id = f"sess-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{user.username}"
    record = SessionRecord(
        session_id=session_id,
        user=user.username,
        target_host=target.hostname,
        protocol=body.protocol,
        started_at=datetime.now(UTC),
    )
    start_session_record(session_id, record)
    client_id = guacamole_client_id(target.name)
    return {
        "session_id": session_id,
        "status": "started",
        "target_name": target.name,
        "guacamole_url": f"/guacamole/#/client/{client_id}",
    }


@app.post("/sessions/end")
async def end_session(
    body: SessionEndRequest,
    user: User = Depends(require_admin),
) -> dict[str, str]:
    session = pop_session(body.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    record: SessionRecord = session["record"]
    ended_at = datetime.now(UTC)
    started = (
        record.started_at
        if isinstance(record.started_at, datetime)
        else datetime.fromisoformat(str(record.started_at))
    )
    duration = (ended_at - started).total_seconds()
    record.ended_at = ended_at
    record.commands = body.commands or session.get("commands", [])
    record.duration_seconds = duration
    log_session(record)
    return {
        "status": "ended",
        "session_id": body.session_id,
        "duration_seconds": str(int(duration)),
    }


@app.get("/sessions/audit")
async def audit_log(user: User = Depends(require_admin), limit: int = 50) -> list[dict[str, Any]]:
    return read_sessions(limit=limit)


@app.get("/metrics")
async def metrics() -> PlainTextResponse:
    await refresh_prometheus_metrics()
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

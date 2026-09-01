"""Aplicação FastAPI principal do CIEM Core."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from pydantic import BaseModel, Field

from app.config import settings
from ciem_common.audit import log_session, read_sessions
from ciem_common.auth import User, authenticate
from ciem_common.config_loader import (
    clear_config_cache,
    is_module_enabled,
    load_auth_config,
    load_main_config,
    load_modules_config,
)
from ciem_common.interfaces import SessionRecord, UserRole

REQUEST_COUNT = Counter("ciem_requests_total", "Requisições HTTP", ["method", "endpoint"])

# Mapeamento módulo → URL interna do container (rede Docker/K8s)
MODULE_URLS: dict[str, str] = {
    "zabbix": "http://module-zabbix:8080",
    "cacti": "http://module-cacti:8080",
    "nagios": "http://module-nagios:8080",
    "topdesk": "http://module-topdesk:8080",
    "inventory": "http://module-inventory:8080",
    "syslog": "http://module-syslog:8080",
}

security = HTTPBearer(auto_error=False)
_active_sessions: dict[str, dict[str, Any]] = {}


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


def _require_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> User:
    if not credentials or not credentials.credentials.startswith("ciem-"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    username = credentials.credentials.removeprefix("ciem-")
    auth_cfg = load_auth_config()
    for entry in auth_cfg.local_users:
        if entry.username == username and entry.enabled:
            return User(
                username=entry.username,
                role=UserRole.ADMIN if entry.role == "admin" else UserRole.OBSERVER,
                auth_source="local",
            )
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")


def _require_admin(user: User = Depends(_require_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores",
        )
    return user


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
async def get_modules_config(user: User = Depends(_require_user)) -> dict[str, Any]:
    modules_cfg = load_modules_config()
    return {
        name: {"enabled": entry.enabled, "description": entry.description, "options": entry.options}
        for name, entry in modules_cfg.modules.items()
    }


@app.get("/config/main")
async def get_main_config(user: User = Depends(_require_admin)) -> dict[str, Any]:
    return load_main_config().model_dump()


@app.get("/modules/status")
async def modules_status(user: User = Depends(_require_user)) -> list[dict[str, Any]]:
    results = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, url in MODULE_URLS.items():
            enabled = is_module_enabled(name)
            status_info: dict[str, Any] = {"module": name, "enabled": enabled, "url": url}
            if enabled:
                try:
                    resp = await client.get(f"{url}/health")
                    if resp.status_code == 200:
                        status_info["health"] = resp.json()
                    else:
                        status_info["health"] = {"status": "error"}
                except httpx.HTTPError:
                    status_info["health"] = {"status": "unreachable"}
            results.append(status_info)
    return results


@app.post("/modules/{module_name}/collect")
async def trigger_collect(module_name: str, user: User = Depends(_require_user)) -> dict[str, Any]:
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
async def active_alarms(user: User = Depends(_require_user)) -> list[dict[str, Any]]:
    """Agrega alarmes ativos de todos os módulos habilitados."""
    alarms: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        for name, url in MODULE_URLS.items():
            if not is_module_enabled(name):
                continue
            try:
                resp = await client.post(f"{url}/collect")
                if resp.status_code == 200:
                    data = resp.json()
                    for alarm in data.get("active_alarms", []):
                        alarm["source_module"] = name
                        alarms.append(alarm)
            except httpx.HTTPError:
                continue
    severity_order = {"critical": 0, "high": 1, "warning": 2, "info": 3}
    alarms.sort(key=lambda a: severity_order.get(a.get("severity", "info"), 99))
    return alarms


@app.get("/history")
async def history(user: User = Depends(_require_user), limit: int = 100) -> list[dict[str, Any]]:
    """Agrega histórico de eventos de todos os módulos habilitados."""
    events: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        for name, url in MODULE_URLS.items():
            if not is_module_enabled(name):
                continue
            try:
                resp = await client.post(f"{url}/collect")
                if resp.status_code == 200:
                    data = resp.json()
                    for event in data.get("history_events", []):
                        event["source_module"] = name
                        events.append(event)
            except httpx.HTTPError:
                continue
    events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return events[:limit]


@app.post("/sessions/start")
async def start_session(
    body: SessionStartRequest,
    user: User = Depends(_require_admin),
) -> dict[str, Any]:
    session_id = f"sess-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{user.username}"
    record = SessionRecord(
        session_id=session_id,
        user=user.username,
        target_host=body.target_id,
        protocol=body.protocol,
        started_at=datetime.now(UTC),
    )
    _active_sessions[session_id] = {"record": record, "commands": []}
    guac_url = f"/guacamole/#/client/{session_id}"
    return {"session_id": session_id, "status": "started", "guacamole_url": guac_url}


@app.post("/sessions/end")
async def end_session(
    body: SessionEndRequest,
    user: User = Depends(_require_admin),
) -> dict[str, str]:
    session = _active_sessions.pop(body.session_id, None)
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    record: SessionRecord = session["record"]
    ended_at = datetime.now(UTC)
    if isinstance(record.started_at, datetime):
        started = record.started_at
    else:
        started = datetime.fromisoformat(str(record.started_at))
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
async def audit_log(user: User = Depends(_require_admin), limit: int = 50) -> list[dict[str, Any]]:
    return read_sessions(limit=limit)


@app.get("/metrics")
async def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

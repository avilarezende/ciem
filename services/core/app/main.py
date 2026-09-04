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
    create_local_user,
    delete_local_user,
    is_module_enabled,
    load_auth_config,
    load_main_config,
    load_modules_config,
    update_ldap_config,
    update_local_user,
    update_module_config,
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


class ModuleUpdateRequest(BaseModel):
    enabled: bool | None = None
    options: dict[str, Any] | None = None


@app.get("/config/modules")
async def get_modules_config(user: User = Depends(require_user)) -> dict[str, Any]:
    modules_cfg = load_modules_config()
    return {
        name: {"enabled": entry.enabled, "description": entry.description, "options": entry.options}
        for name, entry in modules_cfg.modules.items()
    }


@app.put("/config/modules/{module_name}")
async def update_module(
    module_name: str,
    body: ModuleUpdateRequest,
    user: User = Depends(require_admin),
) -> dict[str, Any]:
    """Ativa/desativa módulo e/ou atualiza opções (URL, credenciais, etc.)."""
    if body.enabled is None and body.options is None:
        raise HTTPException(status_code=400, detail="Informe enabled e/ou options")
    try:
        entry = update_module_config(module_name, enabled=body.enabled, options=body.options)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {
        "module": module_name,
        "enabled": entry.enabled,
        "description": entry.description,
        "options": entry.options,
    }


class LdapUpdateRequest(BaseModel):
    enabled: bool | None = None
    host: str | None = None
    port: int | None = None
    use_ssl: bool | None = None
    server_url: str | None = None
    domain: str | None = None
    base_dn: str | None = None
    uid_attribute: str | None = None
    user_filter: str | None = None
    bind_dn: str | None = None
    bind_password: str | None = None
    ca_cert_path: str | None = None
    client_cert_path: str | None = None
    display_name_attribute: str | None = None
    group_role_mapping: dict[str, str] | None = None
    default_role: str | None = None
    verify_ssl: bool | None = None


class LocalUserCreateRequest(BaseModel):
    username: str
    password: str
    role: str = "observer"
    enabled: bool = True


class LocalUserUpdateRequest(BaseModel):
    password: str | None = None
    role: str | None = None
    enabled: bool | None = None


@app.get("/config/auth")
async def get_auth_config(user: User = Depends(require_admin)) -> dict[str, Any]:
    """Retorna LDAP + usuários locais (sem expor password_hash)."""
    cfg = load_auth_config()
    ldap = cfg.ldap.to_yaml_dict()
    # Não devolver senha de bind em claro na UI se quiser mascarar — admin precisa editar
    return {
        "local_users": [
            {
                "username": u.username,
                "role": u.role,
                "enabled": u.enabled,
                "is_default_admin": u.username == "admin" and u.role == "admin",
            }
            for u in cfg.local_users
        ],
        "ldap": ldap,
        "notes": {
            "local_priority": "Autenticação local é sempre tentada antes do LDAP.",
            "default_admin": "O usuário admin local existe independentemente do LDAP.",
        },
    }


@app.put("/config/auth/ldap")
async def put_ldap_config(
    body: LdapUpdateRequest,
    user: User = Depends(require_admin),
) -> dict[str, Any]:
    """Atualiza apontamentos LDAP em config/auth.yaml."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Nenhum campo LDAP informado")
    try:
        ldap = update_ldap_config(updates)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ldap": ldap.to_yaml_dict(), "status": "saved"}


@app.post("/config/auth/users")
async def post_local_user(
    body: LocalUserCreateRequest,
    user: User = Depends(require_admin),
) -> dict[str, Any]:
    try:
        entry = create_local_user(body.username.strip(), body.password, body.role, body.enabled)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"username": entry.username, "role": entry.role, "enabled": entry.enabled}


@app.put("/config/auth/users/{username}")
async def put_local_user(
    username: str,
    body: LocalUserUpdateRequest,
    user: User = Depends(require_admin),
) -> dict[str, Any]:
    if body.password is None and body.role is None and body.enabled is None:
        raise HTTPException(status_code=400, detail="Informe password, role e/ou enabled")
    try:
        entry = update_local_user(
            username,
            password=body.password,
            role=body.role,
            enabled=body.enabled,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"username": entry.username, "role": entry.role, "enabled": entry.enabled}


@app.delete("/config/auth/users/{username}")
async def remove_local_user(username: str, user: User = Depends(require_admin)) -> dict[str, str]:
    try:
        delete_local_user(username)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "deleted", "username": username}




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

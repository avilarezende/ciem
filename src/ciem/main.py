from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from pydantic import BaseModel, Field

from ciem import __version__
from ciem.config import settings

REQUEST_COUNT = Counter("ciem_requests_total", "Total de requisições HTTP", ["method", "endpoint"])

app = FastAPI(
    title="CIEM",
    description="Cloud Infrastructure & Environment Management API",
    version=__version__,
)


class EnvironmentSpec(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    install: str | None = None
    start: str | None = None
    repos: list[str] = Field(default_factory=list)


class EnvironmentValidation(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


@app.middleware("http")
async def count_requests(request, call_next):
    response = await call_next(request)
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    return response


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": __version__,
        "env": settings.env,
    }


@app.get("/info")
async def info() -> dict[str, Any]:
    return {
        "name": settings.app_name,
        "version": __version__,
        "cloud_provider": settings.cloud_provider,
        "repo_url": settings.repo_url,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.post("/environments/validate", response_model=EnvironmentValidation)
async def validate_environment(spec: EnvironmentSpec) -> EnvironmentValidation:
    errors: list[str] = []
    warnings: list[str] = []

    if not spec.install and not spec.start:
        errors.append("Pelo menos um comando 'install' ou 'start' deve ser definido.")

    if spec.install and "&&" in spec.install:
        warnings.append("Prefira um comando por linha em 'install' em vez de encadear com &&.")

    if not spec.repos:
        warnings.append("Nenhum repositório vinculado ao ambiente.")

    for repo in spec.repos:
        if not repo.startswith(("https://", "http://", "git@")):
            errors.append(f"URL de repositório inválida: {repo}")

    return EnvironmentValidation(valid=len(errors) == 0, errors=errors, warnings=warnings)


@app.get("/environments/{name}")
async def get_environment(name: str) -> dict[str, Any]:
    if name != settings.app_name:
        raise HTTPException(status_code=404, detail=f"Ambiente '{name}' não encontrado.")
    return {
        "name": settings.app_name,
        "provider": settings.cloud_provider,
        "repo_url": settings.repo_url,
        "status": "active",
    }


@app.get("/metrics")
async def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

"""Factory FastAPI para expor endpoints /health e /collect."""

from fastapi import FastAPI

from ciem_common.collector import CollectorModule
from ciem_common.models import CollectResponse


def create_collector_app(collector: CollectorModule, *, title: str | None = None) -> FastAPI:
    """Cria aplicação FastAPI padronizada para um módulo coletor."""
    app = FastAPI(
        title=title or f"CIEM Collector - {collector.name}",
        version="0.1.0",
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "module": collector.name}

    @app.post("/collect", response_model=CollectResponse)
    async def collect() -> CollectResponse:
        return await collector.collect()

    return app

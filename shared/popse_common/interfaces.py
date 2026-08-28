"""Contratos compartilhados entre módulos."""

from typing import Protocol


class SourceCollector(Protocol):
    name: str

    async def collect(self) -> list[dict]:
        """Retorna documentos [{id, text, metadata}] para ingestão RAG."""
        ...


class ChannelAdapter(Protocol):
    name: str

    async def start(self) -> None:
        """Inicia escuta do canal e encaminha mensagens ao engine."""
        ...

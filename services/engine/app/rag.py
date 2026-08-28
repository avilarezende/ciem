"""Armazenamento vetorial simples para RAG."""

from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings

_client: chromadb.PersistentClient | None = None


def get_chroma() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        Path(settings.chroma_path).mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=settings.chroma_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def get_collection(name: str = "operacional"):
    return get_chroma().get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})


def ingest_documents(collection: str, docs: list[dict]) -> int:
    """docs: [{id, text, metadata}]"""
    if not docs:
        return 0
    col = get_collection(collection)
    col.upsert(
        ids=[d["id"] for d in docs],
        documents=[d["text"] for d in docs],
        metadatas=[d.get("metadata", {}) for d in docs],
    )
    return len(docs)


def query_context(collection: str, question: str, top_k: int = 6) -> str:
    col = get_collection(collection)
    if col.count() == 0:
        return ""
    result = col.query(query_texts=[question], n_results=min(top_k, col.count()))
    docs = result.get("documents", [[]])[0]
    metas = result.get("metadatas", [[]])[0]
    chunks = []
    for doc, meta in zip(docs, metas):
        source = meta.get("source", "desconhecida") if meta else "desconhecida"
        chunks.append(f"[{source}]\n{doc}")
    return "\n\n---\n\n".join(chunks)

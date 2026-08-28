"""Testes dos provedores LLM (com mocks HTTP)."""

import httpx
import pytest
import respx

from app.config import settings
from app.llm.providers import GeminiProvider, GrokProvider, OllamaProvider, OpenAIProvider


@pytest.mark.asyncio
@respx.mock
async def test_ollama_provider(monkeypatch):
    monkeypatch.setattr(settings, "ollama_host", "http://localhost:11434")
    monkeypatch.setattr(settings, "ollama_model", "test-model")
    respx.post("http://localhost:11434/api/chat").mock(
        return_value=httpx.Response(200, json={"message": {"content": "Olá do Ollama"}})
    )
    reply = await OllamaProvider().generate("system", "user")
    assert "Ollama" in reply


@pytest.mark.asyncio
@respx.mock
async def test_grok_provider(monkeypatch):
    monkeypatch.setattr(settings, "grok_api_key", "test-key")
    monkeypatch.setattr(settings, "grok_base_url", "https://api.x.ai/v1")
    monkeypatch.setattr(settings, "grok_model", "grok-2-latest")
    respx.post("https://api.x.ai/v1/chat/completions").mock(
        return_value=httpx.Response(
            200, json={"choices": [{"message": {"content": "Resposta Grok"}}]}
        )
    )
    reply = await GrokProvider().generate("system", "user")
    assert reply == "Resposta Grok"


@pytest.mark.asyncio
@respx.mock
async def test_openai_provider(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "openai_model", "gpt-4o-mini")
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200, json={"choices": [{"message": {"content": "Resposta OpenAI"}}]}
        )
    )
    reply = await OpenAIProvider().generate("system", "user")
    assert reply == "Resposta OpenAI"


@pytest.mark.asyncio
@respx.mock
async def test_gemini_provider(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "gem-key")
    monkeypatch.setattr(settings, "gemini_model", "gemini-1.5-flash")
    respx.post(url__regex=r"https://generativelanguage\.googleapis\.com/.*generateContent.*").mock(
        return_value=httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": "Resposta Gemini"}]}}]}
        )
    )
    reply = await GeminiProvider().generate("system", "user")
    assert reply == "Resposta Gemini"

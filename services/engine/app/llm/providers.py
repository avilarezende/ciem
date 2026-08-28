"""Provedores de LLM: local (Ollama) e remotos (Gemini, OpenAI, Azure, Grok)."""

from typing import Protocol

import httpx

from app.config import settings


class LlmProvider(Protocol):
    async def generate(self, system: str, user_prompt: str) -> str: ...


class OllamaProvider:
    async def generate(self, system: str, user_prompt: str) -> str:
        url = f"{settings.ollama_host.rstrip('/')}/api/chat"
        payload = {
            "model": settings.ollama_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json().get("message", {}).get("content", "")


class GeminiProvider:
    async def generate(self, system: str, user_prompt: str) -> str:
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY não configurada")
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
        )
        payload = {"contents": [{"parts": [{"text": f"{system}\n\n{user_prompt}"}]}]}
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            parts = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
            return parts[0].get("text", "")


class OpenAIProvider:
    async def generate(self, system: str, user_prompt: str) -> str:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY não configurada")
        base = (settings.openai_base_url or "https://api.openai.com/v1").rstrip("/")
        payload = {
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"{base}/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]


class AzureOpenAIProvider:
    async def generate(self, system: str, user_prompt: str) -> str:
        if not all([settings.azure_openai_api_key, settings.azure_openai_endpoint, settings.azure_openai_deployment]):
            raise ValueError("Credenciais Azure OpenAI incompletas (AZURE_OPENAI_*)")
        endpoint = settings.azure_openai_endpoint.rstrip("/")
        url = (
            f"{endpoint}/openai/deployments/{settings.azure_openai_deployment}/chat/completions"
            f"?api-version={settings.azure_openai_api_version}"
        )
        payload = {
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                url,
                headers={"api-key": settings.azure_openai_api_key},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]


class GrokProvider:
    """xAI Grok — API compatível com OpenAI Chat Completions."""

    async def generate(self, system: str, user_prompt: str) -> str:
        if not settings.grok_api_key:
            raise ValueError("GROK_API_KEY não configurada")
        base = settings.grok_base_url.rstrip("/")
        payload = {
            "model": settings.grok_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"{base}/chat/completions",
                headers={"Authorization": f"Bearer {settings.grok_api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]


def get_provider() -> LlmProvider:
    providers: dict[str, LlmProvider] = {
        "ollama": OllamaProvider(),
        "gemini": GeminiProvider(),
        "openai": OpenAIProvider(),
        "azure": AzureOpenAIProvider(),
        "grok": GrokProvider(),
    }
    provider = providers.get(settings.llm_provider)
    if not provider:
        raise ValueError(f"Provedor LLM desconhecido: {settings.llm_provider}")
    return provider

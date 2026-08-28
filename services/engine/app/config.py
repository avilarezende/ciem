"""Configurações compartilhadas do Conversador PoP-SE."""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

LlmProvider = Literal["ollama", "gemini", "openai", "azure", "grok"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Banco e RAG ---
    database_url: str = "postgresql+asyncpg://popse:altere_em_producao@postgres:5432/conversador"
    chroma_path: str = "/data/chroma"
    config_path: str = "/app/config"
    popse_context_url: str = "https://www.pop-se.rnp.br"

    # --- Provedor de IA ---
    # Valores: ollama | gemini | openai | azure | grok
    llm_provider: LlmProvider = "ollama"

    # Ollama (local, gratuito)
    ollama_host: str = "http://ollama:11434"
    ollama_model: str = "llama3.2:3b"

    # Google Gemini (API key em https://aistudio.google.com/apikey)
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-1.5-flash"

    # OpenAI (API key em https://platform.openai.com/api-keys)
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str | None = None  # opcional: proxy compatível OpenAI

    # Azure OpenAI (portal Azure → recurso OpenAI → Keys and Endpoint)
    azure_openai_api_key: str | None = None
    azure_openai_endpoint: str | None = None  # ex.: https://SEU-RECURSO.openai.azure.com
    azure_openai_deployment: str | None = None  # nome do deployment no Azure
    azure_openai_api_version: str = "2024-08-01-preview"

    # xAI Grok (API key em https://console.x.ai)
    grok_api_key: str | None = None
    grok_model: str = "grok-2-latest"
    grok_base_url: str = "https://api.x.ai/v1"

    @property
    def config_dir(self) -> Path:
        return Path(self.config_path)


settings = Settings()

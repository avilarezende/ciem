"""Configuração do serviço core CIEM."""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class CoreSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CIEM_", env_file=".env", extra="ignore")

    app_name: str = "ciem"
    version: str = "0.2.0"
    host: str = "0.0.0.0"
    port: int = 8000
    config_path: str = "./config"
    secret_key: str = "change-me-in-production"
    # Em produção defina origens explícitas (ex.: https://ciem.exemplo.local).
    # "*" com credentials é inseguro — o app desativa credentials automaticamente.
    cors_origins: str = "*"
    # development | staging | production
    env: str = "development"
    # Lista separada por vírgula; vazio = TrustedHost desativado (útil em testes/dev).
    trusted_hosts: str = ""
    # Expõe /docs e /redoc apenas fora de production (ou force com CIEM_DOCS_ENABLED=1).
    docs_enabled: bool | None = None


settings = CoreSettings()
settings.config_path = os.environ.get("CONFIG_PATH", settings.config_path)

# Alias legado: CIEM_ENV também alimenta settings.env via env_prefix CIEM_ + env.
if os.environ.get("CIEM_ENV"):
    settings.env = os.environ["CIEM_ENV"]

_docs_flag = os.environ.get("CIEM_DOCS_ENABLED")
if _docs_flag is not None:
    settings.docs_enabled = _docs_flag.strip().lower() in {"1", "true", "yes", "on"}
elif settings.docs_enabled is None:
    settings.docs_enabled = settings.env.strip().lower() != "production"

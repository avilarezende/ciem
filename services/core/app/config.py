"""Configuração do serviço core CIEM."""

import os
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CoreSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CIEM_", env_file=".env", extra="ignore", hide_input_in_errors=True
    )

    app_name: str = "ciem"
    version: str = "0.2.0"
    host: str = "127.0.0.1"
    port: int = 8000
    config_path: str = "./config"
    secret_key: str = "change-me-in-production"
    # Em produção defina origens explícitas (ex.: https://ciem.exemplo.local).
    # "*" com credentials é inseguro — o app desativa credentials automaticamente.
    cors_origins: str = "*"
    # development | staging | production
    env: Literal["development", "staging", "production"] = "development"
    rate_limit_enabled: bool = True
    # Lista separada por vírgula; vazio = TrustedHost desativado (útil em testes/dev).
    trusted_hosts: str = ""
    # Expõe /docs e /redoc apenas fora de production (ou force com CIEM_DOCS_ENABLED=1).
    docs_enabled: bool | None = None

    @model_validator(mode="after")
    def validate_production(self):
        if self.env in {"staging", "production"}:
            if len(self.secret_key) < 32 or any(
                s in self.secret_key.lower() for s in ("change-me", "test-", "example")
            ):
                raise ValueError("CIEM_SECRET_KEY forte é obrigatória fora de development")
            if not self.trusted_hosts or "*" in self.trusted_hosts:
                raise ValueError("CIEM_TRUSTED_HOSTS explícitos são obrigatórios")
            if "*" in self.cors_origins or any(
                origin and not origin.strip().startswith("https://")
                for origin in self.cors_origins.split(",")
            ):
                raise ValueError("CIEM_CORS_ORIGINS requer origens HTTPS explícitas")
            if self.docs_enabled or not self.rate_limit_enabled:
                raise ValueError("Produção requer rate limiting e documentação de API desativada")
        return self


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

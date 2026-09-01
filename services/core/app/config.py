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
    cors_origins: str = "*"


settings = CoreSettings()
settings.config_path = os.environ.get("CONFIG_PATH", settings.config_path)

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CIEM_", env_file=".env", extra="ignore")

    app_name: str = "ciem"
    env: str = "development"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000
    cloud_provider: str = "cursor"
    repo_url: str = "https://github.com/rodrigo-rezende/ciem"


settings = Settings()

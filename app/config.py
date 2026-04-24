from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    max_bot_token: str
    max_webhook_secret: str | None = None

    public_base_url: str | None = None
    webhook_path: str = "/webhook/max"

    database_url: str = "sqlite+aiosqlite:///./var/app.db"

    admin_api_key: str | None = None

    rate_limit_per_minute: int = 60
    log_level: str = "INFO"


settings = Settings()

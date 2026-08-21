"""Typed application settings.

Values come from environment variables with the ``BRIEFTAUBE_`` prefix
(and a local ``.env`` file if present). See ``.env.example``.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from brieftaube.i18n import DEFAULT_LOCALE


class Settings(BaseSettings):
    """Runtime configuration, validated and typed by pydantic-settings."""

    model_config = SettingsConfigDict(
        env_prefix="BRIEFTAUBE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Dev-only default; production MUST set BRIEFTAUBE_SECRET_KEY.
    secret_key: str = "dev-only-secret-change-me"  # noqa: S105 - safe dev default

    database_path: Path = Path("data/brieftaube.db")
    default_locale: str = DEFAULT_LOCALE

    signal_cli_url: str = "http://signal-cli:8080"

    # Empty host disables the MQTT consumer (see docs/concepts/architecture.md section 4).
    mqtt_host: str | None = None
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return Settings()

"""Runtime configuration. Values overridable via env vars."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Globtel Weather Scoring"
    api_prefix: str = "/api/v1"

    open_meteo_base_url: str = "https://archive-api.open-meteo.com/v1/archive"
    open_meteo_timeout_seconds: float = 15.0

    weight_temperature: float = Field(default=0.35)
    weight_wind: float = Field(default=0.20)
    weight_humidity: float = Field(default=0.20)
    weight_cloud: float = Field(default=0.25)


@lru_cache
def get_settings() -> Settings:
    return Settings()

from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    supabase_url: str
    supabase_service_key: str
    frontend_url: str = "http://localhost:3000"
    api_prefix: str = "/api/v1"

    @property
    def frontend_urls(self) -> List[str]:
        return [url.strip() for url in self.frontend_url.split(",")]


def get_settings() -> Settings:
    return Settings()

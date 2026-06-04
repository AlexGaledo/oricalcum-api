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
    secrets_encryption_key: str | None = None

    # AI assistant
    google_api_key: str | None = None
    agent_model: str = "gemini-2.5-flash"
    # Loopback URL the in-process agent uses to reach the mounted FastMCP server.
    mcp_internal_url: str = "http://127.0.0.1:8000/mcp/"

    @property
    def frontend_urls(self) -> List[str]:
        return [url.strip() for url in self.frontend_url.split(",")]


def get_settings() -> Settings:
    return Settings()

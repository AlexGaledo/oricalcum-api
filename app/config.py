from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    supabase_url: str
    supabase_service_key: str
    frontend_url: str = "http://localhost:3000"
    api_prefix: str = "/api/v1"


def get_settings() -> Settings:
    return Settings()

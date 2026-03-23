from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LinkedIn Personal Branding Assistant"
    app_env: str = "development"
    log_level: str = "INFO"

    # SQLite default lets the app boot without external DB setup.
    database_url: str = "sqlite:///./linkedin_branding.db"

    groq_api_key: str = ""
    groq_model: str = "llama-3.1-70b-versatile"
    groq_timeout_seconds: int = 60

    duckduckgo_max_results: int = 10
    max_influencers: int = 15

    outlook_smtp_host: str = "smtp.office365.com"
    outlook_smtp_port: int = 587
    outlook_smtp_username: str = ""
    outlook_smtp_password: str = ""
    outlook_from_email: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

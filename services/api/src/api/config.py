import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env_file() -> str | None:
    """Find .env file, preferring .env.local for local development."""
    for env_file in [".env.local", ".env"]:
        for base in [".", os.environ.get("REPO_ROOT", "")]:
            if base:
                path = Path(base) / env_file
                if path.exists():
                    return str(path)
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_find_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite:///./local.db"

    # OpenAI
    openai_api_key: str = ""
    openai_model_text: str = "gpt-4o-mini"
    openai_model_stt: str = "gpt-4o-mini-transcribe"
    openai_model_tts: str = "gpt-4o-mini-tts"
    openai_model_realtime: str = "gpt-4o-mini-realtime-preview"

    # Domain configuration
    active_domains: str = "medical"

    # CORS
    cors_origin: str = ""


settings = Settings()

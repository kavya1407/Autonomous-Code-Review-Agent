from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal
from pathlib import Path


class Settings(BaseSettings):
    """Application configuration loaded from environment or .env file."""

    # GitHub Integration
    github_token: str = ""

    # LLM Settings
    openai_api_key: str = ""
    openai_model_name: str = "gpt-4o-mini"
    llm_provider: Literal["openai", "mock"] = "mock"

    # Server Configuration
    app_env: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # State Persistence
    persistence_type: Literal["memory", "sqlite"] = "memory"
    checkpoint_db_path: str = "./data/checkpoints.sqlite"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

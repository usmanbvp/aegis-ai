from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="aegis")
    app_env: Literal["development", "staging", "production"] = Field(default="development")
    groq_api_key: str = Field(default="")
    groq_base_url: str = Field(default="https://api.groq.com/openai/v1")
    groq_model: str = Field(default="openai/gpt-oss-20b")
    gemini_api_key: str = Field(default="")
    gemini_base_url: str = Field(default="https://generativelanguage.googleapis.com/v1beta/openai")
    gemini_model: str = Field(default="gemini-3.8-flash")
    llm_primary_provider: Literal["groq", "gemini"] = Field(default="groq")
    llm_max_retries: int = Field(default=1, ge=0, le=5)
    llm_timeout_seconds: float = Field(default=45, gt=0, le=300)
    llm_retry_backoff_seconds: float = Field(default=0.5, ge=0, le=30)
    cohere_api_key: str = Field(default="")
    database_url: str = Field(default="sqlite:///./aegis.db")
    redis_url: str = Field(default="redis://localhost:6379/0")
    qdrant_url: str = Field(default="http://localhost:6333")
    langchain_tracing_v2: bool = Field(default=False)
    langchain_api_key: str = Field(default="")
    langchain_project: str = Field(default="aegis")
    vite_api_base_url: str = Field(default="http://localhost:8000")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

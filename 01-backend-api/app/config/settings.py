"""
Application settings — loaded from ``.env``.

All configuration lives here.  Other modules import ``get_settings()``
through dependency injection.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for the EchoQuery backend."""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    # ---- Application --------------------------------------------------
    app_name: str = "EchoQuery"
    app_version: str = "0.1.0"
    debug: bool = False

    # ---- CORS ---------------------------------------------------------
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173", "*"],
        description="Allowed CORS origins.",
    )

    # ---- STT Provider -------------------------------------------------
    stt_provider: Optional[str] = Field(
        default=None,
        description="Force a specific STT provider: sarvam | voxtral | mock.  "
        "If omitted, auto-selects based on available API keys.",
    )
    sarvam_api_key: str = Field(default="", description="Sarvam API key.")
    voxtral_api_key: str = Field(default="", description="Voxtral/Mistral API key.")

    # ---- RAG Engine ---------------------------------------------------
    rag_endpoint: str = Field(
        default="",
        description="URL of the RAG engine API.  Empty ⇒ use mock.",
    )
    rag_timeout_seconds: float = Field(default=30.0)

    # ---- Audio --------------------------------------------------------
    max_audio_size_mb: float = Field(
        default=25.0,
        description="Maximum audio upload size in megabytes.",
    )
    max_audio_duration_seconds: float = Field(
        default=30.0,
        description="Maximum audio duration in seconds (Sarvam REST limit).",
    )

    # ---- Server -------------------------------------------------------
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()

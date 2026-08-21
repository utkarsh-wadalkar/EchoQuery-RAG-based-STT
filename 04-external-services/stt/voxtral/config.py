"""Voxtral Mini configuration."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class VoxtralConfig(BaseSettings):
    """
    Configuration for the Voxtral Mini STT provider (testing).

    Values are loaded from environment variables prefixed with ``VOXTRAL_``.
    """

    model_config = {"env_prefix": "VOXTRAL_"}

    api_key: str = Field(
        default="",
        description="Mistral / Voxtral API key.",
    )
    endpoint: str = Field(
        default="https://api.mistral.ai/v1/audio/transcriptions",
        description="Voxtral transcription endpoint.",
    )
    model: str = Field(
        default="mistral-voxtral-mini",
        description="Model identifier.",
    )
    timeout_seconds: float = Field(
        default=30.0,
        description="HTTP request timeout in seconds.",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts on transient errors.",
    )
    retry_base_delay: float = Field(
        default=1.0,
        description="Base delay in seconds for exponential backoff.",
    )

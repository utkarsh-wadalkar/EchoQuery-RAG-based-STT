"""Sarvam Saaras v3 configuration."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class SarvamConfig(BaseSettings):
    """
    Configuration for the Sarvam Saaras v3 STT provider.

    Values are loaded from environment variables prefixed with ``SARVAM_``.
    """

    model_config = {"env_prefix": "SARVAM_"}

    api_key: str = Field(
        default="",
        description="Sarvam API subscription key.",
    )
    endpoint: str = Field(
        default="https://api.sarvam.ai/speech-to-text",
        description="Sarvam STT REST endpoint.",
    )
    model: str = Field(
        default="saaras:v3",
        description="Sarvam model identifier.",
    )
    mode: str = Field(
        default="transcribe",
        description="Transcription mode (transcribe | translate | verbatim | translit | codemix).",
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

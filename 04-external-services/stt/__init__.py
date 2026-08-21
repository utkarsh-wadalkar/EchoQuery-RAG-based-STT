"""
EchoQuery STT provider package.

Usage::

    from stt import create_stt_provider, STTProvider, Transcript

    provider = create_stt_provider(sarvam_api_key="...")
    transcript = await provider.transcribe(audio_bytes, request_id="req-1")
"""

from .base import (
    STTClientError,
    STTError,
    STTProvider,
    STTProviderError,
    STTProviderName,
    STTTimeoutError,
    SupportedLanguage,
    Transcript,
)
from .factory import create_stt_provider

__all__ = [
    "STTProvider",
    "STTProviderName",
    "SupportedLanguage",
    "Transcript",
    "STTError",
    "STTTimeoutError",
    "STTProviderError",
    "STTClientError",
    "create_stt_provider",
]

"""
Abstract base for all STT providers.

Every concrete provider (Sarvam, Voxtral, Mock) must subclass ``STTProvider``
and return a ``Transcript`` that conforms to ``00-contracts/transcript.schema.json``.
"""

from __future__ import annotations

import abc
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared enums
# ---------------------------------------------------------------------------

class SupportedLanguage(str, Enum):
    """Languages supported by EchoQuery (matches contract enum)."""

    EN_IN = "en-IN"
    HI_IN = "hi-IN"
    BN_IN = "bn-IN"
    TA_IN = "ta-IN"
    TE_IN = "te-IN"
    KN_IN = "kn-IN"
    ML_IN = "ml-IN"
    MR_IN = "mr-IN"
    GU_IN = "gu-IN"
    PA_IN = "pa-IN"
    OD_IN = "od-IN"


class STTProviderName(str, Enum):
    """Identifiers for STT providers (matches contract enum)."""

    SARVAM = "sarvam"
    VOXTRAL = "voxtral"


# ---------------------------------------------------------------------------
# Contract-compliant transcript model
# ---------------------------------------------------------------------------

class Transcript(BaseModel):
    """
    Normalised speech-to-text output.

    Mirrors ``00-contracts/transcript.schema.json`` exactly.
    """

    request_id: str
    text: str
    language: SupportedLanguage
    is_final: bool
    provider: STTProviderName
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    timestamp_ms: Optional[int] = Field(default=None, ge=0)
    duration_ms: Optional[int] = Field(default=None, ge=0)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class STTError(Exception):
    """Base exception for STT failures."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class STTTimeoutError(STTError):
    """STT provider timed out."""

    def __init__(self, message: str = "STT provider timed out") -> None:
        super().__init__(message, retryable=True)


class STTProviderError(STTError):
    """STT provider returned a server-side error (5xx)."""

    def __init__(self, message: str, *, status_code: int = 500) -> None:
        super().__init__(message, retryable=True)
        self.status_code = status_code


class STTClientError(STTError):
    """STT provider rejected the request (4xx)."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message, retryable=False)
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Abstract provider
# ---------------------------------------------------------------------------

class STTProvider(abc.ABC):
    """
    Abstract STT provider.

    Implementations receive raw audio bytes and return a contract-compliant
    ``Transcript``.  Language may be ``None`` to request auto-detection.
    """

    @abc.abstractmethod
    async def transcribe(
        self,
        audio: bytes,
        *,
        request_id: str,
        language: Optional[str] = None,
    ) -> Transcript:
        """Transcribe *audio* and return a ``Transcript``."""

    @abc.abstractmethod
    async def close(self) -> None:
        """Release any resources held by this provider."""

    @property
    @abc.abstractmethod
    def provider_name(self) -> STTProviderName:
        """Return the provider identifier."""

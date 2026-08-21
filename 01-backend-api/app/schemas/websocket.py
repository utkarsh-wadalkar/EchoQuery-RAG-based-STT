"""
WebSocket event schemas.

Derived from:
- ``00-contracts/websocket-client-events.schema.json``
- ``00-contracts/websocket-server-events.schema.json``
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from .query import SupportedLanguage


# =========================================================================
# Client → Server events
# =========================================================================

class ClientEventType(str, Enum):
    SESSION_START = "session_start"
    AUDIO_END = "audio_end"
    CANCEL = "cancel"


class SessionStartEvent(BaseModel):
    """Sent by the client to begin a new voice query session."""

    type: ClientEventType = ClientEventType.SESSION_START
    request_id: str = Field(min_length=1)
    language: Optional[SupportedLanguage] = None
    session_id: Optional[str] = None


class AudioEndEvent(BaseModel):
    """Sent by the client to signal end of audio data."""

    type: ClientEventType = ClientEventType.AUDIO_END
    request_id: str = Field(min_length=1)


class CancelEvent(BaseModel):
    """Sent by the client to cancel an active request."""

    type: ClientEventType = ClientEventType.CANCEL
    request_id: str = Field(min_length=1)


# =========================================================================
# Server → Client events
# =========================================================================

class ServerEventType(str, Enum):
    TRANSCRIPT = "transcript"
    PROCESSING = "processing"
    ANSWER = "answer"
    ERROR = "error"
    COMPLETE = "complete"


class ProcessingStage(str, Enum):
    TRANSCRIPTION = "transcription"
    PREPROCESSING = "preprocessing"
    EMBEDDING = "embedding"
    RETRIEVAL = "retrieval"
    RERANKING = "reranking"
    GENERATION = "generation"
    GROUNDING = "grounding"


class ErrorCode(str, Enum):
    INVALID_REQUEST = "INVALID_REQUEST"
    UNSUPPORTED_LANGUAGE = "UNSUPPORTED_LANGUAGE"
    STT_ERROR = "STT_ERROR"
    STT_TIMEOUT = "STT_TIMEOUT"
    RAG_ERROR = "RAG_ERROR"
    RAG_TIMEOUT = "RAG_TIMEOUT"
    NO_RELEVANT_CONTEXT = "NO_RELEVANT_CONTEXT"
    GROUNDING_FAILED = "GROUNDING_FAILED"
    CANCELLED = "CANCELLED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class CompletionStatus(str, Enum):
    SUCCESS = "success"
    CANCELLED = "cancelled"
    FAILED = "failed"


def _now() -> str:
    """ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Server event payloads
# ---------------------------------------------------------------------------

class TranscriptData(BaseModel):
    text: str
    language: SupportedLanguage
    is_final: bool


class ProcessingData(BaseModel):
    stage: ProcessingStage


class ErrorData(BaseModel):
    code: ErrorCode
    message: str = Field(min_length=1)
    retryable: Optional[bool] = None


class CompleteData(BaseModel):
    status: CompletionStatus


# ---------------------------------------------------------------------------
# Server event wrappers
# ---------------------------------------------------------------------------

class _ServerEventBase(BaseModel):
    """Base fields shared by all server events."""

    type: ServerEventType
    request_id: str
    timestamp: str = Field(default_factory=_now)


class TranscriptEvent(_ServerEventBase):
    type: ServerEventType = ServerEventType.TRANSCRIPT
    data: TranscriptData


class ProcessingEvent(_ServerEventBase):
    type: ServerEventType = ServerEventType.PROCESSING
    data: ProcessingData


class AnswerEvent(_ServerEventBase):
    type: ServerEventType = ServerEventType.ANSWER
    data: dict[str, Any]  # Full AnswerResponse dict


class ErrorEvent(_ServerEventBase):
    type: ServerEventType = ServerEventType.ERROR
    data: ErrorData


class CompleteEvent(_ServerEventBase):
    type: ServerEventType = ServerEventType.COMPLETE
    data: CompleteData


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_transcript_event(
    request_id: str,
    text: str,
    language: SupportedLanguage,
    is_final: bool,
) -> dict[str, Any]:
    return TranscriptEvent(
        request_id=request_id,
        data=TranscriptData(text=text, language=language, is_final=is_final),
    ).model_dump(mode="json")


def make_processing_event(
    request_id: str,
    stage: ProcessingStage,
) -> dict[str, Any]:
    return ProcessingEvent(
        request_id=request_id,
        data=ProcessingData(stage=stage),
    ).model_dump(mode="json")


def make_answer_event(
    request_id: str,
    answer_data: dict[str, Any],
) -> dict[str, Any]:
    return AnswerEvent(
        request_id=request_id,
        data=answer_data,
    ).model_dump(mode="json")


def make_error_event(
    request_id: str,
    code: ErrorCode,
    message: str,
    *,
    retryable: bool | None = None,
) -> dict[str, Any]:
    return ErrorEvent(
        request_id=request_id,
        data=ErrorData(code=code, message=message, retryable=retryable),
    ).model_dump(mode="json")


def make_complete_event(
    request_id: str,
    status: CompletionStatus,
) -> dict[str, Any]:
    return CompleteEvent(
        request_id=request_id,
        data=CompleteData(status=status),
    ).model_dump(mode="json")

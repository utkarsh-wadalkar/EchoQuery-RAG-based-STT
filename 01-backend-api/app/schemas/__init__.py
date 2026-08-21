"""Backend schemas package."""

from .query import QueryRequest, SupportedLanguage, TextQueryInput
from .response import AnswerResponse, HealthResponse, Latency, ReadinessResponse, Source
from .websocket import (
    AudioEndEvent,
    CancelEvent,
    ClientEventType,
    CompletionStatus,
    ErrorCode,
    ProcessingStage,
    SessionStartEvent,
    make_answer_event,
    make_complete_event,
    make_error_event,
    make_processing_event,
    make_transcript_event,
)

__all__ = [
    "AnswerResponse",
    "AudioEndEvent",
    "CancelEvent",
    "ClientEventType",
    "CompletionStatus",
    "ErrorCode",
    "HealthResponse",
    "Latency",
    "ProcessingStage",
    "QueryRequest",
    "ReadinessResponse",
    "SessionStartEvent",
    "Source",
    "SupportedLanguage",
    "TextQueryInput",
    "make_answer_event",
    "make_complete_event",
    "make_error_event",
    "make_processing_event",
    "make_transcript_event",
]

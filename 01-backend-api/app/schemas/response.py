"""
Response schemas — derived from ``00-contracts/answer.schema.json``.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from .query import SupportedLanguage


# ---------------------------------------------------------------------------
# Answer (from RAG engine)
# ---------------------------------------------------------------------------

class Source(BaseModel):
    """A retrieved source chunk used by the RAG engine."""

    id: str
    text: str
    score: float
    metadata: Optional[dict[str, Any]] = None


class Latency(BaseModel):
    """Per-stage latency measurements (milliseconds)."""

    total_ms: float = Field(ge=0)
    embedding_ms: Optional[float] = Field(default=None, ge=0)
    retrieval_ms: Optional[float] = Field(default=None, ge=0)
    reranking_ms: Optional[float] = Field(default=None, ge=0)
    generation_ms: Optional[float] = Field(default=None, ge=0)


class AnswerResponse(BaseModel):
    """
    Grounded answer returned by the RAG pipeline.

    Mirrors ``00-contracts/answer.schema.json``.
    """

    request_id: str
    answer: str = Field(min_length=1)
    language: SupportedLanguage
    grounded: bool
    sources: list[Source]
    latency: Latency


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Response for the ``GET /health`` endpoint."""

    status: str = "ok"
    uptime_seconds: float
    stt_provider: str
    rag_mode: str


class ReadinessResponse(BaseModel):
    """Response for the ``GET /health/ready`` endpoint."""

    ready: bool
    stt_ready: bool
    rag_ready: bool
    details: Optional[str] = None

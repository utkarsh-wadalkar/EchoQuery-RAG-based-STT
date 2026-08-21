"""
Query schemas — derived from ``00-contracts/query.schema.json``.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SupportedLanguage(str, Enum):
    """Languages supported by EchoQuery (mirrors contract enum)."""

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


class QueryRequest(BaseModel):
    """
    Normalised query submitted to the RAG pipeline.

    Mirrors ``00-contracts/query.schema.json``.
    """

    request_id: str
    query: str = Field(min_length=1)
    language: SupportedLanguage
    top_k: int = Field(default=5, ge=1, le=20)
    session_id: Optional[str] = None


class TextQueryInput(BaseModel):
    """
    REST input for the ``POST /api/v1/query/text`` endpoint.

    ``request_id`` is auto-generated if omitted.
    """

    query: str = Field(min_length=1, description="User question text.")
    language: SupportedLanguage = Field(
        default=SupportedLanguage.EN_IN,
        description="Language of the query.",
    )
    top_k: int = Field(default=5, ge=1, le=20)
    session_id: Optional[str] = None

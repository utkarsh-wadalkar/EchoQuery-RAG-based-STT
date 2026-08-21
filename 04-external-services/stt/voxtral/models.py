"""
Raw Voxtral API response models.

Provider-specific — MUST NOT leak past the adapter boundary.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class VoxtralTranscriptResponse(BaseModel):
    """Subset of the Voxtral transcription response that we use."""

    text: str
    language: Optional[str] = None

"""
Raw Sarvam API response models.

These are provider-specific and MUST NOT leak past the adapter boundary.
The adapter maps them to the contract ``Transcript`` model.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class SarvamTranscriptResponse(BaseModel):
    """
    Subset of the Sarvam ``/speech-to-text`` JSON response that we use.

    The Sarvam API returns more fields; we only parse what we need.
    """

    transcript: str
    language_code: Optional[str] = None
    confidence: Optional[float] = None

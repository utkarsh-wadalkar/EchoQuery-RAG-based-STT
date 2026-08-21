"""
Mock STT provider for local development.

Returns realistic fake transcripts with configurable latency so the full
pipeline can be tested without any external API credentials.
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Optional

from ..base import (
    STTProvider,
    STTProviderName,
    SupportedLanguage,
    Transcript,
)

logger = logging.getLogger(__name__)

# Sample responses per language for realistic mock output
_MOCK_RESPONSES: dict[SupportedLanguage, list[str]] = {
    SupportedLanguage.EN_IN: [
        "What are the admission requirements for the engineering program?",
        "Tell me about the scholarship options available.",
        "How do I apply for the computer science department?",
        "What is the fee structure for this semester?",
        "Can you explain the placement statistics?",
    ],
    SupportedLanguage.HI_IN: [
        "इंजीनियरिंग प्रोग्राम के लिए प्रवेश आवश्यकताएं क्या हैं?",
        "उपलब्ध छात्रवृत्ति विकल्पों के बारे में बताइए।",
        "कंप्यूटर साइंस विभाग में आवेदन कैसे करें?",
    ],
    SupportedLanguage.TA_IN: [
        "பொறியியல் திட்டத்திற்கான சேர்க்கை தேவைகள் என்ன?",
    ],
    SupportedLanguage.TE_IN: [
        "ఇంజనీరింగ్ ప్రోగ్రామ్‌కు ప్రవేశ అవసరాలు ఏమిటి?",
    ],
}

# Fallback for languages not in the map
_DEFAULT_MOCK = "This is a mock transcription for testing purposes."


class MockSTT(STTProvider):
    """
    Mock STT provider for local development.

    Simulates transcription with a configurable delay and returns
    realistic sample text.
    """

    def __init__(
        self,
        *,
        latency_min_ms: int = 100,
        latency_max_ms: int = 500,
    ) -> None:
        self._latency_min = latency_min_ms
        self._latency_max = latency_max_ms

    @property
    def provider_name(self) -> STTProviderName:
        # Report as sarvam since the contract enum only allows sarvam/voxtral
        return STTProviderName.SARVAM

    async def close(self) -> None:
        pass  # nothing to clean up

    async def transcribe(
        self,
        audio: bytes,
        *,
        request_id: str,
        language: Optional[str] = None,
    ) -> Transcript:
        # Simulate realistic STT latency
        delay_ms = random.randint(self._latency_min, self._latency_max)
        await asyncio.sleep(delay_ms / 1000)

        # Resolve language
        resolved_lang = SupportedLanguage.EN_IN
        if language:
            try:
                resolved_lang = SupportedLanguage(language)
            except ValueError:
                resolved_lang = SupportedLanguage.EN_IN

        # Pick a sample response
        responses = _MOCK_RESPONSES.get(resolved_lang, [_DEFAULT_MOCK])
        text = random.choice(responses)

        logger.info(
            "[MockSTT] request=%s lang=%s delay=%dms text=%s",
            request_id, resolved_lang.value, delay_ms, text[:60],
        )

        return Transcript(
            request_id=request_id,
            text=text,
            language=resolved_lang,
            is_final=True,
            provider=self.provider_name,
            confidence=round(random.uniform(0.85, 0.99), 3),
            duration_ms=len(audio) // 32 if audio else None,  # rough estimate
        )

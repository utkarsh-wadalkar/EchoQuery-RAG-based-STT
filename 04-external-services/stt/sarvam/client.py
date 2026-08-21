"""
Sarvam Saaras v3 STT adapter.

Calls the Sarvam REST API and maps the response to the contract ``Transcript``.
"""

from __future__ import annotations

import io
import logging
from typing import Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..base import (
    STTClientError,
    STTProvider,
    STTProviderError,
    STTProviderName,
    STTTimeoutError,
    SupportedLanguage,
    Transcript,
)
from .config import SarvamConfig
from .models import SarvamTranscriptResponse

logger = logging.getLogger(__name__)

# Map Sarvam language codes to our contract enum values
_SARVAM_LANG_MAP: dict[str, SupportedLanguage] = {
    "en-IN": SupportedLanguage.EN_IN,
    "hi-IN": SupportedLanguage.HI_IN,
    "bn-IN": SupportedLanguage.BN_IN,
    "ta-IN": SupportedLanguage.TA_IN,
    "te-IN": SupportedLanguage.TE_IN,
    "kn-IN": SupportedLanguage.KN_IN,
    "ml-IN": SupportedLanguage.ML_IN,
    "mr-IN": SupportedLanguage.MR_IN,
    "gu-IN": SupportedLanguage.GU_IN,
    "pa-IN": SupportedLanguage.PA_IN,
    "od-IN": SupportedLanguage.OD_IN,
    # Common Sarvam alternative codes
    "en": SupportedLanguage.EN_IN,
    "hi": SupportedLanguage.HI_IN,
    "bn": SupportedLanguage.BN_IN,
    "ta": SupportedLanguage.TA_IN,
    "te": SupportedLanguage.TE_IN,
    "kn": SupportedLanguage.KN_IN,
    "ml": SupportedLanguage.ML_IN,
    "mr": SupportedLanguage.MR_IN,
    "gu": SupportedLanguage.GU_IN,
    "pa": SupportedLanguage.PA_IN,
    "od": SupportedLanguage.OD_IN,
    "or": SupportedLanguage.OD_IN,
}


class SarvamSTT(STTProvider):
    """
    Sarvam Saaras v3 speech-to-text adapter.

    Uses ``httpx.AsyncClient`` for async HTTP calls and ``tenacity`` for
    retry with exponential backoff on transient errors.
    """

    def __init__(self, config: SarvamConfig | None = None) -> None:
        self._config = config or SarvamConfig()
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._config.timeout_seconds),
        )

    @property
    def provider_name(self) -> STTProviderName:
        return STTProviderName.SARVAM

    async def close(self) -> None:
        await self._client.aclose()

    async def transcribe(
        self,
        audio: bytes,
        *,
        request_id: str,
        language: Optional[str] = None,
    ) -> Transcript:
        """
        Send audio to Sarvam and return a contract ``Transcript``.

        Retries transient errors up to ``max_retries`` times with exponential
        backoff.
        """
        return await self._transcribe_with_retry(
            audio, request_id=request_id, language=language,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _transcribe_with_retry(
        self,
        audio: bytes,
        *,
        request_id: str,
        language: Optional[str],
    ) -> Transcript:
        """Wrapper that applies tenacity retry logic."""

        @retry(
            retry=retry_if_exception_type((STTProviderError, STTTimeoutError)),
            stop=stop_after_attempt(self._config.max_retries),
            wait=wait_exponential(
                multiplier=self._config.retry_base_delay, min=1, max=16,
            ),
            reraise=True,
        )
        async def _call() -> Transcript:
            return await self._do_transcribe(
                audio, request_id=request_id, language=language,
            )

        return await _call()

    async def _do_transcribe(
        self,
        audio: bytes,
        *,
        request_id: str,
        language: Optional[str],
    ) -> Transcript:
        """Execute a single transcription request."""
        files = {"file": ("audio.wav", io.BytesIO(audio), "audio/wav")}
        data: dict[str, str] = {
            "model": self._config.model,
            "mode": self._config.mode,
        }
        if language:
            data["language_code"] = language

        headers = {"api-subscription-key": self._config.api_key}

        try:
            response = await self._client.post(
                self._config.endpoint,
                headers=headers,
                files=files,
                data=data,
            )
        except httpx.TimeoutException as exc:
            logger.warning(
                "Sarvam STT timeout for request %s: %s", request_id, exc,
            )
            raise STTTimeoutError() from exc
        except httpx.HTTPError as exc:
            logger.error(
                "Sarvam STT network error for request %s: %s",
                request_id, exc,
            )
            raise STTProviderError(f"Network error: {exc}") from exc

        if response.status_code >= 500:
            logger.warning(
                "Sarvam STT server error %d for request %s",
                response.status_code, request_id,
            )
            raise STTProviderError(
                f"Server error {response.status_code}",
                status_code=response.status_code,
            )
        if response.status_code >= 400:
            detail = response.text[:300]
            logger.error(
                "Sarvam STT client error %d for request %s: %s",
                response.status_code, request_id, detail,
            )
            raise STTClientError(
                f"Client error {response.status_code}: {detail}",
                status_code=response.status_code,
            )

        raw = SarvamTranscriptResponse.model_validate(response.json())

        # Resolve language
        detected = self._resolve_language(raw.language_code, language)

        return Transcript(
            request_id=request_id,
            text=raw.transcript,
            language=detected,
            is_final=True,
            provider=STTProviderName.SARVAM,
            confidence=raw.confidence,
        )

    @staticmethod
    def _resolve_language(
        detected: str | None,
        requested: str | None,
    ) -> SupportedLanguage:
        """
        Map a Sarvam language code to the contract enum.

        Prefers the detected language from the API; falls back to the
        requested language.  Defaults to ``en-IN`` if neither is available.
        """
        for code in (detected, requested):
            if code and code in _SARVAM_LANG_MAP:
                return _SARVAM_LANG_MAP[code]
        return SupportedLanguage.EN_IN

"""
Voxtral Mini STT adapter (testing provider).

Calls the Mistral Voxtral transcription API and maps the response to the
contract ``Transcript``.
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
from .config import VoxtralConfig
from .models import VoxtralTranscriptResponse

logger = logging.getLogger(__name__)

# Best-effort mapping from Voxtral language codes → contract enum
_VOXTRAL_LANG_MAP: dict[str, SupportedLanguage] = {
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
    "or": SupportedLanguage.OD_IN,
    "od": SupportedLanguage.OD_IN,
    "english": SupportedLanguage.EN_IN,
    "hindi": SupportedLanguage.HI_IN,
}


class VoxtralSTT(STTProvider):
    """
    Voxtral Mini STT adapter (testing provider).

    Same adapter pattern as Sarvam — retries, timeout, contract mapping.
    """

    def __init__(self, config: VoxtralConfig | None = None) -> None:
        self._config = config or VoxtralConfig()
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._config.timeout_seconds),
        )

    @property
    def provider_name(self) -> STTProviderName:
        return STTProviderName.VOXTRAL

    async def close(self) -> None:
        await self._client.aclose()

    async def transcribe(
        self,
        audio: bytes,
        *,
        request_id: str,
        language: Optional[str] = None,
    ) -> Transcript:
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
        files = {"file": ("audio.wav", io.BytesIO(audio), "audio/wav")}
        data: dict[str, str] = {"model": self._config.model}
        if language:
            data["language"] = language

        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
        }

        try:
            response = await self._client.post(
                self._config.endpoint,
                headers=headers,
                files=files,
                data=data,
            )
        except httpx.TimeoutException as exc:
            raise STTTimeoutError() from exc
        except httpx.HTTPError as exc:
            raise STTProviderError(f"Network error: {exc}") from exc

        if response.status_code >= 500:
            raise STTProviderError(
                f"Server error {response.status_code}",
                status_code=response.status_code,
            )
        if response.status_code >= 400:
            raise STTClientError(
                f"Client error {response.status_code}: {response.text[:300]}",
                status_code=response.status_code,
            )

        raw = VoxtralTranscriptResponse.model_validate(response.json())

        detected = self._resolve_language(raw.language, language)

        return Transcript(
            request_id=request_id,
            text=raw.text,
            language=detected,
            is_final=True,
            provider=STTProviderName.VOXTRAL,
        )

    @staticmethod
    def _resolve_language(
        detected: str | None,
        requested: str | None,
    ) -> SupportedLanguage:
        for code in (detected, requested):
            if code:
                normalised = code.lower().strip()
                if normalised in _VOXTRAL_LANG_MAP:
                    return _VOXTRAL_LANG_MAP[normalised]
                # Try direct match against enum values
                try:
                    return SupportedLanguage(normalised)
                except ValueError:
                    pass
        return SupportedLanguage.EN_IN

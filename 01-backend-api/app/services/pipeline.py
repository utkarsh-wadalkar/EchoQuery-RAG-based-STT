"""
VoicePipeline — orchestrates the full voice-query flow.

    audio → STT → Transcript → Query → RAG → Answer

Emits progress callbacks so the WebSocket handler can push live
``processing`` events to the frontend.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Awaitable, Callable

from ..middleware.errors import (
    RAGServiceError,
    STTServiceError,
    STTTimeoutServiceError,
)
from ..schemas.query import QueryRequest, SupportedLanguage
from ..schemas.response import AnswerResponse
from ..schemas.websocket import ProcessingStage
from ..services.rag_client import RAGClient

# Lazy import to avoid circular dependency at module level
import sys
import os

# Add the external-services directory to the path so we can import stt
_EXTERNAL_SERVICES = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "04-external-services"),
)
if _EXTERNAL_SERVICES not in sys.path:
    sys.path.insert(0, _EXTERNAL_SERVICES)

from stt.base import STTError, STTProvider, STTTimeoutError, Transcript  # noqa: E402

logger = logging.getLogger(__name__)

# Type alias for progress callbacks
ProgressCallback = Callable[[ProcessingStage], Awaitable[None]]


class VoicePipeline:
    """
    Orchestrates: audio → STT → RAG → answer.

    Parameters
    ----------
    stt_provider:
        The STT adapter to use for transcription.
    rag_client:
        The RAG engine client (mock or HTTP).
    """

    def __init__(
        self,
        stt_provider: STTProvider,
        rag_client: RAGClient,
    ) -> None:
        self._stt = stt_provider
        self._rag = rag_client

    async def run(
        self,
        audio: bytes,
        *,
        request_id: str | None = None,
        language: str | None = None,
        top_k: int = 5,
        session_id: str | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> tuple[Transcript, AnswerResponse]:
        """
        Execute the full pipeline.

        Returns
        -------
        tuple[Transcript, AnswerResponse]
            The STT transcript and the RAG answer.
        """
        rid = request_id or str(uuid.uuid4())
        t0 = time.perf_counter()

        # --- Stage 1: Transcription ----------------------------------------
        await self._emit(on_progress, ProcessingStage.TRANSCRIPTION)
        transcript = await self._transcribe(audio, request_id=rid, language=language)
        stt_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "[Pipeline] STT done request=%s stt=%.1fms text=%s",
            rid, stt_ms, transcript.text[:80],
        )

        # --- Stage 2: Build query ------------------------------------------
        await self._emit(on_progress, ProcessingStage.PREPROCESSING)
        query = QueryRequest(
            request_id=rid,
            query=transcript.text,
            language=SupportedLanguage(transcript.language.value),
            top_k=top_k,
            session_id=session_id,
        )

        # --- Stage 3–6: RAG pipeline --------------------------------------
        await self._emit(on_progress, ProcessingStage.EMBEDDING)
        answer = await self._query_rag(query, on_progress=on_progress)

        total_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "[Pipeline] Done request=%s total=%.1fms (stt=%.1fms rag=%.1fms)",
            rid, total_ms, stt_ms, answer.latency.total_ms,
        )

        return transcript, answer

    async def run_text(
        self,
        text: str,
        *,
        request_id: str | None = None,
        language: SupportedLanguage = SupportedLanguage.EN_IN,
        top_k: int = 5,
        session_id: str | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> AnswerResponse:
        """
        Execute the pipeline starting from text (skipping STT).

        Useful for testing the RAG connection directly.
        """
        rid = request_id or str(uuid.uuid4())

        await self._emit(on_progress, ProcessingStage.PREPROCESSING)
        query = QueryRequest(
            request_id=rid,
            query=text,
            language=language,
            top_k=top_k,
            session_id=session_id,
        )

        await self._emit(on_progress, ProcessingStage.EMBEDDING)
        return await self._query_rag(query, on_progress=on_progress)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _transcribe(
        self,
        audio: bytes,
        *,
        request_id: str,
        language: str | None,
    ) -> Transcript:
        try:
            return await self._stt.transcribe(
                audio, request_id=request_id, language=language,
            )
        except STTTimeoutError as exc:
            raise STTTimeoutServiceError(str(exc)) from exc
        except STTError as exc:
            raise STTServiceError(str(exc)) from exc

    async def _query_rag(
        self,
        query: QueryRequest,
        *,
        on_progress: ProgressCallback | None = None,
    ) -> AnswerResponse:
        try:
            # The RAG client handles its own internal stages, but we emit
            # coarse progress events here for the WebSocket.
            await self._emit(on_progress, ProcessingStage.RETRIEVAL)
            await self._emit(on_progress, ProcessingStage.RERANKING)
            await self._emit(on_progress, ProcessingStage.GENERATION)
            answer = await self._rag.query(query)
            await self._emit(on_progress, ProcessingStage.GROUNDING)
            return answer
        except Exception as exc:
            raise RAGServiceError(str(exc)) from exc

    @staticmethod
    async def _emit(
        callback: ProgressCallback | None,
        stage: ProcessingStage,
    ) -> None:
        if callback:
            await callback(stage)

"""
REST query endpoints.

- ``POST /api/v1/query/audio`` — audio file upload → STT → RAG → answer
- ``POST /api/v1/query/text``  — text query → RAG → answer (bypass STT)
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile

from ..dependencies import get_pipeline
from ...schemas.query import SupportedLanguage, TextQueryInput
from ...schemas.response import AnswerResponse
from ...services.audio import validate_audio
from ...services.pipeline import VoicePipeline
from ...config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/query", tags=["Query"])


@router.post(
    "/audio",
    response_model=AnswerResponse,
    summary="Voice query — upload audio file",
    description=(
        "Upload an audio file (WAV, MP3, FLAC, OGG, WebM, etc.).  "
        "The backend transcribes it via the configured STT provider, "
        "then queries the RAG engine and returns a grounded answer."
    ),
)
async def query_audio(
    audio: UploadFile = File(..., description="Audio file to transcribe"),
    language: SupportedLanguage | None = Form(
        default=None,
        description="Language hint.  ``null`` = auto-detect.",
    ),
    top_k: int = Form(default=5, ge=1, le=20),
    pipeline: VoicePipeline = Depends(get_pipeline),
) -> AnswerResponse:
    settings = get_settings()
    data = await audio.read()

    validate_audio(
        data,
        content_type=audio.content_type,
        max_size_mb=settings.max_audio_size_mb,
    )

    request_id = str(uuid.uuid4())
    lang_str = language.value if language else None

    _transcript, answer = await pipeline.run(
        data,
        request_id=request_id,
        language=lang_str,
        top_k=top_k,
    )

    return answer


@router.post(
    "/text",
    response_model=AnswerResponse,
    summary="Text query — bypass STT",
    description=(
        "Submit a text query directly to the RAG pipeline.  "
        "Useful for testing the RAG connection without audio."
    ),
)
async def query_text(
    body: TextQueryInput,
    pipeline: VoicePipeline = Depends(get_pipeline),
) -> AnswerResponse:
    request_id = str(uuid.uuid4())

    answer = await pipeline.run_text(
        body.query,
        request_id=request_id,
        language=body.language,
        top_k=body.top_k,
        session_id=body.session_id,
    )

    return answer

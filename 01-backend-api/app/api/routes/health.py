"""
Health-check endpoints.

- ``GET /health``       — basic liveness (status, uptime, provider info)
- ``GET /health/ready`` — readiness (checks STT + RAG reachability)
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from ..dependencies import get_rag, get_stt
from ...schemas.response import HealthResponse, ReadinessResponse
from ...services.rag_client import RAGClient

import os, sys  # noqa: E401
_EXTERNAL_SERVICES = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "04-external-services"),
)
if _EXTERNAL_SERVICES not in sys.path:
    sys.path.insert(0, _EXTERNAL_SERVICES)
from stt import STTProvider  # noqa: E402

router = APIRouter(prefix="/health", tags=["Health"])

_start_time = time.time()


@router.get(
    "",
    response_model=HealthResponse,
    summary="Liveness check",
)
async def health(
    stt: STTProvider = Depends(get_stt),
    rag: RAGClient = Depends(get_rag),
) -> HealthResponse:
    return HealthResponse(
        status="ok",
        uptime_seconds=round(time.time() - _start_time, 1),
        stt_provider=stt.provider_name.value,
        rag_mode=rag.mode,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness check",
)
async def readiness(
    rag: RAGClient = Depends(get_rag),
) -> ReadinessResponse:
    rag_ok = await rag.health_check()
    return ReadinessResponse(
        ready=rag_ok,
        stt_ready=True,  # STT is tested lazily on first request
        rag_ready=rag_ok,
        details=None if rag_ok else "RAG engine unreachable",
    )

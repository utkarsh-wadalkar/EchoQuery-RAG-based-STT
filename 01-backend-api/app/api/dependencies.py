"""
FastAPI dependency injection.

Provides singletons for the STT provider, RAG client, and VoicePipeline,
managed through the application lifespan.
"""

from __future__ import annotations

import logging
import os
import sys

from ..config.settings import Settings, get_settings
from ..services.rag_client import RAGClient, create_rag_client

# Add external-services to path for STT imports
_EXTERNAL_SERVICES = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "04-external-services"),
)
if _EXTERNAL_SERVICES not in sys.path:
    sys.path.insert(0, _EXTERNAL_SERVICES)

from stt import STTProvider, create_stt_provider  # noqa: E402
from ..services.pipeline import VoicePipeline  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singletons (initialised during app lifespan)
# ---------------------------------------------------------------------------
_stt_provider: STTProvider | None = None
_rag_client: RAGClient | None = None
_pipeline: VoicePipeline | None = None


async def init_services(settings: Settings | None = None) -> None:
    """Initialise all service singletons.  Called from app lifespan."""
    global _stt_provider, _rag_client, _pipeline

    s = settings or get_settings()

    _stt_provider = create_stt_provider(
        sarvam_api_key=s.sarvam_api_key,
        voxtral_api_key=s.voxtral_api_key,
        force_provider=s.stt_provider,
    )

    _rag_client = create_rag_client(
        endpoint=s.rag_endpoint,
        timeout=s.rag_timeout_seconds,
    )

    _pipeline = VoicePipeline(
        stt_provider=_stt_provider,
        rag_client=_rag_client,
    )

    logger.info(
        "Services initialised — STT=%s  RAG=%s",
        _stt_provider.provider_name.value,
        _rag_client.mode,
    )


async def shutdown_services() -> None:
    """Shut down all service singletons.  Called from app lifespan."""
    if _stt_provider:
        await _stt_provider.close()
    if _rag_client:
        await _rag_client.close()
    logger.info("Services shut down.")


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

def get_stt() -> STTProvider:
    assert _stt_provider is not None, "Services not initialised"
    return _stt_provider


def get_rag() -> RAGClient:
    assert _rag_client is not None, "Services not initialised"
    return _rag_client


def get_pipeline() -> VoicePipeline:
    assert _pipeline is not None, "Services not initialised"
    return _pipeline

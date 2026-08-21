"""
STT provider factory.

Auto-selects the best available provider based on configured API keys:

    Sarvam (production) → Voxtral (testing) → Mock (local dev)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base import STTProvider
from .mock.client import MockSTT
from .sarvam.client import SarvamSTT
from .sarvam.config import SarvamConfig
from .voxtral.client import VoxtralSTT
from .voxtral.config import VoxtralConfig

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def create_stt_provider(
    *,
    sarvam_api_key: str = "",
    voxtral_api_key: str = "",
    force_provider: str | None = None,
) -> STTProvider:
    """
    Create an STT provider.

    Parameters
    ----------
    sarvam_api_key:
        Sarvam API subscription key.  If provided, Sarvam is used.
    voxtral_api_key:
        Voxtral / Mistral API key.  Used if Sarvam key is absent.
    force_provider:
        Override auto-selection.  One of ``"sarvam"``, ``"voxtral"``, ``"mock"``.

    Returns
    -------
    STTProvider
        The selected provider, ready to use.
    """
    if force_provider == "mock":
        logger.info("STT provider: Mock (forced)")
        return MockSTT()

    if force_provider == "sarvam" or (not force_provider and sarvam_api_key):
        cfg = SarvamConfig(api_key=sarvam_api_key)
        logger.info("STT provider: Sarvam Saaras v3 (model=%s)", cfg.model)
        return SarvamSTT(config=cfg)

    if force_provider == "voxtral" or (not force_provider and voxtral_api_key):
        cfg = VoxtralConfig(api_key=voxtral_api_key)
        logger.info("STT provider: Voxtral Mini (model=%s)", cfg.model)
        return VoxtralSTT(config=cfg)

    logger.info(
        "STT provider: Mock (no API keys configured — local dev mode)",
    )
    return MockSTT()

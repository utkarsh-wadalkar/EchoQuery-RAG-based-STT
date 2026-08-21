"""
Audio validation and normalisation utilities.
"""

from __future__ import annotations

import logging

from ..middleware.errors import InvalidRequestError

logger = logging.getLogger(__name__)

# Supported MIME types and their file signatures (magic bytes)
_AUDIO_SIGNATURES: dict[bytes, str] = {
    b"RIFF": "audio/wav",
    b"\xff\xfb": "audio/mpeg",         # MP3
    b"\xff\xf3": "audio/mpeg",         # MP3
    b"\xff\xf2": "audio/mpeg",         # MP3
    b"ID3": "audio/mpeg",              # MP3 with ID3 tag
    b"fLaC": "audio/flac",
    b"OggS": "audio/ogg",
}

SUPPORTED_CONTENT_TYPES = {
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/flac",
    "audio/ogg",
    "audio/webm",
    "audio/aac",
    "audio/mp4",
    "application/octet-stream",  # browser recordings often lack MIME
}


def validate_audio(
    data: bytes,
    *,
    content_type: str | None = None,
    max_size_mb: float = 25.0,
) -> None:
    """
    Validate audio data.

    Raises ``InvalidRequestError`` on validation failure.
    """
    if not data:
        raise InvalidRequestError("No audio data received.")

    max_bytes = int(max_size_mb * 1024 * 1024)
    if len(data) > max_bytes:
        raise InvalidRequestError(
            f"Audio too large ({len(data) / 1024 / 1024:.1f} MB). "
            f"Maximum is {max_size_mb} MB.",
        )

    # Check content type if provided
    if content_type and content_type.lower() not in SUPPORTED_CONTENT_TYPES:
        logger.warning("Unusual content type: %s — attempting anyway", content_type)

    # Verify magic bytes (best-effort)
    detected = _detect_format(data)
    if detected is None and content_type == "application/octet-stream":
        logger.warning(
            "Could not detect audio format from magic bytes (size=%d). "
            "Proceeding anyway.",
            len(data),
        )


def _detect_format(data: bytes) -> str | None:
    """Detect audio format from file header magic bytes."""
    for signature, fmt in _AUDIO_SIGNATURES.items():
        if data[: len(signature)] == signature:
            return fmt
    return None

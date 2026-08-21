"""
WebSocket endpoint — full real-time voice query flow.

Protocol (per ``00-contracts/``):

    Client → Server:
        1. ``session_start`` (JSON)       — start a new session
        2. binary audio frames            — stream audio data
        3. ``audio_end`` (JSON)           — signal end of audio
        4. ``cancel`` (JSON)              — abort at any point

    Server → Client:
        1. ``transcript`` events          — STT results
        2. ``processing`` events          — pipeline stage updates
        3. ``answer`` event               — final RAG answer
        4. ``complete`` event             — session done
        5. ``error`` event                — on failure
"""

from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..dependencies import get_pipeline
from ...schemas.query import SupportedLanguage
from ...schemas.websocket import (
    ClientEventType,
    CompletionStatus,
    ErrorCode,
    ProcessingStage,
    make_answer_event,
    make_complete_event,
    make_error_event,
    make_processing_event,
    make_transcript_event,
)
from ...middleware.errors import AppError
from ...services.audio import validate_audio
from ...services.pipeline import VoicePipeline

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/query")
async def websocket_query(ws: WebSocket) -> None:
    """
    Full voice-query WebSocket endpoint.

    Follows the contract lifecycle:
    ``session_start`` → binary frames → ``audio_end`` → response events.
    """
    await ws.accept()
    pipeline: VoicePipeline = get_pipeline()

    request_id: str = ""
    language: str | None = None
    session_id: str | None = None
    audio_buffer: bytearray = bytearray()
    session_active = False

    try:
        while True:
            message = await ws.receive()

            # --- Client disconnected -----------------------------------
            if message.get("type") == "websocket.disconnect":
                logger.info("[WS] Client disconnected request=%s", request_id)
                break

            # --- Binary audio frame ------------------------------------
            if "bytes" in message and message["bytes"]:
                if not session_active:
                    await _send_error(
                        ws, request_id or "unknown",
                        ErrorCode.INVALID_REQUEST,
                        "Audio received before session_start.",
                    )
                    continue
                audio_buffer.extend(message["bytes"])
                continue

            # --- JSON control event ------------------------------------
            if "text" in message and message["text"]:
                try:
                    event = json.loads(message["text"])
                except json.JSONDecodeError:
                    await _send_error(
                        ws, request_id or "unknown",
                        ErrorCode.INVALID_REQUEST,
                        "Invalid JSON.",
                    )
                    continue

                event_type = event.get("type")

                # ---- session_start ----
                if event_type == ClientEventType.SESSION_START.value:
                    request_id = event.get("request_id", str(uuid.uuid4()))
                    language = event.get("language")
                    session_id = event.get("session_id")
                    audio_buffer = bytearray()
                    session_active = True

                    # Validate language upfront
                    if language:
                        try:
                            SupportedLanguage(language)
                        except ValueError:
                            await _send_error(
                                ws, request_id,
                                ErrorCode.UNSUPPORTED_LANGUAGE,
                                f"Language '{language}' is not supported.",
                            )
                            await _send_complete(ws, request_id, CompletionStatus.FAILED)
                            session_active = False
                            continue

                    logger.info(
                        "[WS] session_start request=%s lang=%s",
                        request_id, language,
                    )
                    continue

                # ---- audio_end ----
                if event_type == ClientEventType.AUDIO_END.value:
                    if not session_active:
                        continue

                    logger.info(
                        "[WS] audio_end request=%s buffer=%d bytes",
                        request_id, len(audio_buffer),
                    )

                    # Validate audio
                    try:
                        validate_audio(bytes(audio_buffer))
                    except AppError as exc:
                        await _send_error(
                            ws, request_id,
                            ErrorCode.INVALID_REQUEST,
                            str(exc),
                        )
                        await _send_complete(ws, request_id, CompletionStatus.FAILED)
                        session_active = False
                        continue

                    # Run the pipeline
                    try:
                        await _run_pipeline(
                            ws, pipeline,
                            audio=bytes(audio_buffer),
                            request_id=request_id,
                            language=language,
                            session_id=session_id,
                        )
                        await _send_complete(ws, request_id, CompletionStatus.SUCCESS)
                    except AppError as exc:
                        error_code = _map_app_error(exc)
                        await _send_error(
                            ws, request_id, error_code, str(exc),
                            retryable=exc.retryable,
                        )
                        await _send_complete(ws, request_id, CompletionStatus.FAILED)
                    except Exception:
                        logger.exception("Unhandled error in WS pipeline")
                        await _send_error(
                            ws, request_id,
                            ErrorCode.INTERNAL_ERROR,
                            "An unexpected error occurred.",
                        )
                        await _send_complete(ws, request_id, CompletionStatus.FAILED)

                    session_active = False
                    continue

                # ---- cancel ----
                if event_type == ClientEventType.CANCEL.value:
                    cancel_rid = event.get("request_id", request_id)
                    logger.info("[WS] cancel request=%s", cancel_rid)
                    session_active = False
                    await _send_complete(ws, cancel_rid, CompletionStatus.CANCELLED)
                    continue

    except WebSocketDisconnect:
        logger.info("[WS] Client disconnected request=%s", request_id)
    except Exception:
        logger.exception("[WS] Unexpected error")
        try:
            await _send_error(
                ws, request_id or "unknown",
                ErrorCode.INTERNAL_ERROR,
                "Internal server error.",
            )
            await _send_complete(
                ws, request_id or "unknown", CompletionStatus.FAILED,
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _run_pipeline(
    ws: WebSocket,
    pipeline: VoicePipeline,
    *,
    audio: bytes,
    request_id: str,
    language: str | None,
    session_id: str | None,
) -> None:
    """Run the voice pipeline and emit events to the WebSocket."""

    async def on_progress(stage: ProcessingStage) -> None:
        await ws.send_json(make_processing_event(request_id, stage))

    transcript, answer = await pipeline.run(
        audio,
        request_id=request_id,
        language=language,
        session_id=session_id,
        on_progress=on_progress,
    )

    # Emit transcript
    await ws.send_json(
        make_transcript_event(
            request_id,
            text=transcript.text,
            language=SupportedLanguage(transcript.language.value),
            is_final=transcript.is_final,
        ),
    )

    # Emit answer
    await ws.send_json(
        make_answer_event(request_id, answer.model_dump(mode="json")),
    )


async def _send_error(
    ws: WebSocket,
    request_id: str,
    code: ErrorCode,
    message: str,
    *,
    retryable: bool | None = None,
) -> None:
    await ws.send_json(
        make_error_event(request_id, code, message, retryable=retryable),
    )


async def _send_complete(
    ws: WebSocket,
    request_id: str,
    status: CompletionStatus,
) -> None:
    await ws.send_json(make_complete_event(request_id, status))


def _map_app_error(exc: AppError) -> ErrorCode:
    """Map an ``AppError`` to a contract error code."""
    code_map = {
        "INVALID_REQUEST": ErrorCode.INVALID_REQUEST,
        "UNSUPPORTED_LANGUAGE": ErrorCode.UNSUPPORTED_LANGUAGE,
        "STT_ERROR": ErrorCode.STT_ERROR,
        "STT_TIMEOUT": ErrorCode.STT_TIMEOUT,
        "RAG_ERROR": ErrorCode.RAG_ERROR,
        "RAG_TIMEOUT": ErrorCode.RAG_TIMEOUT,
    }
    return code_map.get(exc.code, ErrorCode.INTERNAL_ERROR)

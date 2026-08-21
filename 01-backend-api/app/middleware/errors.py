"""
Global error-handling middleware.

Maps domain exceptions to contract-compliant JSON error responses
(matching ``00-contracts/websocket-server-events.schema.json`` error codes).
"""

from __future__ import annotations

import logging
import traceback

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain exception hierarchy
# ---------------------------------------------------------------------------

class AppError(Exception):
    """Base application error."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.retryable = retryable


class InvalidRequestError(AppError):
    def __init__(self, message: str = "Invalid request") -> None:
        super().__init__(message, code="INVALID_REQUEST", status_code=400)


class UnsupportedLanguageError(AppError):
    def __init__(self, message: str = "Unsupported language") -> None:
        super().__init__(message, code="UNSUPPORTED_LANGUAGE", status_code=400)


class STTServiceError(AppError):
    def __init__(self, message: str = "STT service error") -> None:
        super().__init__(
            message, code="STT_ERROR", status_code=502, retryable=True,
        )


class STTTimeoutServiceError(AppError):
    def __init__(self, message: str = "STT service timed out") -> None:
        super().__init__(
            message, code="STT_TIMEOUT", status_code=504, retryable=True,
        )


class RAGServiceError(AppError):
    def __init__(self, message: str = "RAG service error") -> None:
        super().__init__(
            message, code="RAG_ERROR", status_code=502, retryable=True,
        )


class RAGTimeoutServiceError(AppError):
    def __init__(self, message: str = "RAG service timed out") -> None:
        super().__init__(
            message, code="RAG_TIMEOUT", status_code=504, retryable=True,
        )


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Catches unhandled exceptions and returns structured JSON errors.

    WebSocket endpoints handle their own errors inside the handler,
    so this middleware only affects HTTP routes.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> JSONResponse:
        try:
            return await call_next(request)
        except AppError as exc:
            logger.warning(
                "AppError [%s] %s (retryable=%s)",
                exc.code, exc, exc.retryable,
            )
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": {
                        "code": exc.code,
                        "message": str(exc),
                        "retryable": exc.retryable,
                    },
                },
            )
        except Exception:
            logger.error("Unhandled exception:\n%s", traceback.format_exc())
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An unexpected error occurred.",
                        "retryable": False,
                    },
                },
            )

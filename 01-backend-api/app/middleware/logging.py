"""
Structured-logging middleware.

Attaches ``request_id`` to every log record and records per-request
latency so we can correlate logs across the full pipeline.
"""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger("echoquery.access")


def _setup_logging(log_level: str = "INFO") -> None:
    """Configure structured logging for the application."""
    fmt = (
        "%(asctime)s | %(levelname)-7s | %(name)s | "
        "req=%(request_id)s | %(message)s"
    )

    class RequestIdFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            if not hasattr(record, "request_id"):
                record.request_id = "-"  # type: ignore[attr-defined]
            return True

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt))
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    # Avoid duplicate handlers on reload
    if not root.handlers:
        root.addHandler(handler)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every HTTP request with timing and a ``request_id``.

    The ``request_id`` is taken from the ``X-Request-ID`` header if
    provided by the client, otherwise a UUID is generated.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        # Store on request state so route handlers can access it
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "%s %s → %d (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            extra={"request_id": request_id},
        )

        response.headers["X-Request-ID"] = request_id
        return response

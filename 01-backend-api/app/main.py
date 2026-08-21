"""
EchoQuery Backend — FastAPI application entry point.

Start with::

    uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.dependencies import init_services, shutdown_services
from .api.routes.health import router as health_router
from .api.routes.query import router as query_router
from .api.routes.websocket import router as ws_router
from .config.settings import get_settings
from .middleware.errors import ErrorHandlerMiddleware
from .middleware.logging import RequestLoggingMiddleware, _setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — initialise and tear down services."""
    settings = get_settings()
    _setup_logging(settings.log_level)

    logger.info("Starting EchoQuery backend v%s", settings.app_version)
    await init_services(settings)

    yield

    logger.info("Shutting down EchoQuery backend")
    await shutdown_services()


def create_app() -> FastAPI:
    """Factory function to create the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="EchoQuery API",
        description=(
            "Voice-powered RAG query engine.  "
            "Upload audio or send text queries to get grounded answers "
            "from the knowledge base."
        ),
        version=settings.app_version,
        lifespan=lifespan,
    )

    # --- Middleware (order matters: outermost first) --------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    # --- Routes --------------------------------------------------------
    app.include_router(health_router)
    app.include_router(query_router)
    app.include_router(ws_router)

    return app


# Create the application instance (used by ``uvicorn app.main:app``)
app = create_app()

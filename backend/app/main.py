from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import anyio.to_thread
from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import (
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
    configure_logging,
)
from app.core.security import SecurityManager
from app.db.session import Database
from app.documents.storage import create_storage
from app.ai.providers import create_ai_provider


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        anyio.to_thread.current_default_thread_limiter().total_tokens = 8
        database = Database(
            app_settings.database_url,
            connect_timeout_seconds=app_settings.readiness_timeout_seconds,
        )
        app.state.settings = app_settings
        app.state.database = database
        app.state.security = SecurityManager(app_settings)
        app.state.storage = create_storage(app_settings)
        app.state.ai_provider = create_ai_provider(app_settings)
        yield
        database.dispose()

    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        docs_url="/docs" if app_settings.docs_enabled else None,
        redoc_url="/redoc" if app_settings.docs_enabled else None,
        openapi_url="/openapi.json" if app_settings.docs_enabled else None,
        lifespan=lifespan,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.include_router(api_router)
    return app

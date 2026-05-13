"""
PPT Master Web Service - FastAPI Application Entry Point.

Creates and configures the FastAPI application with:
- Lifespan event handlers (DB connect/disconnect)
- CORS configuration
- Static file serving
- API router registration
- WebSocket support
- Health check endpoint
- OpenAPI documentation
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict

# Load .env file EARLY, before any os.getenv calls.
# pydantic-settings in app.core.config does this too, but that module
# is imported too late in the startup chain (after _init_database runs).
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.api.deps import set_db_session_factory
from app.api.websocket import router as ws_router, ws_manager
from app.core.schemas import ErrorResponse, HealthCheckResponse


# ────────────────────────────────
# Database Setup
# ────────────────────────────────


async def _init_database() -> Any:
    """Initialize async database engine and session factory.

    Returns:
        Tuple of (engine, session_factory).
    """
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    database_url = os.getenv("DATABASE_URL") or os.getenv(
        "DB_URL",
        "postgresql+asyncpg://pptmaster:pptmaster@localhost:5432/pptmaster",
    )

    engine = create_async_engine(
        database_url,
        echo=os.getenv("DEBUG", "false").lower() == "true",
        pool_pre_ping=True,
        pool_recycle=300,
    )

    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
        autoflush=False,
    )

    return engine, session_factory


# ────────────────────────────────
# Lifespan Events
# ────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler.

    Startup:
        - Creates async database engine
        - Initializes session factory
        - Sets up storage backend

    Shutdown:
        - Disposes database engine
        - Cleans up resources
    """
    # ─── Startup ───
    engine, session_factory = await _init_database()
    set_db_session_factory(session_factory)

    # Store engine reference for shutdown
    app.state.db_engine = engine
    app.state.session_factory = session_factory

    # Create tables if configured (development only)
    if os.getenv("AUTO_CREATE_TABLES", "false").lower() == "true":
        from app.db.base import Base

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # Initialize storage backend
    from app.services.storage_service import get_storage_backend

    storage = get_storage_backend()
    app.state.storage = storage

    # Initialize Celery app (optional — gracefully skipped if Redis unavailable)
    try:
        from app.core.celery_app import celery_app
        app.state.celery = celery_app
    except Exception:
        app.state.celery = None

    # Log startup
    print(f"[{datetime.now(timezone.utc).isoformat()}] PPT Master Web Service started")
    print(f"  - API docs: http://localhost:8000/docs")
    print(f"  - Health:   http://localhost:8000/health")

    yield

    # ─── Shutdown ───
    await engine.dispose()
    print(f"[{datetime.now(timezone.utc).isoformat()}] PPT Master Web Service stopped")


# ────────────────────────────────
# FastAPI Application
# ────────────────────────────────

app = FastAPI(
    title="PPT Master Web Service",
    description=(
        "Backend API for the PPT Master Web Service. "
        "Provides project management, pipeline orchestration, "
        "SVG page editing, and PPTX export capabilities."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    contact={
        "name": "PPT Master Team",
    },
    license_info={
        "name": "MIT",
    },
)

# ────────────────────────────────
# CORS Configuration
# ────────────────────────────────

# Read CORS origins from environment
_cors_origins_env = os.getenv("CORS_ORIGINS", "")
if _cors_origins_env:
    _cors_origins = [origin.strip() for origin in _cors_origins_env.split(",")]
else:
    # Default: allow common development origins
    _cors_origins = [
        "http://localhost:3000",  # Vue dev server
        "http://localhost:5173",  # Vite dev server
        "http://localhost:8080",  # Alternative dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Total-Count"],
)

# ────────────────────────────────
# Static Files
# ────────────────────────────────

_storage_dir = os.getenv("LOCAL_STORAGE_DIR", "./storage")
if os.path.isdir(_storage_dir):
    app.mount("/storage", StaticFiles(directory=_storage_dir), name="storage")

# ────────────────────────────────
# Global Exception Handlers
# ────────────────────────────────


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle ValueError as 400 Bad Request."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            detail=str(exc),
            error_code="validation_error",
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Handle unhandled exceptions as 500 Internal Server Error."""
    import traceback

    error_detail = str(exc) if os.getenv("DEBUG") == "true" else "Internal server error"
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            detail=error_detail,
            error_code="internal_error",
        ).model_dump(),
    )


# ────────────────────────────────
# Router Registration
# ────────────────────────────────

# API routes under /api prefix
app.include_router(api_router)

# WebSocket routes (not under /api prefix)
app.include_router(ws_router)

# ────────────────────────────────
# Health Check
# ────────────────────────────────


@app.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health check",
    description="Check service health and dependency availability.",
    tags=["health"],
)
async def health_check() -> Dict[str, Any]:
    """Health check endpoint.

    Returns service status and basic connectivity info.
    """
    services: Dict[str, str] = {"api": "ok"}

    # Check database
    try:
        from app.api.deps import get_db_session_factory

        factory = get_db_session_factory()
        if factory is not None:
            services["database"] = "ok"
        else:
            services["database"] = "not_initialized"
    except Exception as exc:
        services["database"] = f"error: {exc}"

    # Check Redis (via Celery)
    try:
        from app.core.celery_app import celery_app

        inspector = celery_app.control.inspect()
        ping = inspector.ping()
        services["celery"] = "ok" if ping else "no_workers"
    except Exception:
        services["celery"] = "disabled"

    return {
        "status": "ok" if all(v == "ok" for v in services.values()) else "degraded",
        "version": "0.1.0",
        "services": services,
    }


# ────────────────────────────────
# WebSocket Status Endpoint
# ────────────────────────────────


@app.get(
    "/ws-status",
    summary="WebSocket connection status",
    description="Get current WebSocket connection statistics.",
    tags=["websocket"],
)
async def websocket_status() -> Dict[str, Any]:
    """Get WebSocket connection statistics.

    Returns:
        Connection counts and project subscriptions.
    """
    return ws_manager.get_stats()

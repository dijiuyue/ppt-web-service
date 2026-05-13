"""
PPT Master Web Service - Dependency Injection.

Provides FastAPI dependencies for:
- Database session management
- Storage backend access
- Current project resolution
- API key authentication
"""

import os
from typing import Any, AsyncGenerator, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.schemas import ErrorResponse
from app.services.storage_service import StorageBackend, get_storage_backend

# Lazy imports for database to avoid circular dependencies
# Database session factory - set up during app lifespan
_db_session_factory: Optional[Any] = None

# ────────────────────────────────
# Database Dependency
# ────────────────────────────────


async def get_db() -> AsyncGenerator[Any, None]:
    """Yield an async database session.

    Uses SQLAlchemy async session. The session is committed on success
    and rolled back on exception.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    global _db_session_factory
    if _db_session_factory is None:
        raise RuntimeError("Database session factory not initialized")

    async with _db_session_factory() as session:
        try:
            yield session
            await session.commit()
        except HTTPException:
            await session.rollback()
            raise
        except Exception:
            await session.rollback()
            raise


async def get_db_ro() -> AsyncGenerator[Any, None]:
    """Yield a read-only database session (no auto-commit)."""
    from sqlalchemy.ext.asyncio import AsyncSession

    global _db_session_factory
    if _db_session_factory is None:
        raise RuntimeError("Database session factory not initialized")

    async with _db_session_factory() as session:
        yield session


# ────────────────────────────────
# Storage Dependency
# ────────────────────────────────


async def get_storage() -> StorageBackend:
    """Return the configured storage backend."""
    return get_storage_backend()


# ────────────────────────────────
# Project Dependency
# ────────────────────────────────


async def get_current_project(
    id: UUID,
    db: Any = Depends(get_db_ro),
) -> Any:
    """Resolve the current project from path parameter.

    Args:
        id: Project UUID from the URL path.
        db: Database session.

    Returns:
        The Project ORM instance.

    Raises:
        HTTPException 404: If project not found.
    """
    from sqlalchemy import select
    from app.models.project import Project

    result = await db.execute(select(Project).where(Project.id == id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{id}' not found",
        )
    return project


# ────────────────────────────────
# API Key Authentication
# ────────────────────────────────


security_bearer = HTTPBearer(auto_error=False)


async def verify_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
) -> str:
    """Verify the API key from Authorization header.

    In development mode (DEBUG=true), API key is optional.
    """
    api_key = os.getenv("API_KEY", "")
    debug = os.getenv("DEBUG", "false").lower() == "true"

    if not api_key:
        # No API key configured - allow in debug mode
        if debug:
            return "debug"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key not configured on server",
        )

    if credentials is None:
        if debug:
            return "debug"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.credentials != api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return credentials.credentials


# ────────────────────────────────
# Optional Auth (no error if missing)
# ────────────────────────────────


async def optional_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
) -> Optional[str]:
    """Optional API key - returns the key if provided, None otherwise."""
    api_key = os.getenv("API_KEY", "")
    debug = os.getenv("DEBUG", "false").lower() == "true"

    if credentials and credentials.credentials == api_key:
        return credentials.credentials
    if debug:
        return "debug"
    return None


# ────────────────────────────────
# Pagination Dependency
# ────────────────────────────────


class PaginationParams:
    """Pagination query parameters."""

    def __init__(
        self,
        page: int = Query(default=1, ge=1, description="Page number (1-based)"),
        page_size: int = Query(
            default=20, ge=1, le=100, description="Items per page"
        ),
    ) -> None:
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size


# ────────────────────────────────
# DB Factory Setup
# ────────────────────────────────


def set_db_session_factory(factory: Any) -> None:
    """Set the database session factory (called during app startup)."""
    global _db_session_factory
    _db_session_factory = factory


def get_db_session_factory() -> Optional[Any]:
    """Get the current database session factory."""
    return _db_session_factory

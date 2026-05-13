"""Async database engine, session management and dependency injection.

Typical usage in a FastAPI route::

    from app.core.database import AsyncSession, get_db

    @router.get("/items")
    async def list_items(db: AsyncSession = Depends(get_db)):
        ...
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.db.base import Base

# ---------------------------------------------------------------------------
# Engine & session factory
# ---------------------------------------------------------------------------

_engine: Optional[AsyncEngine] = None
_async_session_maker: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine() -> AsyncEngine:
    """Return (or create) the singleton async engine."""
    global _engine
    if _engine is None:
        engine_kwargs = {"echo": settings.db.echo, "future": True}
        # SQLite does not support connection pool sizing
        if "sqlite" not in settings.db.url:
            engine_kwargs.update(
                pool_size=settings.db.pool_size,
                max_overflow=settings.db.max_overflow,
                pool_timeout=settings.db.pool_timeout,
                pool_recycle=settings.db.pool_recycle,
            )
        _engine = create_async_engine(settings.db.url, **engine_kwargs)
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Return (or create) the async session maker."""
    global _async_session_maker
    if _async_session_maker is None:
        _async_session_maker = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _async_session_maker


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session for FastAPI ``Depends``."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Lifecycle helpers
# ---------------------------------------------------------------------------


async def init_db() -> None:
    """Create all tables defined by ``Base.metadata``.

    Also initialises the session factory so that ``get_db()`` works
    immediately (required for test suites using SQLite).

    .. note::
        In production prefer Alembic migrations over this function.
    """
    global _async_session_maker
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Ensure session factory is ready – get_db() depends on it
    if _async_session_maker is None:
        _async_session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )


async def close_db() -> None:
    """Dispose the engine and clean up resources."""
    global _engine, _async_session_maker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
    _async_session_maker = None

"""SQLAlchemy declarative base for all ORM models."""

from __future__ import annotations

import uuid as _stdlib_uuid

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import Uuid as _UuidType


# Patch Uuid type to accept string values (common in API/test code)
def _patched_bind_processor(self, dialect):
    def process(value):
        if value is None:
            return None
        if isinstance(value, str):
            value = _stdlib_uuid.UUID(value)
        return value.hex
    return process

_UuidType.bind_processor = _patched_bind_processor


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models.

    Subclasses should define ``__tablename__`` and use
    ``Mapped`` / ``mapped_column`` annotations (SQLAlchemy 2.0 style).
    """

    @classmethod
    def select(cls):
        from sqlalchemy import select
        return select(cls)

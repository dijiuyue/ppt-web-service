"""SourceFile model — uploaded documents / URLs that feed the pipeline."""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SourceFileType(str, enum.Enum):
    """Supported source file formats."""

    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"
    URL = "url"
    MD = "md"
    TXT = "txt"
    HTML = "html"
    EPUB = "epub"


class ConversionStatus(str, enum.Enum):
    """Markdown conversion status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class SourceFile(Base):
    """An uploaded source file or URL attached to a project."""

    __tablename__ = "source_files"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="User-visible filename",
    )
    file_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="File type enum",
    )
    storage_key: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="Path in MinIO / local filesystem",
    )
    storage_backend: Mapped[str] = mapped_column(
        String(16),
        default="minio",
        nullable=False,
        comment="Backend that holds the file: minio / local",
    )
    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Size in bytes",
    )

    # Converted markdown
    markdown_content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Converted markdown text (inline for small files)",
    )
    markdown_storage_key: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Path to the converted .md file",
    )

    # Conversion status
    conversion_status: Mapped[str] = mapped_column(
        String(16),
        default=ConversionStatus.PENDING.value,
        nullable=False,
    )
    conversion_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if conversion failed",
    )

    # Ordering
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Display order within the project",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="source_files",
    )

    def __repr__(self) -> str:
        return f"<SourceFile {self.id} {self.original_filename}>"

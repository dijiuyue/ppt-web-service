"""PPTXExport model — exported PowerPoint files.

Records the result of the ``post_processing`` step where SVG pages
are compiled into a downloadable ``.pptx`` file.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ExportType(str, enum.Enum):
    """Kind of PPTX export."""

    NATIVE = "native"
    SVG_PREVIEW = "svg_preview"


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class PPTXExport(Base):
    """A PPTX export artefact."""

    __tablename__ = "pptx_exports"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    export_type: Mapped[str] = mapped_column(
        String(16),
        default=ExportType.NATIVE.value,
        nullable=False,
        comment="native / svg_preview",
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment='e.g. "project_name_20240115_120000.pptx"',
    )
    storage_key: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="Object storage path to the .pptx file",
    )
    storage_backend: Mapped[str] = mapped_column(
        String(16),
        default="minio",
        nullable=False,
    )
    file_size: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Size in bytes",
    )

    # Animation / transition configuration
    transition_effect: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="Slide transition effect name",
    )
    animation_effect: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="Animation effect name",
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="pptx_exports",
    )

    def __repr__(self) -> str:
        return f"<PPTXExport {self.id} {self.filename}>"

"""SpeakerNote model — per-slide speaker notes.

Generated during the post-processing step and optionally split into
individual files for export.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.svg_page import SVGPage


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class SpeakerNote(Base):
    """Speaker notes attached to a single SVG page."""

    __tablename__ = "speaker_notes"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    svg_page_id: Mapped[UUID] = mapped_column(
        ForeignKey("svg_pages.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    page_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="1-based page index (denormalised for convenience)",
    )
    page_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Page name identifier",
    )

    # Content
    note_content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Full speaker note text for this page",
    )

    # Split file
    split_storage_key: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Object storage key for the individual .md note file",
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
        back_populates="speaker_notes",
    )
    svg_page: Mapped["SVGPage"] = relationship(
        "SVGPage",
        back_populates="speaker_note",
    )

    def __repr__(self) -> str:
        return f"<SpeakerNote page={self.page_number} project={self.project_id}>"

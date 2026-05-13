"""SVGPage model — a single slide rendered as SVG.

The Executor step produces one ``SVGPage`` per presentation page.
Quality-check results and an optional speaker note are stored inline
or via relationships.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.speaker_note import SpeakerNote


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class QualityCheckStatus(str, enum.Enum):
    """Result of the automated SVG quality checker."""

    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


class PageRhythm(str, enum.Enum):
    """Visual rhythm classification for a page."""

    ANCHOR = "anchor"
    DENSE = "dense"
    BREATHING = "breathing"


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class SVGPage(Base):
    """An individual SVG slide belonging to a project."""

    __tablename__ = "svg_pages"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    page_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="1-based page index",
    )
    page_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment='e.g. "cover", "content_1"',
    )
    filename: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment='e.g. "01_cover.svg"',
    )

    # SVG payload
    svg_content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="SVG XML text (inline for small files)",
    )
    svg_storage_key: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Object storage key for the .svg file",
    )

    # Page attributes
    page_rhythm: Mapped[Optional[str]] = mapped_column(
        String(16),
        nullable=True,
        comment="anchor / dense / breathing",
    )
    page_layout: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="Layout template name",
    )
    page_chart: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="Chart type if applicable",
    )

    # Quality check
    quality_check_status: Mapped[str] = mapped_column(
        String(16),
        default=QualityCheckStatus.PENDING.value,
        nullable=False,
    )
    quality_check_errors: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        comment="List of error strings",
    )
    quality_check_warnings: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        comment="List of warning strings",
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
        back_populates="svg_pages",
    )
    speaker_note: Mapped[Optional["SpeakerNote"]] = relationship(
        "SpeakerNote",
        back_populates="svg_page",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<SVGPage {self.page_number:02d} {self.page_name} project={self.project_id}>"

"""SpecLock model — machine-readable design specification.

The *spec lock* is the parsed, structured counterpart of
:py:class:`~app.models.design_spec.DesignSpec`.  It contains exact
values ( colours, fonts, icon libraries, page layouts ) that the
Executor step consumes when generating SVG pages.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class SpecLock(Base):
    """Machine-readable design spec lock."""

    __tablename__ = "spec_locks"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Canvas
    canvas_viewbox: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment='SVG viewBox string, e.g. "0 0 1280 720"',
    )
    canvas_format: Mapped[Optional[str]] = mapped_column(
        String(16),
        nullable=True,
        comment="Canvas format identifier",
    )

    # Parsed structured fields
    colors: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON: {bg, primary, accent, secondary_accent, text, text_secondary, border, ...}",
    )
    typography: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON: {font_family, title_family, body_family, body_size, title_size, ...}",
    )
    icons: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON: {library, brand_library, inventory, stroke_width}",
    )
    images: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        comment='JSON: [{name, path, no_crop}, ...]',
    )
    page_rhythm: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment='JSON: {"P01": "anchor", "P02": "dense", ...}',
    )
    page_layouts: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment='JSON: {"P01": "01_cover", ...}',
    )
    page_charts: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment='JSON: {"P05": "bar_chart", ...}',
    )
    forbidden: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        comment='JSON: ["rule1", "rule2"]',
    )

    # Original markdown content
    lock_content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Raw markdown text of the spec lock",
    )
    lock_storage_key: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Object storage key for the lock file",
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
        back_populates="spec_lock",
    )

    def __repr__(self) -> str:
        return f"<SpecLock {self.id} project={self.project_id}>"

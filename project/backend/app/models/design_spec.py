"""DesignSpec model — the strategist output and Eight Confirmations.

Holds the human-readable ``design_spec.md`` content as well as the
individual *Eight Confirmations* fields that the user reviews and
approves before the pipeline continues.
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


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ConfirmationStatus(str, enum.Enum):
    """Whether the user has confirmed the Eight Confirmations."""

    PENDING = "pending"
    CONFIRMED = "confirmed"


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class DesignSpec(Base):
    """Design specification produced by the Strategist step."""

    __tablename__ = "design_specs"

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

    # ------------------ Eight Confirmations ------------------
    confirmation_canvas: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="Confirmed canvas format",
    )
    confirmation_page_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Confirmed number of pages",
    )
    confirmation_audience: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Target audience description",
    )
    confirmation_style_mode: Mapped[Optional[str]] = mapped_column(
        String(8),
        nullable=True,
        comment="Style mode: A / B / C",
    )
    confirmation_style_descriptor: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable style description",
    )
    confirmation_color_scheme: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON: {primary, secondary, accent, ...}",
    )
    confirmation_icon_approach: Mapped[Optional[str]] = mapped_column(
        String(8),
        nullable=True,
        comment="Icon approach: A / B / C / D",
    )
    confirmation_typography: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON: {title_font, body_font, ...}",
    )
    confirmation_image_approach: Mapped[Optional[str]] = mapped_column(
        String(8),
        nullable=True,
        comment="Image approach: A / B / C / D / E",
    )

    # Confirmation status
    confirmation_status: Mapped[str] = mapped_column(
        String(16),
        default="pending",
        nullable=False,
        comment="pending / confirmed",
    )
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="When the user confirmed",
    )

    # Full design_spec.md content
    spec_content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Complete markdown text of the design spec",
    )
    spec_storage_key: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Object storage key for the spec file",
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
        back_populates="design_spec",
    )

    def __repr__(self) -> str:
        return f"<DesignSpec {self.id} project={self.project_id} status={self.confirmation_status}>"

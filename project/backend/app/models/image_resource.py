"""ImageResource model — images used in the presentation.

Tracks every image needed by the pipeline: AI-generated, web-sourced,
user-uploaded or placeholder.  The Executor step references these
records when embedding images into SVG pages.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Float, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ImageAcquireVia(str, enum.Enum):
    """How the image was (or will be) obtained."""

    AI = "ai"
    WEB = "web"
    USER = "user"
    PLACEHOLDER = "placeholder"


class ImageStatus(str, enum.Enum):
    """Processing status of an image resource."""

    PENDING = "pending"
    GENERATED = "generated"
    SOURCED = "sourced"
    EXISTING = "existing"
    NEEDS_MANUAL = "needs_manual"
    PLACEHOLDER = "placeholder"


class ImageType(str, enum.Enum):
    """Semantic category of the image."""

    BACKGROUND = "Background"
    PHOTOGRAPHY = "Photography"
    ILLUSTRATION = "Illustration"
    DIAGRAM = "Diagram"
    DECORATIVE = "Decorative"


class LicenseTier(str, enum.Enum):
    """Licensing requirements for web-sourced images."""

    NO_ATTRIBUTION = "no-attribution"
    ATTRIBUTION_REQUIRED = "attribution-required"


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class ImageResource(Base):
    """An image asset associated with a project."""

    __tablename__ = "image_resources"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Display / file name",
    )
    dimensions: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment='Pixel dimensions, e.g. "1280x720"',
    )
    ratio: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Aspect ratio (width / height)",
    )
    purpose: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Human-readable purpose / placement hint",
    )
    image_type: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="Semantic type: Background/Photography/Illustration/Diagram/Decorative",
    )

    # Acquisition
    acquire_via: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="ai / web / user / placeholder",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        default=ImageStatus.PENDING.value,
        nullable=False,
    )

    # AI generation
    generation_prompt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Prompt used for AI image generation",
    )
    generation_backend: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="Backend/service used for generation",
    )

    # Web search
    search_query: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Query that produced the image",
    )
    source_url: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
        comment="Original URL",
    )
    attribution_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Attribution line required by licence",
    )
    license_tier: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="no-attribution / attribution-required",
    )

    # Storage
    storage_key: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Path to the processed / final image",
    )
    storage_backend: Mapped[str] = mapped_column(
        String(16),
        default="minio",
        nullable=False,
    )

    # User upload
    original_storage_key: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Path to the user-uploaded original (before processing)",
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
        back_populates="image_resources",
    )

    def __repr__(self) -> str:
        return f"<ImageResource {self.id} {self.filename} ({self.status})>"

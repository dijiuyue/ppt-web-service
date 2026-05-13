"""Project model — the central entity of the PPT Master pipeline.

A *Project* tracks the lifecycle of a PPT creation job, from initial draft
through source-file ingestion, strategist confirmation, image acquisition,
SVG page generation and final export.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.design_spec import DesignSpec
    from app.models.image_resource import ImageResource
    from app.models.pipeline_job import PipelineJob
    from app.models.pptx_export import PPTXExport
    from app.models.source_file import SourceFile
    from app.models.speaker_note import SpeakerNote
    from app.models.spec_lock import SpecLock
    from app.models.svg_page import SVGPage


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ProjectStatus(str, enum.Enum):
    """High-level lifecycle state of a project."""

    DRAFT = "draft"
    CONFIRMING = "confirming"  # waiting for Eight Confirmations
    PROCESSING = "processing"  # pipeline running
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineStep(str, enum.Enum):
    """Individual stages of the generation pipeline."""

    INIT = "init"
    SOURCE_PROCESSING = "source_processing"
    STRATEGIST = "strategist"
    IMAGE_ACQUISITION = "image_acquisition"
    EXECUTOR = "executor"
    POST_PROCESSING = "post_processing"
    COMPLETED = "completed"


class StepStatus(str, enum.Enum):
    """Execution status of the *current* pipeline step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_CONFIRMATION = "waiting_confirmation"


class CanvasFormat(str, enum.Enum):
    """Supported slide canvas formats."""

    PPT169 = "ppt169"
    PPT43 = "ppt43"
    XHS = "xhs"
    STORY = "story"


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class Project(Base):
    """Project master table."""

    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        comment="Unique project identifier",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable project name",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional project description",
    )
    canvas_format: Mapped[str] = mapped_column(
        String(16),
        default=CanvasFormat.PPT169.value,
        nullable=False,
        comment="Slide aspect ratio",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=ProjectStatus.DRAFT.value,
        nullable=False,
        comment="Overall project status",
    )

    # Pipeline tracking
    current_step: Mapped[str] = mapped_column(
        String(32),
        default=PipelineStep.INIT.value,
        nullable=False,
        comment="Current pipeline step",
    )
    step_status: Mapped[str] = mapped_column(
        String(32),
        default=StepStatus.PENDING.value,
        nullable=False,
        comment="Status of the current step",
    )

    # LLM configuration
    llm_provider: Mapped[str] = mapped_column(
        String(32),
        default="openai",
        nullable=False,
        comment="LLM provider: openai / anthropic",
    )
    llm_model: Mapped[str] = mapped_column(
        String(64),
        default="gpt-4o",
        nullable=False,
        comment="Model identifier",
    )

    # Template
    template_path: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Path to the template directory",
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
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="When the pipeline reached 'completed'",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    source_files: Mapped[list["SourceFile"]] = relationship(
        "SourceFile",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    design_spec: Mapped[Optional["DesignSpec"]] = relationship(
        "DesignSpec",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    spec_lock: Mapped[Optional["SpecLock"]] = relationship(
        "SpecLock",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    image_resources: Mapped[list["ImageResource"]] = relationship(
        "ImageResource",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    svg_pages: Mapped[list["SVGPage"]] = relationship(
        "SVGPage",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    speaker_notes: Mapped[list["SpeakerNote"]] = relationship(
        "SpeakerNote",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    pptx_exports: Mapped[list["PPTXExport"]] = relationship(
        "PPTXExport",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    pipeline_jobs: Mapped[list["PipelineJob"]] = relationship(
        "PipelineJob",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Project {self.id} '{self.name}' ({self.status})>"

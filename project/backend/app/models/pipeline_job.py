"""PipelineJob model — tracks execution of every pipeline step.

Each time a Celery task is spawned for a project a ``PipelineJob``
record is created so that progress, logs and errors can be inspected
via the REST API and WebSocket feeds.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PipelineStep(str, enum.Enum):
    """Individual stages of the generation pipeline."""

    INIT = "init"
    SOURCE_PROCESSING = "source_processing"
    STRATEGIST = "strategist"
    IMAGE_ACQUISITION = "image_acquisition"
    EXECUTOR = "executor"
    POST_PROCESSING = "post_processing"
    COMPLETED = "completed"


class JobStatus(str, enum.Enum):
    """Execution status of a pipeline job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_CONFIRMATION = "waiting_confirmation"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class PipelineJob(Base):
    """A single pipeline job ( Celery task execution record )."""

    __tablename__ = "pipeline_jobs"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    step: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Pipeline step name",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=JobStatus.PENDING.value,
        nullable=False,
    )

    # Celery tracking
    celery_task_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="Celery task UUID",
    )

    # Input / output payloads
    input_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Serialised input arguments",
    )
    output_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Serialised result / metadata",
    )

    # Error details
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable error summary",
    )
    error_traceback: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Full traceback text",
    )

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="When the job started executing",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="When the job finished ( success or failure )",
    )
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="pipeline_jobs",
    )

    def __repr__(self) -> str:
        return (
            f"<PipelineJob {self.id} step={self.step} "
            f"status={self.status} project={self.project_id}>"
        )

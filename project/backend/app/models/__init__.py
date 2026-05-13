"""PPT Master ORM models and enumerations.

Import this module to register all models with SQLAlchemy metadata::

    from app.models import Base, Project, SourceFile, ...
"""

from __future__ import annotations

from app.db.base import Base
from app.models.design_spec import ConfirmationStatus, DesignSpec
from app.models.image_resource import (
    ImageAcquireVia,
    ImageResource,
    ImageStatus,
    ImageType,
    LicenseTier,
)
from app.models.pipeline_job import JobStatus, PipelineJob
from app.models.pptx_export import ExportType, PPTXExport
from app.models.source_file import ConversionStatus, SourceFile, SourceFileType
from app.models.speaker_note import SpeakerNote
from app.models.spec_lock import SpecLock
from app.models.project import (
    CanvasFormat,
    PipelineStep,
    Project,
    ProjectStatus,
    StepStatus,
)
from app.models.svg_page import PageRhythm, QualityCheckStatus, SVGPage

__all__ = [
    # Base
    "Base",
    # Models
    "DesignSpec",
    "ImageResource",
    "PipelineJob",
    "PPTXExport",
    "Project",
    "SourceFile",
    "SpeakerNote",
    "SpecLock",
    "SVGPage",
    # Enums
    "CanvasFormat",
    "ConfirmationStatus",
    "ConversionStatus",
    "ExportType",
    "ImageAcquireVia",
    "ImageStatus",
    "ImageType",
    "JobStatus",
    "LicenseTier",
    "PageRhythm",
    "PipelineStep",
    "ProjectStatus",
    "QualityCheckStatus",
    "SourceFileType",
    "StepStatus",
]

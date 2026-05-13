"""
PPT Master Web Service - Pydantic v2 Schemas.

All request/response models for API data validation and serialization.
Uses Pydantic v2 syntax (model_config, model_validate, etc.).
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ────────────────────────────────
# Enum Definitions
# ────────────────────────────────


class ProjectStatus(str, Enum):
    """Project lifecycle status."""

    DRAFT = "draft"
    CONFIRMING = "confirming"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineStep(str, Enum):
    """Pipeline execution step."""

    INIT = "init"
    SOURCE_PROCESSING = "source_processing"
    STRATEGIST = "strategist"
    IMAGE_ACQUISITION = "image_acquisition"
    EXECUTOR = "executor"
    POST_PROCESSING = "post_processing"
    COMPLETED = "completed"


class StepStatus(str, Enum):
    """Status of the current pipeline step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_CONFIRMATION = "waiting_confirmation"


class JobStatus(str, Enum):
    """Pipeline job execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_CONFIRMATION = "waiting_confirmation"
    CANCELLED = "cancelled"


class CanvasFormat(str, Enum):
    """Available canvas aspect ratios."""

    PPT169 = "ppt169"
    PPT43 = "ppt43"
    XHS = "xhs"
    STORY = "story"


class FileType(str, Enum):
    """Supported source file types."""

    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"
    URL = "url"
    MD = "md"
    TXT = "txt"
    HTML = "html"
    EPUB = "epub"


class ConversionStatus(str, Enum):
    """Source file conversion status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ConfirmationStatus(str, Enum):
    """Eight Confirmations status."""

    PENDING = "pending"
    CONFIRMED = "confirmed"


class ImageType(str, Enum):
    """Image resource classification."""

    BACKGROUND = "Background"
    PHOTOGRAPHY = "Photography"
    ILLUSTRATION = "Illustration"
    DIAGRAM = "Diagram"
    DECORATIVE = "Decorative"


class ImageAcquireVia(str, Enum):
    """How the image was obtained."""

    AI = "ai"
    WEB = "web"
    USER = "user"
    PLACEHOLDER = "placeholder"


class ImageStatus(str, Enum):
    """Image resource processing status."""

    PENDING = "pending"
    GENERATED = "generated"
    SOURCED = "sourced"
    EXISTING = "existing"
    NEEDS_MANUAL = "needs_manual"
    PLACEHOLDER = "placeholder"


class QualityCheckStatus(str, Enum):
    """SVG page quality check status."""

    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


class ExportType(str, Enum):
    """PPT export type."""

    NATIVE = "native"
    SVG_PREVIEW = "svg_preview"


class PageRhythm(str, Enum):
    """SVG page rhythm type."""

    ANCHOR = "anchor"
    DENSE = "dense"
    BREATHING = "breathing"


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"


# ────────────────────────────────
# Shared Mixins
# ────────────────────────────────


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""

    created_at: datetime
    # updated_at excluded: SQLAlchemy func.now() as onupdate triggers
    # server-side refresh which fails in async greenlet context
    updated_at: datetime = Field(exclude=True)


class PaginatedResponse(BaseModel):
    """Pagination wrapper for list responses."""

    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int


# ────────────────────────────────
# Project Schemas
# ────────────────────────────────


class ProjectCreate(BaseModel):
    """Request schema for creating a new project."""

    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: Optional[str] = Field(default=None, max_length=2000, description="Project description")
    canvas_format: CanvasFormat = Field(default=CanvasFormat.PPT169, description="Canvas aspect ratio")
    llm_provider: LLMProvider = Field(default=LLMProvider.OPENAI, description="LLM provider")
    llm_model: str = Field(default="gpt-4o", description="LLM model name")


class ProjectUpdate(BaseModel):
    """Request schema for updating a project."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    canvas_format: Optional[CanvasFormat] = None
    llm_provider: Optional[LLMProvider] = None
    llm_model: Optional[str] = None
    template_path: Optional[str] = None


class ProjectResponse(TimestampMixin):
    """Response schema for project data."""

    model_config = ConfigDict(from_attributes=True, exclude={"project"})

    id: UUID
    name: str
    description: Optional[str] = None
    canvas_format: str
    status: ProjectStatus
    current_step: PipelineStep
    step_status: StepStatus
    llm_provider: str
    llm_model: str
    template_path: Optional[str] = None
    completed_at: Optional[datetime] = None


class ProjectListResponse(PaginatedResponse):
    """Paginated list of projects."""

    items: List[ProjectResponse]


class ProjectStartRequest(BaseModel):
    """Request schema for starting the pipeline."""

    start_from_step: Optional[PipelineStep] = Field(
        default=None, description="Step to start from (default: current step)"
    )


# ────────────────────────────────
# Source File Schemas
# ────────────────────────────────


class SourceFileUpload(BaseModel):
    """Request schema for uploading source files (metadata only)."""

    sort_order: int = Field(default=0, ge=0, description="Display order")


class SourceUrlAdd(BaseModel):
    """Request schema for adding a URL source."""

    url: str = Field(..., min_length=1, description="Source URL")
    title: Optional[str] = Field(default=None, description="Optional title for the URL source")
    sort_order: int = Field(default=0, ge=0)


class SourceFileResponse(TimestampMixin):
    """Response schema for source file data."""

    model_config = ConfigDict(from_attributes=True, exclude={"project"})

    id: UUID
    project_id: UUID
    original_filename: str
    file_type: FileType
    storage_key: str
    storage_backend: str
    file_size: int
    markdown_content: Optional[str] = None
    markdown_storage_key: Optional[str] = None
    conversion_status: ConversionStatus
    conversion_error: Optional[str] = None
    sort_order: int


class SourceFileListResponse(PaginatedResponse):
    """Paginated list of source files."""

    items: List[SourceFileResponse]


# ────────────────────────────────
# Design Spec Schemas
# ────────────────────────────────


class ColorScheme(BaseModel):
    """Color scheme for confirmations."""

    primary: Optional[str] = None
    secondary: Optional[str] = None
    accent: Optional[str] = None
    background: Optional[str] = None
    text: Optional[str] = None


class TypographySpec(BaseModel):
    """Typography configuration."""

    title_font: Optional[str] = None
    body_font: Optional[str] = None
    title_size: Optional[str] = None
    body_size: Optional[str] = None


class ConfirmationUpdate(BaseModel):
    """Request schema for updating Eight Confirmations."""

    confirmation_canvas: Optional[str] = None
    confirmation_page_count: Optional[int] = Field(default=None, ge=1, le=100)
    confirmation_audience: Optional[str] = None
    confirmation_style_mode: Optional[str] = None  # A/B/C
    confirmation_style_descriptor: Optional[str] = None
    confirmation_color_scheme: Optional[ColorScheme] = None
    confirmation_icon_approach: Optional[str] = None  # A/B/C/D
    confirmation_typography: Optional[TypographySpec] = None
    confirmation_image_approach: Optional[str] = None  # A/B/C/D/E


class ConfirmationsResponse(BaseModel):
    """Response schema for Eight Confirmations data."""

    model_config = ConfigDict(from_attributes=True, exclude={"project"})

    confirmation_canvas: Optional[str] = None
    confirmation_page_count: Optional[int] = None
    confirmation_audience: Optional[str] = None
    confirmation_style_mode: Optional[str] = None
    confirmation_style_descriptor: Optional[str] = None
    confirmation_color_scheme: Optional[Dict[str, Any]] = None
    confirmation_icon_approach: Optional[str] = None
    confirmation_typography: Optional[Dict[str, Any]] = None
    confirmation_image_approach: Optional[str] = None
    confirmation_status: ConfirmationStatus
    confirmed_at: Optional[datetime] = None


class DesignSpecResponse(TimestampMixin):
    """Response schema for Design Spec."""

    model_config = ConfigDict(from_attributes=True, exclude={"project"})

    id: UUID
    project_id: UUID
    spec_content: Optional[str] = None
    spec_storage_key: Optional[str] = None
    confirmation_status: ConfirmationStatus
    confirmed_at: Optional[datetime] = None
    confirmations: Optional[ConfirmationsResponse] = None


class DesignSpecUpdate(BaseModel):
    """Request schema for updating the full Design Spec (advanced)."""

    spec_content: Optional[str] = Field(default=None, description="Full design_spec.md content")


# ────────────────────────────────
# Pipeline Schemas
# ────────────────────────────────


class PipelineStatusResponse(BaseModel):
    """Response schema for current pipeline status."""

    model_config = ConfigDict(from_attributes=True, exclude={"project"})

    project_id: UUID
    project_status: ProjectStatus
    current_step: PipelineStep
    step_status: StepStatus
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    can_start: bool
    can_cancel: bool
    can_resume: bool
    next_action: Optional[str] = None


class JobResponse(TimestampMixin):
    """Response schema for pipeline job data."""

    model_config = ConfigDict(from_attributes=True, exclude={"project"})

    id: UUID
    project_id: UUID
    step: PipelineStep
    status: JobStatus
    celery_task_id: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class JobListResponse(PaginatedResponse):
    """Paginated list of pipeline jobs."""

    items: List[JobResponse]


class PipelineResumeRequest(BaseModel):
    """Request schema for resuming pipeline."""

    resume_from_step: Optional[PipelineStep] = None
    skip_confirmation: bool = Field(default=False, description="Skip confirmation step if waiting")


# ────────────────────────────────
# SVG Page Schemas
# ────────────────────────────────


class SVGPageResponse(TimestampMixin):
    """Response schema for SVG page data."""

    model_config = ConfigDict(from_attributes=True, exclude={"project"})

    id: UUID
    project_id: UUID
    page_number: int
    page_name: str
    filename: str
    svg_content: Optional[str] = None
    svg_storage_key: Optional[str] = None
    page_rhythm: Optional[str] = None
    page_layout: Optional[str] = None
    page_chart: Optional[str] = None
    quality_check_status: QualityCheckStatus
    quality_check_errors: Optional[List[str]] = None
    quality_check_warnings: Optional[List[str]] = None


class SVGPageUpdate(BaseModel):
    """Request schema for updating SVG page content."""

    svg_content: str = Field(..., description="SVG XML content")
    page_name: Optional[str] = None
    page_rhythm: Optional[str] = None
    page_layout: Optional[str] = None
    page_chart: Optional[str] = None


class SVGPageListResponse(PaginatedResponse):
    """Paginated list of SVG pages."""

    items: List[SVGPageResponse]


# ────────────────────────────────
# PPTX Export Schemas
# ────────────────────────────────


class PPTXExportResponse(TimestampMixin):
    """Response schema for PPTX export data."""

    model_config = ConfigDict(from_attributes=True, exclude={"project"})

    id: UUID
    project_id: UUID
    export_type: ExportType
    filename: str
    storage_key: str
    storage_backend: str
    file_size: Optional[int] = None
    transition_effect: Optional[str] = None
    animation_effect: Optional[str] = None
    download_url: Optional[str] = None


class PPTXExportListResponse(PaginatedResponse):
    """Paginated list of PPTX exports."""

    items: List[PPTXExportResponse]


class PPTXExportCreate(BaseModel):
    """Request schema for creating a new export."""

    export_type: ExportType = Field(default=ExportType.NATIVE)
    transition_effect: Optional[str] = None
    animation_effect: Optional[str] = None


# ────────────────────────────────
# Image Resource Schemas
# ────────────────────────────────


class ImageResourceResponse(TimestampMixin):
    """Response schema for image resource data."""

    model_config = ConfigDict(from_attributes=True, exclude={"project"})

    id: UUID
    project_id: UUID
    filename: str
    dimensions: Optional[str] = None
    ratio: Optional[float] = None
    purpose: Optional[str] = None
    image_type: Optional[ImageType] = None
    acquire_via: ImageAcquireVia
    status: ImageStatus
    generation_prompt: Optional[str] = None
    generation_backend: Optional[str] = None
    search_query: Optional[str] = None
    source_url: Optional[str] = None
    attribution_text: Optional[str] = None
    license_tier: Optional[str] = None
    storage_key: Optional[str] = None
    storage_backend: str
    original_storage_key: Optional[str] = None
    preview_url: Optional[str] = None


class ImageResourceUpdate(BaseModel):
    """Request schema for updating image resource configuration."""

    purpose: Optional[str] = None
    image_type: Optional[ImageType] = None
    generation_prompt: Optional[str] = None
    search_query: Optional[str] = None
    status: Optional[ImageStatus] = None


class ImageResourceListResponse(PaginatedResponse):
    """Paginated list of image resources."""

    items: List[ImageResourceResponse]


# ────────────────────────────────
# WebSocket Message Schemas
# ────────────────────────────────


class WSMessageType(str, Enum):
    """WebSocket message types."""

    STATUS_UPDATE = "status_update"
    JOB_UPDATE = "job_update"
    STEP_CHANGE = "step_change"
    ERROR = "error"
    CONFIRMATION_NEEDED = "confirmation_needed"
    PING = "ping"
    PONG = "pong"


class WebSocketMessage(BaseModel):
    """Base WebSocket message schema."""

    type: WSMessageType
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    project_id: Optional[str] = None


class StatusUpdateData(BaseModel):
    """Data payload for status_update messages."""

    project_status: ProjectStatus
    current_step: PipelineStep
    step_status: StepStatus
    message: Optional[str] = None


class JobUpdateData(BaseModel):
    """Data payload for job_update messages."""

    job_id: str
    step: PipelineStep
    status: JobStatus
    error_message: Optional[str] = None


class StepChangeData(BaseModel):
    """Data payload for step_change messages."""

    previous_step: PipelineStep
    current_step: PipelineStep
    step_status: StepStatus


class ConfirmationNeededData(BaseModel):
    """Data payload for confirmation_needed messages."""

    confirmation_type: str = "eight_confirmations"
    confirmations: Optional[Dict[str, Any]] = None
    message: str = "Please review and confirm the Eight Confirmations."


# ────────────────────────────────
# Error & Health Schemas
# ────────────────────────────────


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    error_code: Optional[str] = None
    field_errors: Optional[Dict[str, str]] = None


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str = "0.1.0"
    services: Dict[str, str] = {}

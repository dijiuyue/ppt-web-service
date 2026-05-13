"""
PPT Master Pipeline - State definitions and validation.

Defines the PPTPipelineState TypedDict, status enumerations,
state transition rules, and validation utilities used by the
LangGraph workflow.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, TypedDict

from app.pipeline.constants import CANVAS_FORMATS, PIPELINE_STEPS


# ---------------------------------------------------------------------------
# Status enumerations
# ---------------------------------------------------------------------------
class ProjectStatus(str, Enum):
    """Overall project lifecycle status."""

    DRAFT = "draft"
    CONFIRMING = "confirming"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineStep(str, Enum):
    """Individual pipeline step names."""

    INIT = "init"
    SOURCE_PROCESSING = "source_processing"
    STRATEGIST = "strategist"
    IMAGE_ACQUISITION = "image_acquisition"
    EXECUTOR = "executor"
    POST_PROCESSING = "post_processing"
    COMPLETED = "completed"


class StepStatus(str, Enum):
    """Execution status of a pipeline step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_CONFIRMATION = "waiting_confirmation"


class JobStatus(str, Enum):
    """Celery pipeline job status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_CONFIRMATION = "waiting_confirmation"
    CANCELLED = "cancelled"


class ConfirmationStatus(str, Enum):
    """Eight Confirmations user-review status."""

    PENDING = "pending"
    CONFIRMED = "confirmed"


class ImageAcquireVia(str, Enum):
    """How an image resource was (or will be) obtained."""

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


# ---------------------------------------------------------------------------
# TypedDict state
# ---------------------------------------------------------------------------
class PPTPipelineState(TypedDict, total=False):
    """
    LangGraph pipeline state.

    All keys are optional (total=False) so that individual nodes
    can return dicts containing only the keys they mutate.
    """

    # Core identifiers
    project_id: str

    # Current position in the pipeline
    current_step: str
    step_status: str

    # Source content (markdown) for strategist / executor
    source_content: str | None

    # Design spec (raw markdown)
    design_spec: str | None
    design_spec_storage_key: str | None

    # Spec lock (raw markdown)
    spec_lock: str | None
    spec_lock_storage_key: str | None

    # Eight confirmations (structured dict)
    confirmations: dict[str, Any] | None

    # Confirmation workflow status
    confirmation_status: str

    # Image resources
    image_resources: list[dict[str, Any]] | None

    # SVG pages produced by executor
    svg_pages: list[dict[str, Any]] | None

    # Speaker notes
    speaker_notes: list[dict[str, Any]] | None

    # Exported PPTX
    exports: list[dict[str, Any]] | None

    # Accumulated errors
    errors: list[str]

    # Retry counter for the current step
    retry_count: int

    # Whether the pipeline should pause after strategist
    needs_confirmation: bool

    # Whether image acquisition can be skipped
    skip_images: bool

    # Workspace path (populated by workspace context manager)
    workspace_path: str | None

    # LLM configuration
    llm_provider: str
    llm_model: str

    # Canvas format
    canvas_format: str

    # Optional user notes / instructions
    user_instructions: str | None

    # WebSocket connection ID for notifications
    ws_client_id: str | None


# ---------------------------------------------------------------------------
# State transition graph
# ---------------------------------------------------------------------------
STEP_TRANSITIONS: dict[str, list[str]] = {
    "init": ["source_processing"],
    "source_processing": ["strategist"],
    "strategist": ["image_acquisition"],
    "image_acquisition": ["executor"],
    "executor": ["post_processing"],
    "post_processing": ["completed"],
    "completed": [],
}


def get_next_step(current_step: str) -> str | None:
    """Return the next sequential step, or None if completed."""
    transitions = STEP_TRANSITIONS.get(current_step, [])
    return transitions[0] if transitions else None


def get_allowed_next_steps(current_step: str) -> list[str]:
    """Return all allowed next steps (for conditional edges)."""
    return STEP_TRANSITIONS.get(current_step, [])


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_state(state: dict[str, Any]) -> list[str]:
    """
    Validate a pipeline state dict and return a list of error strings.

    An empty list means the state is valid.
    """
    errors: list[str] = []

    if not state.get("project_id"):
        errors.append("Missing required field: project_id")

    current_step = state.get("current_step", "init")
    if current_step not in PIPELINE_STEPS:
        errors.append(f"Invalid current_step: {current_step}")

    step_status = state.get("step_status", StepStatus.PENDING)
    valid_statuses = {s.value for s in StepStatus}
    if step_status not in valid_statuses:
        errors.append(f"Invalid step_status: {step_status}")

    canvas_format = state.get("canvas_format", "ppt169")
    if canvas_format not in CANVAS_FORMATS:
        errors.append(f"Invalid canvas_format: {canvas_format}")

    confirmation_status = state.get("confirmation_status", ConfirmationStatus.PENDING)
    valid_conf = {s.value for s in ConfirmationStatus}
    if confirmation_status not in valid_conf:
        errors.append(f"Invalid confirmation_status: {confirmation_status}")

    llm_provider = state.get("llm_provider", "openai")
    if llm_provider not in ("openai", "anthropic"):
        errors.append(f"Invalid llm_provider: {llm_provider}")

    return errors


def is_state_valid(state: dict[str, Any]) -> bool:
    """Return True if the state dict passes validation."""
    return len(validate_state(state)) == 0


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------
def create_initial_state(
    project_id: str,
    llm_provider: str = "openai",
    llm_model: str = "gpt-4o",
    canvas_format: str = "ppt169",
    user_instructions: str | None = None,
    ws_client_id: str | None = None,
) -> PPTPipelineState:
    """Create a fresh pipeline state for a new project."""
    return PPTPipelineState(
        project_id=project_id,
        current_step=PipelineStep.SOURCE_PROCESSING.value,
        step_status=StepStatus.PENDING.value,
        source_content=None,
        design_spec=None,
        design_spec_storage_key=None,
        spec_lock=None,
        spec_lock_storage_key=None,
        confirmations=None,
        confirmation_status=ConfirmationStatus.PENDING.value,
        image_resources=None,
        svg_pages=None,
        speaker_notes=None,
        exports=None,
        errors=[],
        retry_count=0,
        needs_confirmation=True,
        skip_images=False,
        workspace_path=None,
        llm_provider=llm_provider,
        llm_model=llm_model,
        canvas_format=canvas_format,
        user_instructions=user_instructions,
        ws_client_id=ws_client_id,
    )


def update_state(
    state: PPTPipelineState,
    **kwargs: Any,
) -> PPTPipelineState:
    """Return a new state dict with merged updates."""
    new_state = dict(state)
    new_state.update(kwargs)
    return PPTPipelineState(**new_state)


def add_error(state: PPTPipelineState, error: str) -> PPTPipelineState:
    """Append an error message to the state's error list."""
    errors = list(state.get("errors", []))
    errors.append(error)
    return update_state(state, errors=errors)


def reset_retry(state: PPTPipelineState) -> PPTPipelineState:
    """Reset the retry counter to zero."""
    return update_state(state, retry_count=0)


def increment_retry(state: PPTPipelineState) -> PPTPipelineState:
    """Increment the retry counter by one."""
    current = state.get("retry_count", 0)
    return update_state(state, retry_count=current + 1)

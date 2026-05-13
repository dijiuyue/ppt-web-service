"""
PPT Master Pipeline package.

Provides the complete LangGraph-based pipeline for PPT generation,
including state management, LLM integration, script wrappers, and
temporary workspace management.
"""

from app.pipeline.constants import (
    ANTHROPIC_MODELS,
    CANVAS_FORMATS,
    DEFAULT_CANVAS_FORMAT,
    OPENAI_MODELS,
    PIPELINE_STEPS,
)
from app.pipeline.graph import PPTMasterPipeline, get_pipeline
from app.pipeline.llm import (
    LLMClient,
    LLMContentError,
    LLMError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.pipeline.nodes import (
    executor_node,
    image_acquisition_node,
    post_processing_node,
    source_processing_node,
    strategist_node,
    wait_confirmation_node,
)
from app.pipeline.script_runner import ScriptRunner, ScriptRunnerError
from app.pipeline.state import (
    ConfirmationStatus,
    ImageAcquireVia,
    ImageStatus,
    JobStatus,
    PipelineStep,
    PPTPipelineState,
    ProjectStatus,
    StepStatus,
    add_error,
    create_initial_state,
    get_allowed_next_steps,
    get_next_step,
    is_state_valid,
    update_state,
    validate_state,
)
from app.pipeline.workspace import ProjectWorkspace, WorkspaceError

__all__ = [
    # Pipeline
    "PPTMasterPipeline",
    "get_pipeline",
    # State
    "PPTPipelineState",
    "ProjectStatus",
    "PipelineStep",
    "StepStatus",
    "JobStatus",
    "ConfirmationStatus",
    "ImageAcquireVia",
    "ImageStatus",
    "create_initial_state",
    "update_state",
    "add_error",
    "validate_state",
    "is_state_valid",
    "get_next_step",
    "get_allowed_next_steps",
    # Nodes
    "source_processing_node",
    "strategist_node",
    "wait_confirmation_node",
    "image_acquisition_node",
    "executor_node",
    "post_processing_node",
    # LLM
    "LLMClient",
    "LLMError",
    "LLMProviderError",
    "LLMRateLimitError",
    "LLMTimeoutError",
    "LLMContentError",
    # Script Runner
    "ScriptRunner",
    "ScriptRunnerError",
    # Workspace
    "ProjectWorkspace",
    "WorkspaceError",
    # Constants
    "CANVAS_FORMATS",
    "DEFAULT_CANVAS_FORMAT",
    "OPENAI_MODELS",
    "ANTHROPIC_MODELS",
    "PIPELINE_STEPS",
]

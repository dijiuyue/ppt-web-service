"""
PPT Master Web Service — Pipeline State Tests.

Tests for PPTPipelineState creation, state transition rules,
validation, and helper functions.
"""

from __future__ import annotations

import pytest

from app.pipeline.constants import CANVAS_FORMATS, PIPELINE_STEPS
from app.pipeline.state import (
    STEP_TRANSITIONS,
    ConfirmationStatus,
    JobStatus,
    PipelineStep,
    PPTPipelineState,
    ProjectStatus,
    StepStatus,
    add_error,
    create_initial_state,
    get_allowed_next_steps,
    get_next_step,
    increment_retry,
    is_state_valid,
    reset_retry,
    update_state,
    validate_state,
)


# ---------------------------------------------------------------------------
# PPTPipelineState Creation Tests
# ---------------------------------------------------------------------------


class TestPPTPipelineStateCreation:
    """Tests for creating PPTPipelineState instances."""

    def test_create_minimal_state(self) -> None:
        """Test creating a minimal pipeline state."""
        state = PPTPipelineState(
            project_id="test-project-123",
            current_step="init",
            step_status="pending",
        )
        assert state["project_id"] == "test-project-123"
        assert state["current_step"] == "init"
        assert state["step_status"] == "pending"

    def test_create_full_state(self) -> None:
        """Test creating a full pipeline state with all fields."""
        state = PPTPipelineState(
            project_id="test-project-456",
            current_step=PipelineStep.SOURCE_PROCESSING.value,
            step_status=StepStatus.RUNNING.value,
            source_content="# Source\n\nContent",
            design_spec="# Design\n\nSpec",
            design_spec_storage_key="projects/456/design_spec.md",
            spec_lock=None,
            spec_lock_storage_key=None,
            confirmations={"canvas": "ppt169", "page_count": 10},
            confirmation_status=ConfirmationStatus.PENDING.value,
            image_resources=[{"id": "img-1", "status": "pending"}],
            svg_pages=None,
            speaker_notes=None,
            exports=None,
            errors=[],
            retry_count=0,
            needs_confirmation=True,
            skip_images=False,
            workspace_path="/tmp/workspace",
            llm_provider="openai",
            llm_model="gpt-4o",
            canvas_format="ppt169",
            user_instructions="Make it amazing",
            ws_client_id="ws-client-1",
        )
        assert state["project_id"] == "test-project-456"
        assert state["llm_provider"] == "openai"
        assert state["canvas_format"] == "ppt169"
        assert state["user_instructions"] == "Make it amazing"
        assert state["needs_confirmation"] is True
        assert state["skip_images"] is False
        assert len(state["errors"]) == 0

    def test_state_partial_fields(self) -> None:
        """Test that partial state creation works (total=False)."""
        state = PPTPipelineState(project_id="partial-test")
        # Only project_id is set; other fields are optional
        assert state["project_id"] == "partial-test"
        assert "current_step" not in state

    def test_state_is_typed_dict(self) -> None:
        """Test that PPTPipelineState is a TypedDict."""
        from typing import get_type_hints

        hints = get_type_hints(PPTPipelineState)
        assert "project_id" in hints
        assert "current_step" in hints
        assert "errors" in hints


# ---------------------------------------------------------------------------
# State Transition Tests
# ---------------------------------------------------------------------------


class TestStateTransitions:
    """Tests for pipeline step transition rules."""

    def test_step_transitions_completeness(self) -> None:
        """Test that all pipeline steps have transition entries."""
        for step in PIPELINE_STEPS:
            assert step in STEP_TRANSITIONS, f"Missing transition for step: {step}"

    def test_init_transitions(self) -> None:
        """Test transitions from init step."""
        next_steps = STEP_TRANSITIONS["init"]
        assert next_steps == ["source_processing"]

    def test_source_processing_transitions(self) -> None:
        """Test transitions from source_processing step."""
        next_steps = STEP_TRANSITIONS["source_processing"]
        assert next_steps == ["strategist"]

    def test_strategist_transitions(self) -> None:
        """Test transitions from strategist step."""
        next_steps = STEP_TRANSITIONS["strategist"]
        assert next_steps == ["image_acquisition"]

    def test_image_acquisition_transitions(self) -> None:
        """Test transitions from image_acquisition step."""
        next_steps = STEP_TRANSITIONS["image_acquisition"]
        assert next_steps == ["executor"]

    def test_executor_transitions(self) -> None:
        """Test transitions from executor step."""
        next_steps = STEP_TRANSITIONS["executor"]
        assert next_steps == ["post_processing"]

    def test_post_processing_transitions(self) -> None:
        """Test transitions from post_processing step."""
        next_steps = STEP_TRANSITIONS["post_processing"]
        assert next_steps == ["completed"]

    def test_completed_transitions(self) -> None:
        """Test transitions from completed step (no transitions)."""
        next_steps = STEP_TRANSITIONS["completed"]
        assert next_steps == []

    def test_get_next_step_normal(self) -> None:
        """Test get_next_step for normal transitions."""
        assert get_next_step("init") == "source_processing"
        assert get_next_step("source_processing") == "strategist"
        assert get_next_step("strategist") == "image_acquisition"
        assert get_next_step("image_acquisition") == "executor"
        assert get_next_step("executor") == "post_processing"
        assert get_next_step("post_processing") == "completed"

    def test_get_next_step_completed(self) -> None:
        """Test get_next_step returns None for completed."""
        assert get_next_step("completed") is None

    def test_get_next_step_unknown(self) -> None:
        """Test get_next_step returns None for unknown step."""
        assert get_next_step("nonexistent_step") is None

    def test_get_allowed_next_steps(self) -> None:
        """Test get_allowed_next_steps returns correct list."""
        assert get_allowed_next_steps("init") == ["source_processing"]
        assert get_allowed_next_steps("completed") == []
        assert get_allowed_next_steps("nonexistent") == []


# ---------------------------------------------------------------------------
# State Validation Tests
# ---------------------------------------------------------------------------


class TestStateValidation:
    """Tests for state validation functions."""

    def test_validate_valid_state(self) -> None:
        """Test validation of a fully valid state."""
        state = {
            "project_id": "test-123",
            "current_step": "init",
            "step_status": "pending",
            "canvas_format": "ppt169",
            "confirmation_status": "pending",
            "llm_provider": "openai",
        }
        errors = validate_state(state)
        assert errors == []
        assert is_state_valid(state) is True

    def test_validate_missing_project_id(self) -> None:
        """Test validation catches missing project_id."""
        state = {
            "current_step": "init",
        }
        errors = validate_state(state)
        assert any("project_id" in e for e in errors)
        assert is_state_valid(state) is False

    def test_validate_invalid_current_step(self) -> None:
        """Test validation catches invalid current_step."""
        state = {
            "project_id": "test-123",
            "current_step": "invalid_step",
        }
        errors = validate_state(state)
        assert any("current_step" in e for e in errors)

    def test_validate_invalid_step_status(self) -> None:
        """Test validation catches invalid step_status."""
        state = {
            "project_id": "test-123",
            "step_status": "invalid_status",
        }
        errors = validate_state(state)
        assert any("step_status" in e for e in errors)

    def test_validate_invalid_canvas_format(self) -> None:
        """Test validation catches invalid canvas_format."""
        state = {
            "project_id": "test-123",
            "canvas_format": "invalid_format",
        }
        errors = validate_state(state)
        assert any("canvas_format" in e for e in errors)

    def test_validate_invalid_confirmation_status(self) -> None:
        """Test validation catches invalid confirmation_status."""
        state = {
            "project_id": "test-123",
            "confirmation_status": "invalid_status",
        }
        errors = validate_state(state)
        assert any("confirmation_status" in e for e in errors)

    def test_validate_invalid_llm_provider(self) -> None:
        """Test validation catches invalid llm_provider."""
        state = {
            "project_id": "test-123",
            "llm_provider": "google",
        }
        errors = validate_state(state)
        assert any("llm_provider" in e for e in errors)

    def test_validate_multiple_errors(self) -> None:
        """Test validation collects multiple errors."""
        state = {
            "current_step": "bad_step",
            "step_status": "bad_status",
            "canvas_format": "bad_format",
            "llm_provider": "bad_provider",
        }
        errors = validate_state(state)
        assert len(errors) >= 4  # missing project_id + 4 invalid fields

    def test_is_state_valid_with_empty_dict(self) -> None:
        """Test is_state_valid with completely empty state."""
        assert is_state_valid({}) is False

    def test_validate_with_defaults(self) -> None:
        """Test validation with minimal state uses defaults."""
        state = {"project_id": "test-123"}
        errors = validate_state(state)
        # Should be valid since defaults are applied
        assert errors == []
        assert is_state_valid(state) is True


# ---------------------------------------------------------------------------
# create_initial_state Tests
# ---------------------------------------------------------------------------


class TestCreateInitialState:
    """Tests for create_initial_state helper."""

    def test_create_initial_state_defaults(self) -> None:
        """Test create_initial_state with defaults."""
        state = create_initial_state("proj-123")
        assert state["project_id"] == "proj-123"
        assert state["current_step"] == PipelineStep.SOURCE_PROCESSING.value
        assert state["step_status"] == StepStatus.PENDING.value
        assert state["llm_provider"] == "openai"
        assert state["llm_model"] == "gpt-4o"
        assert state["canvas_format"] == "ppt169"
        assert state["confirmation_status"] == ConfirmationStatus.PENDING.value
        assert state["errors"] == []
        assert state["retry_count"] == 0
        assert state["needs_confirmation"] is True
        assert state["skip_images"] is False
        assert state["source_content"] is None
        assert state["design_spec"] is None

    def test_create_initial_state_custom(self) -> None:
        """Test create_initial_state with custom values."""
        state = create_initial_state(
            project_id="proj-456",
            llm_provider="anthropic",
            llm_model="claude-3-5-sonnet-latest",
            canvas_format="ppt43",
            user_instructions="Focus on data visualization",
            ws_client_id="ws-789",
        )
        assert state["project_id"] == "proj-456"
        assert state["llm_provider"] == "anthropic"
        assert state["llm_model"] == "claude-3-5-sonnet-latest"
        assert state["canvas_format"] == "ppt43"
        assert state["user_instructions"] == "Focus on data visualization"
        assert state["ws_client_id"] == "ws-789"

    def test_create_initial_state_returns_valid_state(self) -> None:
        """Test that created initial state passes validation."""
        state = create_initial_state("proj-test")
        assert is_state_valid(state) is True


# ---------------------------------------------------------------------------
# update_state Tests
# ---------------------------------------------------------------------------


class TestUpdateState:
    """Tests for update_state helper."""

    def test_update_state_single_field(self) -> None:
        """Test updating a single field."""
        state = create_initial_state("proj-1")
        new_state = update_state(state, current_step="strategist")
        assert new_state["current_step"] == "strategist"
        # Other fields unchanged
        assert new_state["project_id"] == "proj-1"
        assert new_state["llm_provider"] == "openai"

    def test_update_state_multiple_fields(self) -> None:
        """Test updating multiple fields."""
        state = create_initial_state("proj-1")
        new_state = update_state(
            state,
            current_step="executor",
            step_status="running",
            retry_count=2,
        )
        assert new_state["current_step"] == "executor"
        assert new_state["step_status"] == "running"
        assert new_state["retry_count"] == 2

    def test_update_state_returns_new_instance(self) -> None:
        """Test update_state returns a new instance."""
        state = create_initial_state("proj-1")
        new_state = update_state(state, current_step="strategist")
        assert new_state is not state

    def test_update_state_preserves_unset_fields(self) -> None:
        """Test update_state preserves fields not being updated."""
        state = create_initial_state("proj-1")
        original_model = state["llm_model"]
        new_state = update_state(state, current_step="executor")
        assert new_state["llm_model"] == original_model


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------


class TestAddError:
    """Tests for add_error helper."""

    def test_add_error_to_empty(self) -> None:
        """Test adding error to empty error list."""
        state = create_initial_state("proj-1")
        new_state = add_error(state, "First error")
        assert new_state["errors"] == ["First error"]

    def test_add_error_appends(self) -> None:
        """Test adding error appends to existing list."""
        state = create_initial_state("proj-1")
        state = add_error(state, "First error")
        state = add_error(state, "Second error")
        assert state["errors"] == ["First error", "Second error"]

    def test_add_error_returns_new_instance(self) -> None:
        """Test add_error returns a new instance."""
        state = create_initial_state("proj-1")
        new_state = add_error(state, "Error")
        assert new_state is not state


class TestResetRetry:
    """Tests for reset_retry helper."""

    def test_reset_retry(self) -> None:
        """Test reset_retry sets counter to 0."""
        state = create_initial_state("proj-1")
        state = increment_retry(state)  # retry_count = 1
        state = increment_retry(state)  # retry_count = 2
        assert state["retry_count"] == 2
        state = reset_retry(state)
        assert state["retry_count"] == 0


class TestIncrementRetry:
    """Tests for increment_retry helper."""

    def test_increment_retry_from_zero(self) -> None:
        """Test increment_retry from 0."""
        state = create_initial_state("proj-1")
        assert state["retry_count"] == 0
        state = increment_retry(state)
        assert state["retry_count"] == 1

    def test_increment_retry_multiple(self) -> None:
        """Test increment_retry multiple times."""
        state = create_initial_state("proj-1")
        for i in range(5):
            state = increment_retry(state)
        assert state["retry_count"] == 5

    def test_increment_retry_returns_new_instance(self) -> None:
        """Test increment_retry returns a new instance."""
        state = create_initial_state("proj-1")
        new_state = increment_retry(state)
        assert new_state is not state


# ---------------------------------------------------------------------------
# Enum Tests
# ---------------------------------------------------------------------------


class TestPipelineEnums:
    """Tests for pipeline state enums."""

    def test_project_status_values(self) -> None:
        """Test ProjectStatus enum values."""
        assert ProjectStatus.DRAFT == "draft"
        assert ProjectStatus.CONFIRMING == "confirming"
        assert ProjectStatus.PROCESSING == "processing"
        assert ProjectStatus.COMPLETED == "completed"
        assert ProjectStatus.FAILED == "failed"

    def test_pipeline_step_values(self) -> None:
        """Test PipelineStep enum values."""
        assert PipelineStep.INIT == "init"
        assert PipelineStep.SOURCE_PROCESSING == "source_processing"
        assert PipelineStep.STRATEGIST == "strategist"
        assert PipelineStep.IMAGE_ACQUISITION == "image_acquisition"
        assert PipelineStep.EXECUTOR == "executor"
        assert PipelineStep.POST_PROCESSING == "post_processing"
        assert PipelineStep.COMPLETED == "completed"

    def test_step_status_values(self) -> None:
        """Test StepStatus enum values."""
        assert StepStatus.PENDING == "pending"
        assert StepStatus.RUNNING == "running"
        assert StepStatus.COMPLETED == "completed"
        assert StepStatus.FAILED == "failed"
        assert StepStatus.WAITING_CONFIRMATION == "waiting_confirmation"

    def test_job_status_values(self) -> None:
        """Test JobStatus enum values."""
        assert JobStatus.PENDING == "pending"
        assert JobStatus.RUNNING == "running"
        assert JobStatus.COMPLETED == "completed"
        assert JobStatus.FAILED == "failed"
        assert JobStatus.WAITING_CONFIRMATION == "waiting_confirmation"
        assert JobStatus.CANCELLED == "cancelled"

    def test_confirmation_status_values(self) -> None:
        """Test ConfirmationStatus enum values."""
        assert ConfirmationStatus.PENDING == "pending"
        assert ConfirmationStatus.CONFIRMED == "confirmed"


# ---------------------------------------------------------------------------
# Constants Tests
# ---------------------------------------------------------------------------


class TestPipelineConstants:
    """Tests for pipeline constants."""

    def test_pipeline_steps_list(self) -> None:
        """Test PIPELINE_STEPS contains all steps in order."""
        expected = [
            "init",
            "source_processing",
            "strategist",
            "image_acquisition",
            "executor",
            "post_processing",
            "completed",
        ]
        assert PIPELINE_STEPS == expected

    def test_canvas_formats_keys(self) -> None:
        """Test CANVAS_FORMATS has all expected keys."""
        assert "ppt169" in CANVAS_FORMATS
        assert "ppt43" in CANVAS_FORMATS
        assert "xhs" in CANVAS_FORMATS
        assert "story" in CANVAS_FORMATS

    def test_canvas_formats_structure(self) -> None:
        """Test CANVAS_FORMATS has correct structure."""
        for key, value in CANVAS_FORMATS.items():
            assert "viewbox" in value
            assert "width" in value
            assert "height" in value

    def test_ppt169_dimensions(self) -> None:
        """Test ppt169 canvas dimensions."""
        fmt = CANVAS_FORMATS["ppt169"]
        assert fmt["width"] == 1280
        assert fmt["height"] == 720
        assert fmt["viewbox"] == "0 0 1280 720"

    def test_ppt43_dimensions(self) -> None:
        """Test ppt43 canvas dimensions."""
        fmt = CANVAS_FORMATS["ppt43"]
        assert fmt["width"] == 960
        assert fmt["height"] == 720

    def test_xhs_dimensions(self) -> None:
        """Test xhs canvas dimensions."""
        fmt = CANVAS_FORMATS["xhs"]
        assert fmt["width"] == 900
        assert fmt["height"] == 1200

    def test_story_dimensions(self) -> None:
        """Test story canvas dimensions."""
        fmt = CANVAS_FORMATS["story"]
        assert fmt["width"] == 1080
        assert fmt["height"] == 1920

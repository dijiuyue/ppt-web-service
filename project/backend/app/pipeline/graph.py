"""
PPT Master Pipeline - LangGraph workflow builder.

Defines the PPTMasterPipeline class which constructs a LangGraph
StateGraph from the node functions and conditional edges, then compiles
it into an executable workflow.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from langgraph.graph import END, StateGraph

from app.pipeline.nodes import (
    executor_node,
    image_acquisition_node,
    post_processing_node,
    source_processing_node,
    strategist_node,
    wait_confirmation_node,
)
from app.pipeline.state import (
    ConfirmationStatus,
    PPTPipelineState,
    StepStatus,
    create_initial_state,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Conditional edge functions
# ---------------------------------------------------------------------------

def _check_confirmation(state: PPTPipelineState) -> Literal["confirmed", "waiting"]:
    """
    Conditional edge after wait_confirmation node.

    Returns:
        - ``"confirmed"`` if the user has confirmed Eight Confirmations.
        - ``"waiting"`` to stay at the confirmation checkpoint.
    """
    status = state.get("confirmation_status", ConfirmationStatus.PENDING.value)
    needs = state.get("needs_confirmation", True)

    if status == ConfirmationStatus.CONFIRMED.value and not needs:
        logger.info(
            "[check_confirmation] Confirmed → proceed to image_acquisition"
        )
        return "confirmed"

    logger.info("[check_confirmation] Still waiting for user confirmation")
    return "waiting"


def _check_images(state: PPTPipelineState) -> Literal["needed", "skip"]:
    """
    Conditional edge after image_acquisition node (or skip).

    Returns:
        - ``"needed"`` if images were acquired normally.
        - ``"skip"`` if no images are required (image_approach == "E").
    """
    skip = state.get("skip_images", False)
    if skip:
        logger.info("[check_images] No images needed → skip to executor")
        return "skip"
    return "needed"


def _check_executor(state: PPTPipelineState) -> Literal["proceed", "retry", "fail"]:
    """
    Conditional edge after executor node.

    Returns:
        - ``"proceed"`` if executor completed successfully.
        - ``"retry"`` if we should retry (and retry_count < max).
        - ``"fail"`` if max retries exceeded.
    """
    step_status = state.get("step_status", "")
    errors = state.get("errors", [])
    retry_count = state.get("retry_count", 0)
    max_retries = 2  # Allow up to 3 total attempts

    if step_status == StepStatus.COMPLETED.value:
        return "proceed"

    if retry_count < max_retries and errors:
        logger.info(
            "[check_executor] Retry attempt %d/%d", retry_count + 1, max_retries + 1
        )
        return "retry"

    logger.error("[check_executor] Max retries exceeded, failing")
    return "fail"


def _route_after_source_processing(
    state: PPTPipelineState,
) -> Literal["strategist", "fail"]:
    """Route after source_processing based on success/failure."""
    if state.get("step_status") == StepStatus.COMPLETED.value:
        return "strategist"
    return "fail"


def _route_failure(state: PPTPipelineState) -> Literal["end"]:
    """Terminal node for failure paths."""
    logger.error(
        "[route_failure] Pipeline failed for project %s with errors: %s",
        state.get("project_id"),
        state.get("errors", []),
    )
    return "end"


# ---------------------------------------------------------------------------
# Pipeline class
# ---------------------------------------------------------------------------

class PPTMasterPipeline:
    """
    LangGraph-driven PPT generation pipeline.

    Builds a ``StateGraph`` from the node functions defined in
    ``nodes.py`` and compiles it into an executable workflow.

    Usage::

        pipeline = PPTMasterPipeline()
        workflow = pipeline.compile()

        # Run asynchronously
        result = await workflow.ainvoke(initial_state)

        # Or stream events
        async for event in workflow.astream(initial_state):
            print(event)
    """

    def __init__(self) -> None:
        self._workflow: StateGraph | None = None
        self._compiled = None

    # -- Workflow construction ----------------------------------------------

    def build_workflow(self) -> StateGraph:
        """
        Construct the StateGraph with all nodes and edges.

        The graph layout::

            source_processing → strategist → wait_confirmation
                                                       ↓
                                 [confirmed] → image_acquisition → executor
                                 [waiting]  → END
                                                       ↓
                                              post_processing → END
        """
        builder = StateGraph(PPTPipelineState)

        # -- Nodes ---------------------------------------------------------
        builder.add_node("source_processing", source_processing_node)
        builder.add_node("strategist", strategist_node)
        builder.add_node("wait_confirmation", wait_confirmation_node)
        builder.add_node("image_acquisition", image_acquisition_node)
        builder.add_node("executor", executor_node)
        builder.add_node("post_processing", post_processing_node)
        builder.add_node("_fail", self._fail_node)

        # -- Entry point ---------------------------------------------------
        builder.set_entry_point("source_processing")

        # -- Edges ---------------------------------------------------------

        # source_processing → strategist (or fail)
        builder.add_conditional_edges(
            "source_processing",
            _route_after_source_processing,
            {
                "strategist": "strategist",
                "fail": "_fail",
            },
        )

        # strategist → wait_confirmation
        builder.add_edge("strategist", "wait_confirmation")

        # wait_confirmation → image_acquisition (if confirmed) or END (if waiting)
        builder.add_conditional_edges(
            "wait_confirmation",
            _check_confirmation,
            {
                "confirmed": "image_acquisition",
                "waiting": END,
            },
        )

        # image_acquisition → executor (both "needed" and "skip" go to executor)
        builder.add_conditional_edges(
            "image_acquisition",
            _check_images,
            {
                "needed": "executor",
                "skip": "executor",
            },
        )

        # executor → post_processing (or retry/fail)
        builder.add_edge("executor", "post_processing")

        # post_processing → END
        builder.add_edge("post_processing", END)

        # _fail → END
        builder.add_edge("_fail", END)

        self._workflow = builder
        return builder

    async def _fail_node(self, state: PPTPipelineState) -> dict[str, Any]:
        """Terminal failure node — sets final failed state."""
        project_id = state.get("project_id", "unknown")
        errors = state.get("errors", [])
        logger.error("Pipeline failed for project %s: %s", project_id, errors)

        # Update DB status
        try:
            from app.pipeline.nodes import _update_project_status
            await _update_project_status(
                project_id,
                step="failed",
                step_status=StepStatus.FAILED.value,
                error="; ".join(errors[-3:]) if errors else "Unknown error",
            )
        except Exception as exc:
            logger.error("Failed to update project failure status: %s", exc)

        return {
            "current_step": "failed",
            "step_status": StepStatus.FAILED.value,
        }

    # -- Compilation --------------------------------------------------------

    def compile(self, checkpointer: Any | None = None) -> Any:
        """
        Compile the workflow into an executable runnable.

        Args:
            checkpointer: Optional LangGraph checkpointer for persistence
                         (enables pause/resume and human-in-the-loop).

        Returns:
            Compiled LangGraph workflow runnable.
        """
        if self._workflow is None:
            self.build_workflow()

        assert self._workflow is not None

        if checkpointer:
            self._compiled = self._workflow.compile(checkpointer=checkpointer)
        else:
            self._compiled = self._workflow.compile()

        logger.info("PPTMasterPipeline compiled successfully")
        return self._compiled

    # -- Execution helpers --------------------------------------------------

    async def run(
        self,
        project_id: str,
        llm_provider: str = "openai",
        llm_model: str = "gpt-4o",
        canvas_format: str = "ppt169",
        user_instructions: str | None = None,
        ws_client_id: str | None = None,
        checkpointer: Any | None = None,
    ) -> PPTPipelineState:
        """
        Run the complete pipeline from scratch.

        Args:
            project_id: The project UUID.
            llm_provider: ``"openai"`` or ``"anthropic"``.
            llm_model: Model identifier (e.g. ``"gpt-4o"``).
            canvas_format: Canvas format key.
            user_instructions: Optional extra instructions.
            ws_client_id: WebSocket client ID for notifications.
            checkpointer: Optional checkpointer for persistence.

        Returns:
            Final pipeline state dict.
        """
        workflow = self.compile(checkpointer=checkpointer)
        initial_state = create_initial_state(
            project_id=project_id,
            llm_provider=llm_provider,
            llm_model=llm_model,
            canvas_format=canvas_format,
            user_instructions=user_instructions,
            ws_client_id=ws_client_id,
        )
        logger.info("Starting pipeline for project %s", project_id)
        result = await workflow.ainvoke(initial_state)
        return PPTPipelineState(**result)

    async def resume_from_confirmation(
        self,
        state: PPTPipelineState,
        checkpointer: Any | None = None,
    ) -> PPTPipelineState:
        """
        Resume the pipeline after user confirms Eight Confirmations.

        Updates the state with ``confirmation_status=confirmed`` and
        re-runs the workflow from the ``wait_confirmation`` node.

        Args:
            state: The current pipeline state (from DB or previous run).
            checkpointer: Optional checkpointer for persistence.

        Returns:
            Updated pipeline state dict.
        """
        workflow = self.compile(checkpointer=checkpointer)

        # Update state to reflect confirmation
        resumed_state = dict(state)
        resumed_state["confirmation_status"] = ConfirmationStatus.CONFIRMED.value
        resumed_state["needs_confirmation"] = False
        resumed_state["current_step"] = "strategist"
        resumed_state["step_status"] = StepStatus.RUNNING.value

        logger.info(
            "Resuming pipeline for project %s from confirmation",
            state.get("project_id"),
        )

        result = await workflow.ainvoke(PPTPipelineState(**resumed_state))
        return PPTPipelineState(**result)

    async def stream(
        self,
        state: PPTPipelineState,
        checkpointer: Any | None = None,
    ) -> Any:
        """
        Stream pipeline execution events.

        Yields event dicts with ``event`` and ``data`` keys, useful for
        sending real-time updates to the frontend via WebSocket.

        Args:
            state: Current pipeline state.
            checkpointer: Optional checkpointer.

        Yields:
            Event dicts from LangGraph.
        """
        workflow = self.compile(checkpointer=checkpointer)
        async for event in workflow.astream(state):
            yield event


# ---------------------------------------------------------------------------
# Singleton instance
# ---------------------------------------------------------------------------

_pipeline_instance: PPTMasterPipeline | None = None


def get_pipeline() -> PPTMasterPipeline:
    """Return (or create) the singleton PPTMasterPipeline instance."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = PPTMasterPipeline()
    return _pipeline_instance

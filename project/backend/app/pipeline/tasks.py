"""
PPT Master Pipeline - Celery task definitions.

Wraps the LangGraph pipeline steps as Celery tasks for distributed
execution.  Each task runs in a Celery worker and can be retried
independently on failure.
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from typing import Any

from app.pipeline.constants import CELERY_RETRY_COUNTDOWN, CELERY_TASK_MAX_RETRIES
from app.pipeline.graph import PPTMasterPipeline, get_pipeline
from app.pipeline.llm import LLMClient
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
    PPTPipelineState,
    StepStatus,
    create_initial_state,
)
from app.pipeline.workspace import ProjectWorkspace

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Celery app import (lazy to avoid circular deps at module load)
# ---------------------------------------------------------------------------

def _get_celery_app():
    """Get the Celery application instance."""
    from app.core.celery_app import celery_app as app
    return app


# ---------------------------------------------------------------------------
# Utility: run async function in sync Celery context
# ---------------------------------------------------------------------------

def _run_async(coro):
    """Run an async coroutine in the Celery worker context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Event loop is closed")
        return loop.run_until_complete(coro)
    except RuntimeError:
        # No running event loop — create a new one
        return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

def run_pipeline_step(
    project_id: str,
    step: str,
    input_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Execute a single pipeline step by name.

    This is the main Celery task that orchestrates individual pipeline
    steps. It looks up the step name and dispatches to the appropriate
    node function.

n    Args:
        project_id: The project UUID.
        step: Step name (source_processing / strategist / image_acquisition /
              executor / post_processing).
        input_data: Optional input data dict for the step.

    Returns:
        Dict with step result and updated state fields.
    """
    app = _get_celery_app()

    @app.task(
        bind=True,
        max_retries=CELERY_TASK_MAX_RETRIES,
        default_retry_delay=CELERY_RETRY_COUNTDOWN,
        name="app.pipeline.tasks.run_pipeline_step",
    )
    def _task(self, project_id: str, step: str, input_data: dict[str, Any] | None = None) -> dict[str, Any]:
        logger.info(
            "[run_pipeline_step] project=%s step=%s attempt=%d/%d",
            project_id,
            step,
            self.request.retries,
            CELERY_TASK_MAX_RETRIES,
        )

        # Build initial state
        state = create_initial_state(
            project_id=project_id,
            **(input_data or {}),
        )

        # Map step names to node functions
        node_map = {
            "source_processing": source_processing_node,
            "strategist": strategist_node,
            "image_acquisition": image_acquisition_node,
            "executor": executor_node,
            "post_processing": post_processing_node,
        }

        node_fn = node_map.get(step)
        if not node_fn:
            error_msg = f"Unknown pipeline step: {step}"
            logger.error(error_msg)
            return {"status": "failed", "error": error_msg}

        try:
            result = _run_async(node_fn(state))
            logger.info("[run_pipeline_step] %s completed successfully", step)
            return {"status": "completed", "step": step, "result": result}

        except Exception as exc:
            logger.exception(
                "[run_pipeline_step] %s failed: %s", step, exc
            )
            if self.request.retries < CELERY_TASK_MAX_RETRIES:
                logger.info("Retrying %s (attempt %d)", step, self.request.retries + 1)
                raise self.retry(exc=exc)
            return {
                "status": "failed",
                "step": step,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }

    # Call and return the inner task
    return _task.delay(project_id, step, input_data)


def process_source_file(source_id: str) -> dict[str, Any]:
    """
    Convert a single source file to Markdown.

    Args:
        source_id: The source file UUID.

    Returns:
        Dict with conversion result.
    """
    app = _get_celery_app()

    @app.task(
        bind=True,
        max_retries=CELERY_TASK_MAX_RETRIES,
        default_retry_delay=CELERY_RETRY_COUNTDOWN,
        name="app.pipeline.tasks.process_source_file",
    )
    def _task(self, source_id: str) -> dict[str, Any]:
        logger.info("[process_source_file] source_id=%s", source_id)

        async def _convert():
            from app.core.database import get_session_maker as _get_session_maker
            from app.models import SourceFile
            from app.services.storage_service import get_storage_backend

            async with _get_session_maker()() as db:
                result = await db.execute(
                    SourceFile.select().where(SourceFile.id == source_id)
                )
                source = result.scalar_one_or_none()
                if not source:
                    return {"status": "failed", "error": "Source file not found"}

                storage = get_storage_backend()
                runner = ScriptRunner()

                try:
                    data = await storage.get(source.storage_key)
                    import tempfile

                    with tempfile.NamedTemporaryFile(
                        suffix=f".{source.file_type}", delete=False
                    ) as tmp:
                        tmp.write(data)
                        tmp_path = tmp.name

                    md_content = await runner.convert_source_to_md(
                        tmp_path, source.file_type
                    )

                    source.markdown_content = md_content
                    source.conversion_status = "completed"
                    await db.commit()

                    import os

                    os.unlink(tmp_path)

                    return {
                        "status": "completed",
                        "source_id": source_id,
                        "content_length": len(md_content),
                    }

                except Exception as exc:
                    source.conversion_status = "failed"
                    source.conversion_error = str(exc)
                    await db.commit()
                    raise

        try:
            return _run_async(_convert())
        except Exception as exc:
            logger.exception("[process_source_file] Failed: %s", exc)
            if self.request.retries < CELERY_TASK_MAX_RETRIES:
                raise self.retry(exc=exc)
            return {
                "status": "failed",
                "source_id": source_id,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }

    return _task.delay(source_id)


def generate_images(project_id: str, image_ids: list[str] | None = None) -> dict[str, Any]:
    """
    Generate or acquire images for a project.

    Args:
        project_id: The project UUID.
        image_ids: Optional list of specific image resource IDs to generate.
                   If None, all pending images are processed.

    Returns:
        Dict with generation results.
    """
    app = _get_celery_app()

    @app.task(
        bind=True,
        max_retries=CELERY_TASK_MAX_RETRIES,
        default_retry_delay=CELERY_RETRY_COUNTDOWN * 2,
        name="app.pipeline.tasks.generate_images",
    )
    def _task(self, project_id: str, image_ids: list[str] | None = None) -> dict[str, Any]:
        logger.info(
            "[generate_images] project=%s image_ids=%s", project_id, image_ids
        )

        async def _generate():
            from app.core.database import get_session_maker as _get_session_maker
            from app.models import ImageResource, Project
            from app.services.storage_service import get_storage_backend

            async with _get_session_maker()() as db:
                result = await db.execute(
                    Project.select().where(Project.id == project_id)
                )
                project = result.scalar_one_or_none()
                if not project:
                    return {"status": "failed", "error": "Project not found"}

                # Build query
                from sqlalchemy import select
                query = select(ImageResource).where(
                    ImageResource.project_id == project_id
                )
                if image_ids:
                    query = query.where(ImageResource.id.in_(image_ids))
                else:
                    query = query.where(
                        ImageResource.status.in_(["pending", "needs_manual"])
                    )

                result = await db.execute(query)
                images = result.scalars().all()

                storage = get_storage_backend()
                runner = ScriptRunner()
                results = []

                for img in images:
                    try:
                        output_path = f"/tmp/{img.filename}"

                        if img.acquire_via == "ai" and img.generation_prompt:
                            await runner.run_image_gen(
                                project_path=f"/tmp/ppt_{project_id}",
                                prompt=img.generation_prompt,
                                output_path=output_path,
                            )
                        elif img.acquire_via == "web" and img.search_query:
                            await runner.run_image_search(
                                project_path=f"/tmp/ppt_{project_id}",
                                query=img.search_query,
                                output_path=output_path,
                            )
                        else:
                            results.append(
                                {
                                    "id": str(img.id),
                                    "status": "skipped",
                                    "reason": "No generation prompt or search query",
                                }
                            )
                            continue

                        # Upload to storage
                        if __import__("os").path.exists(output_path):
                            with open(output_path, "rb") as f:
                                storage_key = (
                                    f"projects/{project_id}/images/{img.filename}"
                                )
                                await storage.put(storage_key, f.read())
                                img.storage_key = storage_key
                                img.status = "generated"
                                await db.commit()
                                results.append(
                                    {
                                        "id": str(img.id),
                                        "status": "completed",
                                        "storage_key": storage_key,
                                    }
                                )
                        else:
                            results.append(
                                {
                                    "id": str(img.id),
                                    "status": "failed",
                                    "reason": "Output file not created",
                                }
                            )

                    except Exception as exc:
                        logger.error(
                            "Failed to generate image %s: %s", img.id, exc
                        )
                        results.append(
                            {"id": str(img.id), "status": "failed", "error": str(exc)}
                        )

                return {"status": "completed", "results": results}

        try:
            return _run_async(_generate())
        except Exception as exc:
            logger.exception("[generate_images] Failed: %s", exc)
            if self.request.retries < CELERY_TASK_MAX_RETRIES:
                raise self.retry(exc=exc)
            return {
                "status": "failed",
                "project_id": project_id,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }

    return _task.delay(project_id, image_ids)


def run_svg_quality_check_task(project_id: str) -> dict[str, Any]:
    """
    Run SVG quality checks on all pages for a project.

    Args:
        project_id: The project UUID.

    Returns:
        Dict with quality check results per page.
    """
    app = _get_celery_app()

    @app.task(
        bind=True,
        max_retries=2,
        default_retry_delay=CELERY_RETRY_COUNTDOWN,
        name="app.pipeline.tasks.run_svg_quality_check",
    )
    def _task(self, project_id: str) -> dict[str, Any]:
        logger.info("[run_svg_quality_check] project=%s", project_id)

        async def _check():
            from app.services.storage_service import get_storage_backend

            storage = get_storage_backend()
            runner = ScriptRunner()

            async with ProjectWorkspace(
                project_id=project_id,
                storage=storage,
            ) as ws:
                results = await runner.run_svg_quality_check(str(ws.path))

                # Update DB
                from app.core.database import get_session_maker as _get_session_maker
                from app.models import SVGPage

                async with _get_session_maker()() as db:
                    for filename, check_result in results.items():
                        if not filename.endswith(".svg"):
                            continue
                        result = await db.execute(
                            SVGPage.select().where(
                                SVGPage.project_id == project_id,
                                SVGPage.filename == filename,
                            )
                        )
                        page = result.scalar_one_or_none()
                        if page and isinstance(check_result, dict):
                            page.quality_check_status = (
                                "passed" if check_result.get("passed") else "failed"
                            )
                            page.quality_check_errors = check_result.get("errors", [])
                            page.quality_check_warnings = check_result.get(
                                "warnings", []
                            )
                    await db.commit()

                return {"status": "completed", "results": results}

        try:
            return _run_async(_check())
        except Exception as exc:
            logger.exception("[run_svg_quality_check] Failed: %s", exc)
            if self.request.retries < 2:
                raise self.retry(exc=exc)
            return {
                "status": "failed",
                "project_id": project_id,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }

    return _task.delay(project_id)


def export_pptx(project_id: str, export_options: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Export a project's SVG pages to PPTX format.

    Args:
        project_id: The project UUID.
        export_options: Optional export configuration (transition, animation, etc.).

    Returns:
        Dict with export results and file paths.
    """
    app = _get_celery_app()

    @app.task(
        bind=True,
        max_retries=CELERY_TASK_MAX_RETRIES,
        default_retry_delay=CELERY_RETRY_COUNTDOWN,
        name="app.pipeline.tasks.export_pptx",
    )
    def _task(self, project_id: str, export_options: dict[str, Any] | None = None) -> dict[str, Any]:
        logger.info("[export_pptx] project=%s options=%s", project_id, export_options)

        async def _export():
            from app.core.database import get_session_maker as _get_session_maker
            from app.models import PPTXExport, Project
            from app.services.storage_service import get_storage_backend

            async with _get_session_maker()() as db:
                result = await db.execute(
                    Project.select().where(Project.id == project_id)
                )
                project = result.scalar_one_or_none()
                if not project:
                    return {"status": "failed", "error": "Project not found"}

                storage = get_storage_backend()
                runner = ScriptRunner()
                exports = []

                async with ProjectWorkspace(
                    project_id=project_id,
                    storage=storage,
                    canvas_format=project.canvas_format,
                ) as ws:
                    # Ensure SVGs are finalized
                    await runner.run_finalize_svg(str(ws.path))

                    # Export
                    options = export_options or {}
                    options["format"] = project.canvas_format
                    pptx_paths = await runner.run_svg_to_pptx(str(ws.path), options)

                    for pptx_path in pptx_paths:
                        if not __import__("os").path.exists(pptx_path):
                            continue

                        filename = __import__("os").path.basename(pptx_path)
                        storage_key = f"projects/{project_id}/exports/{filename}"
                        file_size = __import__("os").path.getsize(pptx_path)

                        with open(pptx_path, "rb") as f:
                            await storage.put(storage_key, f.read())

                        export = PPTXExport(
                            project_id=project_id,
                            filename=filename,
                            storage_key=storage_key,
                            file_size=file_size,
                            transition_effect=options.get("transition"),
                            animation_effect=options.get("animation"),
                        )
                        db.add(export)
                        await db.commit()
                        await db.refresh(export)

                        exports.append(
                            {
                                "id": str(export.id),
                                "filename": filename,
                                "storage_key": storage_key,
                                "file_size": file_size,
                            }
                        )

                return {"status": "completed", "exports": exports}

        try:
            return _run_async(_export())
        except Exception as exc:
            logger.exception("[export_pptx] Failed: %s", exc)
            if self.request.retries < CELERY_TASK_MAX_RETRIES:
                raise self.retry(exc=exc)
            return {
                "status": "failed",
                "project_id": project_id,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }

    return _task.delay(project_id, export_options)


def run_full_pipeline(
    project_id: str,
    llm_provider: str = "openai",
    llm_model: str = "gpt-4o",
    canvas_format: str = "ppt169",
    user_instructions: str | None = None,
) -> dict[str, Any]:
    """
    Run the complete pipeline from start to finish.

    This task executes the entire LangGraph workflow in the Celery worker,
    handling the confirmation checkpoint by pausing and resuming.

    Args:
        project_id: The project UUID.
        llm_provider: LLM provider name.
        llm_model: LLM model identifier.
        canvas_format: Canvas format.
        user_instructions: Optional user instructions.

    Returns:
        Dict with final pipeline state.
    """
    app = _get_celery_app()

    @app.task(
        bind=True,
        max_retries=1,
        default_retry_delay=30,
        name="app.pipeline.tasks.run_full_pipeline",
    )
    def _task(self, project_id: str, llm_provider: str, llm_model: str,
              canvas_format: str, user_instructions: str | None) -> dict[str, Any]:
        logger.info(
            "[run_full_pipeline] project=%s provider=%s model=%s",
            project_id,
            llm_provider,
            llm_model,
        )

        async def _run():
            pipeline = get_pipeline()
            initial_state = create_initial_state(
                project_id=project_id,
                llm_provider=llm_provider,
                llm_model=llm_model,
                canvas_format=canvas_format,
                user_instructions=user_instructions,
            )

            workflow = pipeline.compile()
            result = await workflow.ainvoke(initial_state)

            return {
                "status": result.get("step_status", "unknown"),
                "current_step": result.get("current_step"),
                "project_id": project_id,
                "has_design_spec": result.get("design_spec") is not None,
                "has_spec_lock": result.get("spec_lock") is not None,
                "svg_pages_count": len(result.get("svg_pages", [])),
                "exports_count": len(result.get("exports", [])),
                "errors": result.get("errors", []),
            }

        try:
            return _run_async(_run())
        except Exception as exc:
            logger.exception("[run_full_pipeline] Failed: %s", exc)
            return {
                "status": "failed",
                "project_id": project_id,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }

    return _task.delay(project_id, llm_provider, llm_model, canvas_format, user_instructions)


def resume_pipeline_after_confirmation(
    project_id: str,
    confirmed_confirmations: dict[str, Any],
) -> dict[str, Any]:
    """
    Resume the pipeline after the user confirms Eight Confirmations.

    Updates the design spec with user-confirmed values and re-runs
    the workflow from the wait_confirmation node onward.

    Args:
        project_id: The project UUID.
        confirmed_confirmations: The user-confirmed Eight Confirmations dict.

    Returns:
        Dict with updated pipeline state.
    """
    app = _get_celery_app()

    @app.task(
        bind=True,
        max_retries=1,
        default_retry_delay=30,
        name="app.pipeline.tasks.resume_pipeline_after_confirmation",
    )
    def _task(self, project_id: str, confirmed_confirmations: dict[str, Any]) -> dict[str, Any]:
        logger.info(
            "[resume_pipeline] project=%s confirmations=%s",
            project_id,
            confirmed_confirmations,
        )

        async def _resume():
            from app.core.database import get_session_maker as _get_session_maker
            from app.models import DesignSpec

            # Update confirmations in DB
            async with _get_session_maker()() as db:
                result = await db.execute(
                    DesignSpec.select().where(DesignSpec.project_id == project_id)
                )
                spec = result.scalar_one_or_none()
                if not spec:
                    return {"status": "failed", "error": "Design spec not found"}

                # Update with confirmed values
                spec.confirmation_canvas = confirmed_confirmations.get("canvas_format")
                spec.confirmation_page_count = confirmed_confirmations.get("page_count")
                spec.confirmation_audience = confirmed_confirmations.get("audience")
                spec.confirmation_style_mode = confirmed_confirmations.get("style_mode")
                spec.confirmation_style_descriptor = confirmed_confirmations.get(
                    "style_descriptor"
                )
                spec.confirmation_color_scheme = confirmed_confirmations.get("color_scheme")
                spec.confirmation_icon_approach = confirmed_confirmations.get("icon_approach")
                spec.confirmation_typography = confirmed_confirmations.get("typography")
                spec.confirmation_image_approach = confirmed_confirmations.get("image_approach")
                spec.confirmation_status = ConfirmationStatus.CONFIRMED.value
                await db.commit()

            # Build state and resume
            pipeline = get_pipeline()
            state = create_initial_state(project_id=project_id)
            state["confirmation_status"] = ConfirmationStatus.CONFIRMED.value
            state["needs_confirmation"] = False
            state["confirmations"] = confirmed_confirmations

            result_state = await pipeline.resume_from_confirmation(state)

            return {
                "status": result_state.get("step_status", "unknown"),
                "current_step": result_state.get("current_step"),
                "project_id": project_id,
                "svg_pages_count": len(result_state.get("svg_pages", [])),
                "exports_count": len(result_state.get("exports", [])),
                "errors": result_state.get("errors", []),
            }

        try:
            return _run_async(_resume())
        except Exception as exc:
            logger.exception("[resume_pipeline] Failed: %s", exc)
            return {
                "status": "failed",
                "project_id": project_id,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }

    return _task.delay(project_id, confirmed_confirmations)

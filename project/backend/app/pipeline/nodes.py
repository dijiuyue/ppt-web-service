"""
PPT Master Pipeline - Node implementations.

Each async function defined here corresponds to a node in the LangGraph
StateGraph.  Nodes receive the current PPTPipelineState dict and return
a partial dict with updated fields.

All nodes follow these conventions:
- Accept ``state: PPTPipelineState`` as the first argument.
- Return a ``dict`` (NOT the full TypedDict) containing only mutated keys.
- Log extensively via the module logger.
- Catch exceptions, log them, and add error messages to state["errors"].
- Use the workspace context manager for file-system operations.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any
from uuid import UUID

from app.pipeline.constants import CANVAS_FORMATS
from app.pipeline.llm import LLMClient, LLMError
from app.pipeline.prompts import (
    EXECUTOR_PAGE_PROMPT,
    EXECUTOR_SYSTEM_PROMPT_BASE,
    SOURCE_AGGREGATION_PROMPT,
    SPEAKER_NOTES_PROMPT,
    STRATEGIST_DESIGN_SPEC_PROMPT,
    STRATEGIST_EIGHT_CONFIRMATIONS_PROMPT,
    STRATEGIST_SPEC_LOCK_PROMPT,
    STRATEGIST_SYSTEM_PROMPT,
    SVG_QUALITY_PROMPT,
)
from app.pipeline.script_runner import ScriptRunner, ScriptRunnerError
from app.pipeline.state import (
    ConfirmationStatus,
    PPTPipelineState,
    StepStatus,
    add_error,
    update_state,
)
from app.pipeline.workspace import ProjectWorkspace

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DB / Storage helpers (lazy import to avoid circular deps)
# ---------------------------------------------------------------------------

def _get_db_session():
    """Get a DB session from the global session factory."""
    from app.core.database import get_session_maker
    return get_session_maker()()

async def _get_storage():
    """Get the global storage backend."""
    from app.services.storage_service import get_storage_backend
    return get_storage_backend()

async def _notify_ws(project_id: str, message_type: str, data: dict[str, Any]) -> None:
    """Send a notification via WebSocket manager."""
    try:
        from app.api.websocket import ws_manager
        await ws_manager.broadcast_to_project(project_id, {"type": message_type, "data": data})
    except Exception as exc:
        logger.warning("WebSocket notification failed: %s", exc)

async def _update_project_status(
    project_id: str,
    step: str | None = None,
    step_status: str | None = None,
    error: str | None = None,
) -> None:
    """Update the project's pipeline status in the database."""
    try:
        pid = UUID(project_id)
        async with _get_db_session() as db:
            from app.models import Project
            result = await db.execute(
                Project.select().where(Project.id == pid)
            )
            project = result.scalar_one_or_none()
            if not project:
                logger.warning("Project %s not found for status update", project_id)
                return

            if step:
                project.current_step = step
            if step_status:
                project.step_status = step_status
            if error:
                project.status = "failed"
            await db.commit()
    except Exception as exc:
        logger.error("Failed to update project status: %s", exc)

async def _create_pipeline_job(
    project_id: str,
    step: str,
    status: str = "running",
    input_data: dict[str, Any] | None = None,
) -> str | None:
    """Create a pipeline job record and return its ID."""
    try:
        pid = UUID(project_id)
        async with _get_db_session() as db:
            from app.models import PipelineJob
            job = PipelineJob(
                project_id=pid,
                step=step,
                status=status,
                input_data=input_data or {},
            )
            db.add(job)
            await db.commit()
            await db.refresh(job)
            return str(job.id)
    except Exception as exc:
        logger.error("Failed to create pipeline job: %s", exc)
        return None

async def _update_pipeline_job(
    job_id: str,
    status: str | None = None,
    output_data: dict[str, Any] | None = None,
    error_message: str | None = None,
    error_traceback: str | None = None,
) -> None:
    """Update a pipeline job record."""
    try:
        jid = UUID(job_id)
        async with _get_db_session() as db:
            from app.models import PipelineJob
            result = await db.execute(
                PipelineJob.select().where(PipelineJob.id == jid)
            )
            job = result.scalar_one_or_none()
            if not job:
                return
            if status:
                job.status = status
            if output_data:
                job.output_data = output_data
            if error_message:
                job.error_message = error_message
            if error_traceback:
                job.error_traceback = error_traceback
            await db.commit()
    except Exception as exc:
        logger.error("Failed to update pipeline job %s: %s", job_id, exc)

async def _get_source_files(project_id: str) -> list[dict[str, Any]]:
    """Fetch all source files for a project from the database."""
    try:
        pid = UUID(project_id)
        async with _get_db_session() as db:
            from app.models import SourceFile
            result = await db.execute(
                SourceFile.select()
                .where(SourceFile.project_id == pid)
                .order_by(SourceFile.sort_order)
            )
            rows = result.scalars().all()
            return [
                {
                    "id": str(r.id),
                    "original_filename": r.original_filename,
                    "file_type": r.file_type,
                    "storage_key": r.storage_key,
                    "markdown_content": r.markdown_content,
                    "conversion_status": r.conversion_status,
                    "conversion_error": r.conversion_error,
                }
                for r in rows
            ]
    except Exception as exc:
        logger.error("Failed to fetch source files: %s", exc)
        return []

async def _get_project_config(project_id: str) -> dict[str, Any]:
    """Fetch project configuration from the database."""
    try:
        pid = UUID(project_id)
        async with _get_db_session() as db:
            from app.models import Project
            result = await db.execute(
                Project.select().where(Project.id == pid)
            )
            project = result.scalar_one_or_none()
            if not project:
                return {}
            return {
                "name": project.name,
                "description": project.description or "",
                "canvas_format": project.canvas_format,
                "llm_provider": project.llm_provider,
                "llm_model": project.llm_model,
                "template_path": project.template_path,
            }
    except Exception as exc:
        logger.error("Failed to fetch project config: %s", exc)
        return {}

async def _get_design_spec(project_id: str) -> dict[str, Any] | None:
    """Fetch the design spec for a project."""
    try:
        async with _get_db_session() as db:
            from app.models import DesignSpec
            result = await db.execute(
                DesignSpec.select().where(DesignSpec.project_id == project_id)
            )
            spec = result.scalar_one_or_none()
            if not spec:
                return None
            return {
                "id": str(spec.id),
                "confirmation_status": spec.confirmation_status,
                "confirmations": {
                    "canvas_format": spec.confirmation_canvas,
                    "page_count": spec.confirmation_page_count,
                    "audience": spec.confirmation_audience,
                    "style_mode": spec.confirmation_style_mode,
                    "style_descriptor": spec.confirmation_style_descriptor,
                    "color_scheme": spec.confirmation_color_scheme,
                    "icon_approach": spec.confirmation_icon_approach,
                    "typography": spec.confirmation_typography,
                    "image_approach": spec.confirmation_image_approach,
                },
                "spec_content": spec.spec_content,
                "spec_storage_key": spec.spec_storage_key,
            }
    except Exception as exc:
        logger.error("Failed to fetch design spec: %s", exc)
        return None

async def _get_spec_lock(project_id: str) -> dict[str, Any] | None:
    """Fetch the spec lock for a project."""
    try:
        async with _get_db_session() as db:
            from app.models import SpecLock
            result = await db.execute(
                SpecLock.select().where(SpecLock.project_id == project_id)
            )
            lock = result.scalar_one_or_none()
            if not lock:
                return None
            return {
                "id": str(lock.id),
                "canvas_viewbox": lock.canvas_viewbox,
                "canvas_format": lock.canvas_format,
                "colors": lock.colors,
                "typography": lock.typography,
                "icons": lock.icons,
                "images": lock.images,
                "page_rhythm": lock.page_rhythm,
                "page_layouts": lock.page_layouts,
                "page_charts": lock.page_charts,
                "forbidden": lock.forbidden,
                "lock_content": lock.lock_content,
            }
    except Exception as exc:
        logger.error("Failed to fetch spec lock: %s", exc)
        return None

async def _get_image_resources(project_id: str) -> list[dict[str, Any]]:
    """Fetch all image resources for a project."""
    try:
        async with _get_db_session() as db:
            from app.models import ImageResource
            result = await db.execute(
                ImageResource.select().where(
                    ImageResource.project_id == project_id
                )
            )
            rows = result.scalars().all()
            return [
                {
                    "id": str(r.id),
                    "filename": r.filename,
                    "purpose": r.purpose,
                    "image_type": r.image_type,
                    "acquire_via": r.acquire_via,
                    "status": r.status,
                    "generation_prompt": r.generation_prompt,
                    "search_query": r.search_query,
                    "storage_key": r.storage_key,
                }
                for r in rows
            ]
    except Exception as exc:
        logger.error("Failed to fetch image resources: %s", exc)
        return []

async def _save_svg_page(
    project_id: str,
    page_number: int,
    page_name: str,
    svg_content: str,
    filename: str,
    page_rhythm: str | None = None,
    page_layout: str | None = None,
    page_chart: str | None = None,
) -> str | None:
    """Save an SVG page to the database and storage."""
    try:
        storage = await _get_storage()
        storage_key = f"projects/{project_id}/svg_output/{filename}"
        await storage.put(storage_key, svg_content.encode("utf-8"))

        async with _get_db_session() as db:
            from app.models import SVGPage
            page = SVGPage(
                project_id=project_id,
                page_number=page_number,
                page_name=page_name,
                filename=filename,
                svg_content=svg_content,
                svg_storage_key=storage_key,
                page_rhythm=page_rhythm,
                page_layout=page_layout,
                page_chart=page_chart,
            )
            db.add(page)
            await db.commit()
            await db.refresh(page)
            return str(page.id)
    except Exception as exc:
        logger.error("Failed to save SVG page: %s", exc)
        return None

async def _save_speaker_note(
    project_id: str,
    svg_page_id: str,
    page_number: int,
    page_name: str,
    note_content: str,
) -> str | None:
    """Save a speaker note to the database."""
    try:
        async with _get_db_session() as db:
            from app.models import SpeakerNote
            note = SpeakerNote(
                project_id=project_id,
                svg_page_id=svg_page_id,
                page_number=page_number,
                page_name=page_name,
                note_content=note_content,
            )
            db.add(note)
            await db.commit()
            await db.refresh(note)
            return str(note.id)
    except Exception as exc:
        logger.error("Failed to save speaker note: %s", exc)
        return None

async def _save_image_resource(
    project_id: str,
    filename: str,
    storage_key: str,
    **kwargs: Any,
) -> str | None:
    """Save or update an image resource record."""
    try:
        async with _get_db_session() as db:
            from app.models import ImageResource
            img = ImageResource(
                project_id=project_id,
                filename=filename,
                storage_key=storage_key,
                **kwargs,
            )
            db.add(img)
            await db.commit()
            await db.refresh(img)
            return str(img.id)
    except Exception as exc:
        logger.error("Failed to save image resource: %s", exc)
        return None


# ===================================================================
# Node implementations
# ===================================================================

async def source_processing_node(state: PPTPipelineState) -> dict[str, Any]:
    """
    Step 1: Convert all source files to Markdown and aggregate.

    Reads source_files from DB, invokes the appropriate conversion
    script for each file type, writes converted markdown back to DB,
    and aggregates everything into a single source_content string.
    """
    project_id = state["project_id"]
    logger.info("[source_processing] Starting for project %s", project_id)

    await _update_project_status(
        project_id,
        step="source_processing",
        step_status=StepStatus.RUNNING.value,
    )
    job_id = await _create_pipeline_job(project_id, "source_processing")

    try:
        source_files = await _get_source_files(project_id)
        if not source_files:
            logger.warning("No source files found for project %s", project_id)
            await _update_project_status(
                project_id, step_status=StepStatus.COMPLETED.value
            )
            if job_id:
                await _update_pipeline_job(job_id, status="completed")
            return {
                "current_step": "source_processing",
                "step_status": StepStatus.COMPLETED.value,
                "source_content": "",
            }

        runner = ScriptRunner()
        storage = await _get_storage()
        converted_sources: list[str] = []

        for sf in source_files:
            if sf["conversion_status"] == "completed" and sf["markdown_content"]:
                converted_sources.append(sf["markdown_content"])
                logger.debug("Using cached markdown for %s", sf["original_filename"])
                continue

            logger.info(
                "Converting source: %s (type=%s)",
                sf["original_filename"],
                sf["file_type"],
            )

            try:
                # Download from storage to temp file
                data = await storage.get(sf["storage_key"])
                import tempfile
                with tempfile.NamedTemporaryFile(
                    suffix=f".{sf['file_type']}", delete=False
                ) as tmp:
                    tmp.write(data)
                    tmp_path = tmp.name

                # Convert
                md_content = await runner.convert_source_to_md(
                    tmp_path, sf["file_type"]
                )
                converted_sources.append(md_content)

                # Update DB
                async with _get_db_session() as db:
                    from app.models import SourceFile
                    result = await db.execute(
                        SourceFile.select().where(SourceFile.id == sf["id"])
                    )
                    row = result.scalar_one()
                    row.markdown_content = md_content
                    row.conversion_status = "completed"
                    await db.commit()

                # Cleanup temp file
                os.unlink(tmp_path)

            except Exception as exc:
                logger.error(
                    "Failed to convert %s: %s", sf["original_filename"], exc
                )
                async with _get_db_session() as db:
                    from app.models import SourceFile
                    result = await db.execute(
                        SourceFile.select().where(SourceFile.id == sf["id"])
                    )
                    row = result.scalar_one()
                    row.conversion_status = "failed"
                    row.conversion_error = str(exc)
                    await db.commit()

        # Aggregate all converted sources
        if len(converted_sources) == 1:
            aggregated = converted_sources[0]
        elif len(converted_sources) > 1:
            sources_text = "\n\n---\n\n".join(
                f"## Source {i + 1}\n\n{src}"
                for i, src in enumerate(converted_sources)
            )
            # Use LLM to aggregate if there are multiple sources
            config = await _get_project_config(project_id)
            llm = LLMClient(
                provider=config.get("llm_provider", "openai"),
                model=config.get("llm_model", "gpt-4o"),
            )
            prompt = SOURCE_AGGREGATION_PROMPT.format(sources=sources_text)
            aggregated = await llm.chat_completion(
                system_prompt="You are a content analyst.",
                user_prompt=prompt,
            )
            await llm.close()
        else:
            aggregated = ""

        await _update_project_status(
            project_id, step_status=StepStatus.COMPLETED.value
        )
        if job_id:
            await _update_pipeline_job(
                job_id,
                status="completed",
                output_data={"source_count": len(source_files)},
            )

        await _notify_ws(
            project_id,
            "step_change",
            {"step": "source_processing", "status": "completed"},
        )

        return {
            "current_step": "source_processing",
            "step_status": StepStatus.COMPLETED.value,
            "source_content": aggregated,
        }

    except Exception as exc:
        logger.exception("[source_processing] Failed: %s", exc)
        await _update_project_status(project_id, error=str(exc))
        if job_id:
            await _update_pipeline_job(
                job_id,
                status="failed",
                error_message=str(exc),
            )
        return {
            "step_status": StepStatus.FAILED.value,
            "errors": [*state.get("errors", []), f"source_processing: {exc}"],
        }


async def strategist_node(state: PPTPipelineState) -> dict[str, Any]:
    """
    Step 2: Generate Eight Confirmations using the Strategist.

    Reads source content and project config, builds the LLM prompt,
    generates Eight Confirmations, saves them to DB, and sets the
    WAITING_CONFIRMATION state.  Also notifies frontend via WebSocket.
    """
    project_id = state["project_id"]
    logger.info("[strategist] Starting for project %s", project_id)

    await _update_project_status(
        project_id,
        step="strategist",
        step_status=StepStatus.RUNNING.value,
    )
    job_id = await _create_pipeline_job(project_id, "strategist")

    try:
        source_content = state.get("source_content", "")
        if not source_content:
            raise ValueError("No source content available for strategist")

        config = await _get_project_config(project_id)
        llm = LLMClient(
            provider=config.get("llm_provider", state.get("llm_provider", "openai")),
            model=config.get("llm_model", state.get("llm_model", "gpt-4o")),
        )

        # Generate Eight Confirmations
        prompt = STRATEGIST_EIGHT_CONFIRMATIONS_PROMPT.format(
            source_content=source_content[:12000]  # Limit context size
        )
        logger.debug("[strategist] Sending Eight Confirmations prompt to LLM")

        raw_response = await llm.chat_completion(
            system_prompt=STRATEGIST_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.7,
        )

        # Parse JSON response
        try:
            confirmations = llm.extract_json_from_markdown(raw_response)
            confirmations_data = json.loads(confirmations)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse Eight Confirmations JSON: %s", exc)
            # Fallback: try the json completion method
            confirmations_data = await llm.chat_completion_json(
                system_prompt=STRATEGIST_SYSTEM_PROMPT,
                user_prompt=prompt + "\n\nEnsure you output ONLY valid JSON.",
            )

        await llm.close()

        # Save to database
        async with _get_db_session() as db:
            from app.models import DesignSpec
            result = await db.execute(
                DesignSpec.select().where(DesignSpec.project_id == project_id)
            )
            spec = result.scalar_one_or_none()
            if not spec:
                spec = DesignSpec(project_id=project_id)
                db.add(spec)

            spec.confirmation_canvas = confirmations_data.get("canvas_format")
            spec.confirmation_page_count = confirmations_data.get("page_count")
            spec.confirmation_audience = confirmations_data.get("audience")
            spec.confirmation_style_mode = confirmations_data.get("style_mode")
            spec.confirmation_style_descriptor = confirmations_data.get(
                "style_descriptor"
            )
            spec.confirmation_color_scheme = confirmations_data.get("color_scheme")
            spec.confirmation_icon_approach = confirmations_data.get("icon_approach")
            spec.confirmation_typography = confirmations_data.get("typography")
            spec.confirmation_image_approach = confirmations_data.get("image_approach")
            spec.confirmation_status = ConfirmationStatus.PENDING.value
            await db.commit()

        await _update_project_status(
            project_id,
            step="strategist",
            step_status=StepStatus.WAITING_CONFIRMATION.value,
        )
        if job_id:
            await _update_pipeline_job(
                job_id,
                status="waiting_confirmation",
                output_data={"confirmations": confirmations_data},
            )

        await _notify_ws(
            project_id,
            "confirmation_needed",
            {
                "step": "strategist",
                "status": "waiting_confirmation",
                "confirmations": confirmations_data,
            },
        )

        return {
            "current_step": "strategist",
            "step_status": StepStatus.WAITING_CONFIRMATION.value,
            "confirmations": confirmations_data,
            "confirmation_status": ConfirmationStatus.PENDING.value,
            "needs_confirmation": True,
        }

    except Exception as exc:
        logger.exception("[strategist] Failed: %s", exc)
        await _update_project_status(project_id, error=str(exc))
        if job_id:
            await _update_pipeline_job(
                job_id,
                status="failed",
                error_message=str(exc),
            )
        return {
            "step_status": StepStatus.FAILED.value,
            "errors": [*state.get("errors", []), f"strategist: {exc}"],
        }


async def wait_confirmation_node(state: PPTPipelineState) -> dict[str, Any]:
    """
    Step 3: Wait for user confirmation of Eight Confirmations.

    If already confirmed, proceed to generate the full design_spec
    and spec_lock.  Otherwise, stay in WAITING_CONFIRMATION state.
    """
    project_id = state["project_id"]
    confirmation_status = state.get("confirmation_status", "pending")

    logger.info(
        "[wait_confirmation] Project %s confirmation_status=%s",
        project_id,
        confirmation_status,
    )

    if confirmation_status != ConfirmationStatus.CONFIRMED.value:
        # Still waiting — end the workflow here; will be resumed later
        logger.info("[wait_confirmation] Still waiting for user confirmation")
        return {"needs_confirmation": True}

    # Confirmed — generate full design_spec and spec_lock
    logger.info("[wait_confirmation] Confirmed, generating design spec and spec lock")

    await _update_project_status(
        project_id,
        step="strategist",
        step_status=StepStatus.RUNNING.value,
    )
    job_id = await _create_pipeline_job(
        project_id, "strategist", input_data={"phase": "design_spec_generation"}
    )

    try:
        source_content = state.get("source_content", "")
        confirmations = state.get("confirmations", {})

        config = await _get_project_config(project_id)
        llm = LLMClient(
            provider=config.get("llm_provider", state.get("llm_provider", "openai")),
            model=config.get("llm_model", state.get("llm_model", "gpt-4o")),
        )

        # Generate Design Spec
        logger.debug("[wait_confirmation] Generating Design Spec")
        design_spec_prompt = STRATEGIST_DESIGN_SPEC_PROMPT.format(
            source_content=source_content[:12000],
            confirmations_json=json.dumps(confirmations, indent=2, ensure_ascii=False),
        )
        design_spec = await llm.chat_completion(
            system_prompt=STRATEGIST_SYSTEM_PROMPT,
            user_prompt=design_spec_prompt,
            temperature=0.7,
            max_tokens=8192,
        )

        # Generate Spec Lock
        logger.debug("[wait_confirmation] Generating Spec Lock")
        spec_lock_prompt = STRATEGIST_SPEC_LOCK_PROMPT.format(
            design_spec=design_spec[:8000]
        )
        spec_lock_raw = await llm.chat_completion_json(
            system_prompt=STRATEGIST_SYSTEM_PROMPT,
            user_prompt=spec_lock_prompt,
            temperature=0.3,
            max_tokens=4096,
        )

        await llm.close()

        # Save to DB
        storage = await _get_storage()

        async with _get_db_session() as db:
            from app.models import DesignSpec, SpecLock

            # Save design spec
            spec_storage_key = f"projects/{project_id}/design_spec.md"
            await storage.put(spec_storage_key, design_spec.encode("utf-8"))

            result = await db.execute(
                DesignSpec.select().where(DesignSpec.project_id == project_id)
            )
            spec = result.scalar_one()
            spec.spec_content = design_spec
            spec.spec_storage_key = spec_storage_key
            await db.commit()

            # Save spec lock
            lock_content = json.dumps(spec_lock_raw, indent=2, ensure_ascii=False)
            lock_storage_key = f"projects/{project_id}/spec_lock.md"
            await storage.put(lock_storage_key, lock_content.encode("utf-8"))

            result = await db.execute(
                SpecLock.select().where(SpecLock.project_id == project_id)
            )
            lock = result.scalar_one_or_none()
            if not lock:
                lock = SpecLock(project_id=project_id)
                db.add(lock)

            lock.canvas_viewbox = spec_lock_raw.get("canvas_viewbox")
            lock.canvas_format = spec_lock_raw.get("canvas_format")
            lock.colors = spec_lock_raw.get("colors")
            lock.typography = spec_lock_raw.get("typography")
            lock.icons = spec_lock_raw.get("icons")
            lock.images = spec_lock_raw.get("images")
            lock.page_rhythm = spec_lock_raw.get("page_rhythm")
            lock.page_layouts = spec_lock_raw.get("page_layouts")
            lock.page_charts = spec_lock_raw.get("page_charts")
            lock.forbidden = spec_lock_raw.get("forbidden")
            lock.lock_content = lock_content
            lock.lock_storage_key = lock_storage_key
            await db.commit()

        if job_id:
            await _update_pipeline_job(
                job_id,
                status="completed",
                output_data={"has_design_spec": True, "has_spec_lock": True},
            )

        await _notify_ws(
            project_id,
            "step_change",
            {"step": "strategist", "status": "completed"},
        )

        # Determine if images are needed
        image_approach = confirmations.get("image_approach", "E")
        skip_images = image_approach == "E"  # E = no images

        return {
            "current_step": "strategist",
            "step_status": StepStatus.COMPLETED.value,
            "design_spec": design_spec,
            "design_spec_storage_key": spec_storage_key,
            "spec_lock": lock_content,
            "spec_lock_storage_key": lock_storage_key,
            "needs_confirmation": False,
            "skip_images": skip_images,
        }

    except Exception as exc:
        logger.exception("[wait_confirmation] Failed: %s", exc)
        await _update_project_status(project_id, error=str(exc))
        if job_id:
            await _update_pipeline_job(
                job_id,
                status="failed",
                error_message=str(exc),
            )
        return {
            "step_status": StepStatus.FAILED.value,
            "errors": [*state.get("errors", []), f"wait_confirmation: {exc}"],
        }


async def image_acquisition_node(state: PPTPipelineState) -> dict[str, Any]:
    """
    Step 4: Acquire images needed by the design spec.

    Checks spec_lock images list and design_spec image requirements,
    generates or searches for each image, and updates the database.
    """
    project_id = state["project_id"]
    logger.info("[image_acquisition] Starting for project %s", project_id)

    await _update_project_status(
        project_id,
        step="image_acquisition",
        step_status=StepStatus.RUNNING.value,
    )
    job_id = await _create_pipeline_job(project_id, "image_acquisition")

    try:
        spec_lock_data = state.get("spec_lock")
        if not spec_lock_data:
            # Try to load from DB
            lock = await _get_spec_lock(project_id)
            if lock:
                spec_lock_data = lock

        if not spec_lock_data:
            logger.warning("No spec_lock found, skipping image acquisition")
            if job_id:
                await _update_pipeline_job(job_id, status="completed")
            return {
                "current_step": "image_acquisition",
                "step_status": StepStatus.COMPLETED.value,
                "skip_images": True,
            }

        # Parse spec_lock if it's a string
        if isinstance(spec_lock_data, str):
            spec_lock_data = json.loads(spec_lock_data)

        images_needed = spec_lock_data.get("images", [])
        if not images_needed:
            logger.info("No images required by spec_lock")
            if job_id:
                await _update_pipeline_job(job_id, status="completed")
            return {
                "current_step": "image_acquisition",
                "step_status": StepStatus.COMPLETED.value,
                "skip_images": True,
            }

        runner = ScriptRunner()
        storage = await _get_storage()
        config = await _get_project_config(project_id)
        canvas_format = config.get("canvas_format", "ppt169")
        canvas_info = CANVAS_FORMATS.get(canvas_format, CANVAS_FORMATS["ppt169"])

        async with ProjectWorkspace(
            project_id=project_id,
            canvas_format=canvas_format,
        ) as ws:
            acquired_images: list[dict[str, Any]] = []

            for img_spec in images_needed:
                img_name = img_spec.get("name", "unnamed")
                img_path = img_spec.get("path", f"images/{img_name}.png")
                no_crop = img_spec.get("no_crop", False)

                logger.info("[image_acquisition] Processing image: %s", img_name)

                # Determine acquisition strategy
                generation_prompt = img_spec.get("generation_prompt", "")
                search_query = img_spec.get("search_query", "")

                output_path = str(ws.path / img_path)
                storage_key = f"projects/{project_id}/{img_path}"

                try:
                    if generation_prompt:
                        # AI generation
                        result_path = await runner.run_image_gen(
                            project_path=str(ws.path),
                            prompt=generation_prompt,
                            output_path=output_path,
                            width=canvas_info["width"],
                            height=canvas_info["height"],
                        )
                        acquire_via = "ai"
                    elif search_query:
                        # Web search
                        search_result = await runner.run_image_search(
                            project_path=str(ws.path),
                            query=search_query,
                            output_path=str(ws.images_dir),
                            max_results=3,
                        )
                        result_path = search_result.get("downloaded_path", output_path)
                        acquire_via = "web"
                    else:
                        # Placeholder
                        logger.warning(
                            "No generation prompt or search query for %s", img_name
                        )
                        acquire_via = "placeholder"
                        result_path = output_path

                    # Upload to storage
                    if os.path.exists(result_path):
                        with open(result_path, "rb") as f:
                            await storage.put(storage_key, f.read())

                    # Save to DB
                    await _save_image_resource(
                        project_id=project_id,
                        filename=f"{img_name}.png",
                        storage_key=storage_key,
                        purpose=img_spec.get("purpose", "Background"),
                        image_type=img_spec.get("type", "Photography"),
                        acquire_via=acquire_via,
                        status="generated" if acquire_via == "ai" else "sourced",
                        generation_prompt=generation_prompt or None,
                        search_query=search_query or None,
                    )

                    acquired_images.append(
                        {
                            "name": img_name,
                            "path": img_path,
                            "storage_key": storage_key,
                            "acquire_via": acquire_via,
                        }
                    )

                except Exception as exc:
                    logger.error(
                        "Failed to acquire image %s: %s", img_name, exc
                    )
                    acquired_images.append(
                        {
                            "name": img_name,
                            "path": img_path,
                            "error": str(exc),
                            "acquire_via": "placeholder",
                        }
                    )

        await _update_project_status(
            project_id, step_status=StepStatus.COMPLETED.value
        )
        if job_id:
            await _update_pipeline_job(
                job_id,
                status="completed",
                output_data={"acquired_images": acquired_images},
            )

        await _notify_ws(
            project_id,
            "step_change",
            {"step": "image_acquisition", "status": "completed"},
        )

        return {
            "current_step": "image_acquisition",
            "step_status": StepStatus.COMPLETED.value,
            "image_resources": acquired_images,
            "skip_images": False,
        }

    except Exception as exc:
        logger.exception("[image_acquisition] Failed: %s", exc)
        await _update_project_status(project_id, error=str(exc))
        if job_id:
            await _update_pipeline_job(
                job_id,
                status="failed",
                error_message=str(exc),
            )
        return {
            "step_status": StepStatus.FAILED.value,
            "errors": [*state.get("errors", []), f"image_acquisition: {exc}"],
        }


async def executor_node(state: PPTPipelineState) -> dict[str, Any]:
    """
    Step 5: Generate SVG pages sequentially.

    Reads the design_spec and spec_lock, then generates one SVG page
    at a time using the LLM. Each page is saved to DB, quality-checked,
    and paired with speaker notes.
    """
    project_id = state["project_id"]
    logger.info("[executor] Starting for project %s", project_id)

    await _update_project_status(
        project_id,
        step="executor",
        step_status=StepStatus.RUNNING.value,
    )
    job_id = await _create_pipeline_job(project_id, "executor")

    try:
        design_spec = state.get("design_spec", "")
        spec_lock_data = state.get("spec_lock", "")

        if not design_spec:
            spec = await _get_design_spec(project_id)
            if spec:
                design_spec = spec.get("spec_content", "")

        if not spec_lock_data:
            lock = await _get_spec_lock(project_id)
            if lock:
                spec_lock_data = lock.get("lock_content", "")

        if not design_spec or not spec_lock_data:
            raise ValueError("Design spec and spec_lock are required for executor")

        # Parse spec_lock
        if isinstance(spec_lock_data, str):
            spec_lock_parsed = json.loads(spec_lock_data)
        else:
            spec_lock_parsed = spec_lock_data

        canvas_viewbox = spec_lock_parsed.get("canvas_viewbox", "0 0 1280 720")
        page_layouts = spec_lock_parsed.get("page_layouts", {})
        page_rhythms = spec_lock_parsed.get("page_rhythm", {})
        page_charts = spec_lock_parsed.get("page_charts", {})

        config = await _get_project_config(project_id)
        llm = LLMClient(
            provider=config.get("llm_provider", state.get("llm_provider", "openai")),
            model=config.get("llm_model", state.get("llm_model", "gpt-4o")),
        )

        svg_pages: list[dict[str, Any]] = []
        speaker_notes: list[dict[str, Any]] = []

        # Sort pages by page number
        sorted_pages = sorted(page_layouts.items(), key=lambda x: x[0])

        for page_key, layout in sorted_pages:
            if not layout:
                logger.warning("[executor] Skipping page %s: no layout name", page_key)
                continue
            page_number = int(page_key.replace("P", ""))
            page_name = str(layout)  # e.g., "01_cover"
            rhythm = page_rhythms.get(page_key, "dense")
            chart = page_charts.get(page_key)

            logger.info(
                "[executor] Generating page %s: %s (layout=%s, rhythm=%s)",
                page_key,
                page_name,
                layout,
                rhythm,
            )

            # Build previous pages summary for consistency
            prev_summary = "\n".join(
                f"- {p['page_key']}: {p['page_name']} ({p['layout']})"
                for p in svg_pages[-3:]  # Last 3 pages for context
            ) or "None (this is the first page)."

            # Extract page content from design spec
            page_content = _extract_page_content(design_spec, page_key, page_name)
            visual_elements = _extract_visual_elements(design_spec, page_key)
            special_instructions = _extract_special_instructions(
                design_spec, page_key
            )

            # Build prompt
            prompt = EXECUTOR_PAGE_PROMPT.format(
                design_spec=design_spec[:6000],
                spec_lock=json.dumps(spec_lock_parsed, indent=2)[:2000],
                page_number=page_number,
                page_name=page_name,
                page_rhythm=rhythm,
                page_layout=layout,
                page_chart=chart or "none",
                page_content=page_content,
                visual_elements=visual_elements,
                special_instructions=special_instructions,
                previous_pages_summary=prev_summary,
                viewbox=canvas_viewbox,
            )

            # Generate SVG
            svg_content = await llm.chat_completion(
                system_prompt=EXECUTOR_SYSTEM_PROMPT_BASE,
                user_prompt=prompt,
                temperature=0.5,
                max_tokens=4096,
            )

            # Clean SVG content
            svg_content = _clean_svg_content(svg_content)

            # Save to DB
            filename = f"{page_number:02d}_{page_name}.svg"
            svg_page_id = await _save_svg_page(
                project_id=project_id,
                page_number=page_number,
                page_name=page_name,
                svg_content=svg_content,
                filename=filename,
                page_rhythm=rhythm,
                page_layout=layout,
                page_chart=chart,
            )

            svg_pages.append(
                {
                    "page_key": page_key,
                    "page_number": page_number,
                    "page_name": page_name,
                    "layout": layout,
                    "filename": filename,
                    "svg_page_id": svg_page_id,
                }
            )

            # Generate speaker notes
            note_prompt = SPEAKER_NOTES_PROMPT.format(
                page_content=page_content,
                svg_summary=f"Page {page_number}: {page_name} with {layout} layout",
                page_number=page_number,
                total_pages=len(sorted_pages),
                presentation_title=config.get("name", "Presentation"),
            )
            note_content = await llm.chat_completion(
                system_prompt="You are a presentation coach.",
                user_prompt=note_prompt,
                temperature=0.7,
                max_tokens=512,
            )

            if svg_page_id:
                note_id = await _save_speaker_note(
                    project_id=project_id,
                    svg_page_id=svg_page_id,
                    page_number=page_number,
                    page_name=page_name,
                    note_content=note_content,
                )
                speaker_notes.append(
                    {
                        "page_number": page_number,
                        "note_id": note_id,
                        "content": note_content,
                    }
                )

            # Notify progress
            await _notify_ws(
                project_id,
                "step_change",
                {
                    "step": "executor",
                    "status": "running",
                    "progress": {
                        "current": page_number,
                        "total": len(sorted_pages),
                        "current_page": page_name,
                    },
                },
            )

        await llm.close()

        # Run quality check on all SVGs
        await _run_quality_check_batch(project_id)

        await _update_project_status(
            project_id, step_status=StepStatus.COMPLETED.value
        )
        if job_id:
            await _update_pipeline_job(
                job_id,
                status="completed",
                output_data={
                    "pages_generated": len(svg_pages),
                    "pages": svg_pages,
                },
            )

        await _notify_ws(
            project_id,
            "step_change",
            {"step": "executor", "status": "completed"},
        )

        return {
            "current_step": "executor",
            "step_status": StepStatus.COMPLETED.value,
            "svg_pages": svg_pages,
            "speaker_notes": speaker_notes,
        }

    except Exception as exc:
        logger.exception("[executor] Failed: %s", exc)
        await _update_project_status(project_id, error=str(exc))
        if job_id:
            await _update_pipeline_job(
                job_id,
                status="failed",
                error_message=str(exc),
            )
        return {
            "step_status": StepStatus.FAILED.value,
            "errors": [*state.get("errors", []), f"executor: {exc}"],
        }


async def post_processing_node(state: PPTPipelineState) -> dict[str, Any]:
    """
    Step 6: Finalize SVGs and export to PPTX.

    Runs finalize_svg.py for post-processing, then svg_to_pptx.py
    to produce the final export files.
    """
    project_id = state["project_id"]
    logger.info("[post_processing] Starting for project %s", project_id)

    await _update_project_status(
        project_id,
        step="post_processing",
        step_status=StepStatus.RUNNING.value,
    )
    job_id = await _create_pipeline_job(project_id, "post_processing")

    try:
        config = await _get_project_config(project_id)
        canvas_format = config.get("canvas_format", "ppt169")
        runner = ScriptRunner()
        storage = await _get_storage()

        exports: list[dict[str, Any]] = []

        async with ProjectWorkspace(
            project_id=project_id,
            db_session=None,  # Use internal sync helpers
            storage=storage,
            canvas_format=canvas_format,
        ) as ws:
            # Step 6a: Finalize SVGs
            logger.info("[post_processing] Running finalize_svg")
            await runner.run_finalize_svg(str(ws.path))

            # Step 6b: Split speaker notes
            logger.info("[post_processing] Running total_md_split")
            try:
                await runner.run_total_md_split(str(ws.path))
            except ScriptRunnerError:
                logger.warning("total_md_split not available or failed; continuing")

            # Step 6c: Export to PPTX
            logger.info("[post_processing] Running svg_to_pptx")
            export_options = {
                "format": canvas_format,
            }
            pptx_paths = await runner.run_svg_to_pptx(
                str(ws.path), export_options
            )

            for pptx_path in pptx_paths:
                filename = os.path.basename(pptx_path)
                storage_key = f"projects/{project_id}/exports/{filename}"

                if os.path.exists(pptx_path):
                    file_size = os.path.getsize(pptx_path)
                    with open(pptx_path, "rb") as f:
                        await storage.put(storage_key, f.read())

                    # Save to DB
                    async with _get_db_session() as db:
                        from app.models import PPTXExport
                        export = PPTXExport(
                            project_id=project_id,
                            filename=filename,
                            storage_key=storage_key,
                            file_size=file_size,
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

        await _update_project_status(
            project_id,
            step="post_processing",
            step_status=StepStatus.COMPLETED.value,
        )
        if job_id:
            await _update_pipeline_job(
                job_id,
                status="completed",
                output_data={"exports": exports},
            )

        await _notify_ws(
            project_id,
            "step_change",
            {"step": "post_processing", "status": "completed", "exports": exports},
        )

        return {
            "current_step": "post_processing",
            "step_status": StepStatus.COMPLETED.value,
            "exports": exports,
        }

    except Exception as exc:
        logger.exception("[post_processing] Failed: %s", exc)
        await _update_project_status(project_id, error=str(exc))
        if job_id:
            await _update_pipeline_job(
                job_id,
                status="failed",
                error_message=str(exc),
            )
        return {
            "step_status": StepStatus.FAILED.value,
            "errors": [*state.get("errors", []), f"post_processing: {exc}"],
        }


# ===================================================================
# Helper functions
# ===================================================================

def _extract_page_content(design_spec: str, page_key: str, page_name: str) -> str:
    """Extract the content outline for a specific page from the design spec."""
    # Simple heuristic: look for the page section
    lines = design_spec.splitlines()
    content_lines: list[str] = []
    in_section = False

    # Try multiple patterns to find the page section
    section_patterns = [
        f"**{page_key}",
        f"### {page_key}",
        f"## {page_key}",
        f"{page_key}:",
        f"{page_key} —",
        f"{page_key} -",
    ]
    if page_name:
        section_patterns.append(page_name)

    for i, line in enumerate(lines):
        # Check if we're entering the page section
        if not in_section:
            for pattern in section_patterns:
                if pattern and pattern.lower() in line.lower():
                    in_section = True
                    content_lines.append(line)
                    break
            continue

        # Check if we've reached the next page section
        if line.strip().startswith(("**P", "### P", "## P")):
            next_key = line.split()[0].replace("*", "").replace("#", "").strip(":")
            if next_key.startswith("P") and next_key != page_key:
                break

        content_lines.append(line)

    if content_lines:
        return "\n".join(content_lines[:50])  # Limit length

    # Fallback: return a generic outline
    return f"Content for {page_key} ({page_name}). Please create appropriate content based on the design spec."


def _extract_visual_elements(design_spec: str, page_key: str) -> str:
    """Extract visual element requirements for a page."""
    # Look for image/chart/icon requirements near the page section
    lines = design_spec.splitlines()
    elements: list[str] = []
    in_section = False

    for line in lines:
        if page_key in line:
            in_section = True
        elif in_section and line.strip().startswith("**P"):
            break

        if in_section and any(
            keyword in line.lower()
            for keyword in ["image", "chart", "icon", "photo", "diagram", "graph"]
        ):
            elements.append(line.strip())

    return "\n".join(elements) if elements else "No specific visual elements required."


def _extract_special_instructions(design_spec: str, page_key: str) -> str:
    """Extract special instructions for a page."""
    lines = design_spec.splitlines()
    instructions: list[str] = []
    in_section = False

    for line in lines:
        if page_key in line:
            in_section = True
        elif in_section and line.strip().startswith("**P"):
            break

        if in_section and any(
            keyword in line.lower()
            for keyword in ["special", "instruction", "note:", "important", "caution"]
        ):
            instructions.append(line.strip())

    return (
        "\n".join(instructions)
        if instructions
        else "Follow the design system consistently."
    )


def _clean_svg_content(svg_content: str) -> str:
    """Clean and validate SVG content from LLM response."""
    svg_content = svg_content.strip()

    # Remove markdown code fences if present
    if svg_content.startswith("```svg"):
        svg_content = svg_content[6:]
    elif svg_content.startswith("```xml"):
        svg_content = svg_content[6:]
    elif svg_content.startswith("```"):
        svg_content = svg_content[3:]
    if svg_content.endswith("```"):
        svg_content = svg_content[:-3]

    svg_content = svg_content.strip()

    # Ensure XML declaration
    if not svg_content.startswith("<?xml"):
        svg_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + svg_content

    # Ensure proper SVG namespace
    if "xmlns=" not in svg_content:
        svg_content = svg_content.replace(
            "<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1
        )

    return svg_content


async def _run_quality_check_batch(project_id: str) -> dict[str, Any]:
    """Run SVG quality checks on all pages for a project."""
    try:
        runner = ScriptRunner()
        async with ProjectWorkspace(
            project_id=project_id,
            db_session=None,
            storage=await _get_storage(),
        ) as ws:
            results = await runner.run_svg_quality_check(str(ws.path))
            logger.info("SVG quality check results: %s", results)

            # Update DB with results
            async with _get_db_session() as db:
                from app.models import SVGPage
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
                    if page:
                        passed = isinstance(check_result, dict) and check_result.get(
                            "passed", False
                        )
                        page.quality_check_status = (
                            "passed" if passed else "failed"
                        )
                        if isinstance(check_result, dict):
                            page.quality_check_errors = check_result.get("errors", [])
                            page.quality_check_warnings = check_result.get(
                                "warnings", []
                            )
                        await db.commit()

            return results
    except Exception as exc:
        logger.error("SVG quality check failed: %s", exc)
        return {"error": str(exc)}

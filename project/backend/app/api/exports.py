"""
PPT Master Web Service - PPT Export API Routes.

Handles PPTX export listing, download (via presigned URL), and re-export.
"""

from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    PaginationParams,
    get_current_project,
    get_db,
    get_db_ro,
    get_storage,
)
from app.core.schemas import (
    ErrorResponse,
    PPTXExportCreate,
    PPTXExportListResponse,
    PPTXExportResponse,
)
from app.models.pptx_export import PPTXExport
from app.models.project import Project
from app.services.storage_service import StorageBackend

router = APIRouter()


# ──── Routes ────


@router.get(
    "",
    response_model=PPTXExportListResponse,
    summary="List PPT exports",
    description="Get all PPTX export records for a project.",
)
async def list_exports(
    pagination: PaginationParams = Depends(),
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db_ro),
    storage: StorageBackend = Depends(get_storage),
) -> dict[str, Any]:
    """List PPTX exports for a project.

    Args:
        pagination: Pagination parameters.
        project: Resolved project dependency.
        db: Database session (read-only).
        storage: Storage backend.

    Returns:
        Paginated export list.
    """
    result = await db.execute(
        select(PPTXExport)
        .where(PPTXExport.project_id == project.id)
        .order_by(PPTXExport.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    exports = list(result.scalars().all())

    # Generate download URLs
    for export in exports:
        if export.storage_key:
            export.download_url = storage.get_url(export.storage_key, expires=3600)

    from sqlalchemy import func

    count_result = await db.execute(
        select(func.count(PPTXExport.id)).where(
            PPTXExport.project_id == project.id
        )
    )
    total = count_result.scalar() or 0
    pages = (total + pagination.page_size - 1) // pagination.page_size

    return {
        "items": exports,
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "pages": max(pages, 1),
    }


@router.get(
    "/{eid}",
    summary="Download PPT",
    description="Download a PPTX file. Redirects to a presigned download URL.",
    responses={
        307: {"description": "Redirect to presigned URL"},
        404: {"description": "Export not found", "model": ErrorResponse},
    },
)
async def download_export(
    eid: UUID,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db_ro),
    storage: StorageBackend = Depends(get_storage),
) -> RedirectResponse:
    """Download a PPTX export.

    Returns a redirect to a presigned URL for the file.

    Args:
        eid: Export ID.
        project: Resolved project dependency.
        db: Database session (read-only).
        storage: Storage backend.

    Returns:
        Redirect response to presigned URL.

    Raises:
        HTTPException: If export not found.
    """
    result = await db.execute(
        select(PPTXExport).where(
            PPTXExport.id == eid, PPTXExport.project_id == project.id
        )
    )
    export = result.scalar_one_or_none()
    if export is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export '{eid}' not found",
        )

    if not export.storage_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export file not available",
        )

    # Generate presigned URL and redirect
    presigned_url = storage.get_url(export.storage_key, expires=3600)
    return RedirectResponse(url=presigned_url)


@router.post(
    "",
    summary="Re-export PPT",
    description="Trigger a new PPTX export for the project.",
    responses={
        202: {"description": "Export task queued"},
        400: {"description": "Cannot export", "model": ErrorResponse},
        404: {"description": "Project not found", "model": ErrorResponse},
    },
)
async def create_export(
    data: PPTXExportCreate,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> dict[str, Any]:
    """Trigger a new PPTX export.

    Args:
        data: Export configuration.
        project: Resolved project dependency.
        db: Database session.
        storage: Storage backend.

    Returns:
        Export task info.
    """
    from app.core.celery_app import celery_app
    from app.core.schemas import JobStatus

    # Create export record
    export = PPTXExport(
        project_id=project.id,
        export_type=data.export_type.value,
        filename=f"{project.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx",
        storage_key="",  # Will be set by the Celery task
        storage_backend="minio",
        transition_effect=data.transition_effect,
        animation_effect=data.animation_effect,
    )
    db.add(export)
    await db.flush()

    # Enqueue export task
    task = celery_app.send_task(
        "app.services.pipeline.export_pptx",
        args=[str(project.id)],
        kwargs={
            "export_options": {
                "export_id": str(export.id),
                "export_type": data.export_type.value,
                "filename": export.filename,
                "transition_effect": data.transition_effect,
                "animation_effect": data.animation_effect,
            }
        },
        queue="script_tasks",
    )

    return {
        "message": "Export queued",
        "export_id": str(export.id),
        "task_id": task.id,
        "status": "queued",
    }


# Need this import
try:
    from datetime import datetime
except ImportError:
    pass

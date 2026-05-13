"""
PPT Master Web Service - Design Spec API Routes.

Handles Design Spec retrieval, Eight Confirmations, and spec updates.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_project, get_db, get_db_ro, get_storage
from app.core.schemas import (
    ConfirmationUpdate,
    ConfirmationsResponse,
    DesignSpecResponse,
    DesignSpecUpdate,
    ErrorResponse,
)
from app.models.project import Project
from app.services.design_spec_service import DesignSpecService
from app.services.storage_service import StorageBackend

router = APIRouter()


def _design_spec_service(
    db: AsyncSession, storage: StorageBackend
) -> DesignSpecService:
    return DesignSpecService(db=db, storage=storage)


# ──── Routes ────


@router.get(
    "",
    response_model=DesignSpecResponse,
    summary="Get Design Spec",
    description="Get the Design Spec for a project, including spec content and confirmations.",
    responses={
        404: {"description": "Project not found", "model": ErrorResponse},
    },
)
async def get_design_spec(
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db_ro),
    storage: StorageBackend = Depends(get_storage),
) -> Any:
    """Get the Design Spec for a project.

    Args:
        project: Resolved project dependency.
        db: Database session (read-only).
        storage: Storage backend.

    Returns:
        DesignSpec with confirmations data.
    """
    service = _design_spec_service(db, storage)
    spec = await service.get_or_create(project.id)

    # Load spec content from storage if needed
    spec_content = await service.get_spec_content(spec)

    return {
        "id": spec.id,
        "project_id": spec.project_id,
        "spec_content": spec_content,
        "spec_storage_key": spec.spec_storage_key,
        "confirmation_status": spec.confirmation_status,
        "confirmed_at": spec.confirmed_at,
        "confirmations": await service.get_confirmations(spec),
        "created_at": spec.created_at,
        "updated_at": spec.updated_at,
    }


@router.get(
    "/confirmations",
    response_model=ConfirmationsResponse,
    summary="Get Eight Confirmations",
    description="Get the Eight Confirmations data for a project.",
)
async def get_confirmations(
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db_ro),
    storage: StorageBackend = Depends(get_storage),
) -> Any:
    """Get Eight Confirmations for a project.

    Args:
        project: Resolved project dependency.
        db: Database session (read-only).
        storage: Storage backend.

    Returns:
        Confirmations data.
    """
    service = _design_spec_service(db, storage)
    spec = await service.get_or_create(project.id)
    confirmations = await service.get_confirmations(spec)

    return ConfirmationsResponse.model_validate(confirmations)


@router.post(
    "/confirm",
    summary="Confirm Eight Confirmations",
    description="Confirm the Eight Confirmations, allowing pipeline to proceed.",
    responses={
        200: {"description": "Confirmations saved and confirmed"},
        400: {"description": "Invalid state or missing fields", "model": ErrorResponse},
        404: {"description": "Project not found", "model": ErrorResponse},
    },
)
async def confirm_design_spec(
    data: ConfirmationUpdate,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> dict[str, Any]:
    """Confirm the Eight Confirmations.

    Updates confirmations data and sets status to 'confirmed'.
    This allows the pipeline to proceed past the strategist step.

    Args:
        data: Updated confirmation data.
        project: Resolved project dependency.
        db: Database session.
        storage: Storage backend.

    Returns:
        Confirmation result.
    """
    from app.core.schemas import ConfirmationStatus
    from app.services.project_service import ProjectService

    service = _design_spec_service(db, storage)
    spec = await service.get_or_create(project.id)

    # Update confirmation fields
    if any(v is not None for v in data.model_dump().values()):
        await service.update_confirmations(spec, data)

    # Confirm
    await service.confirm(spec)

    # Update project status if needed
    if project.status == "confirming":
        project_service = ProjectService(db=db, storage=storage)
        await project_service.set_status(project, project_service.__class__.__mro__[0])  # placeholder
        from app.core.schemas import ProjectStatus as PS
        project.status = PS.PROCESSING.value
        project.step_status = "pending"
        await db.flush()

    return {
        "message": "Eight Confirmations confirmed",
        "confirmation_status": ConfirmationStatus.CONFIRMED.value,
        "confirmed_at": spec.confirmed_at,
    }


@router.put(
    "",
    response_model=DesignSpecResponse,
    summary="Update Design Spec",
    description="Update the full Design Spec content (advanced use).",
)
async def update_design_spec(
    data: DesignSpecUpdate,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> Any:
    """Update the Design Spec.

    Args:
        data: Update data.
        project: Resolved project dependency.
        db: Database session.
        storage: Storage backend.

    Returns:
        Updated DesignSpec.
    """
    service = _design_spec_service(db, storage)
    spec = await service.get_or_create(project.id)
    updated = await service.update_spec(spec, data)

    spec_content = await service.get_spec_content(updated)

    return {
        "id": updated.id,
        "project_id": updated.project_id,
        "spec_content": spec_content,
        "spec_storage_key": updated.spec_storage_key,
        "confirmation_status": updated.confirmation_status,
        "confirmed_at": updated.confirmed_at,
        "confirmations": await service.get_confirmations(updated),
        "created_at": updated.created_at,
        "updated_at": updated.updated_at,
    }

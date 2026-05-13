"""
PPT Master Web Service - Image Resources API Routes.

Handles image resource listing, user uploads, and image configuration updates.
"""

from typing import Any, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
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
    ImageAcquireVia,
    ImageResourceListResponse,
    ImageResourceResponse,
    ImageResourceUpdate,
    ImageStatus,
    ImageType,
)
from app.models.image_resource import ImageResource
from app.models.project import Project
from app.services.storage_service import StorageBackend

router = APIRouter()


# ──── Routes ────


@router.get(
    "",
    response_model=ImageResourceListResponse,
    summary="List image resources",
    description="Get all image resources for a project.",
)
async def list_images(
    status_filter: Optional[ImageStatus] = Query(
        default=None, description="Filter by image status"
    ),
    image_type: Optional[ImageType] = Query(
        default=None, description="Filter by image type"
    ),
    pagination: PaginationParams = Depends(),
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db_ro),
    storage: StorageBackend = Depends(get_storage),
) -> dict[str, Any]:
    """List image resources for a project.

    Args:
        status_filter: Optional status filter.
        image_type: Optional image type filter.
        pagination: Pagination parameters.
        project: Resolved project dependency.
        db: Database session (read-only).
        storage: Storage backend.

    Returns:
        Paginated image resource list.
    """
    query = select(ImageResource).where(
        ImageResource.project_id == project.id
    )

    if status_filter:
        query = query.where(ImageResource.status == status_filter.value)
    if image_type:
        query = query.where(ImageResource.image_type == image_type.value)

    result = await db.execute(
        query.order_by(ImageResource.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    images = list(result.scalars().all())

    # Generate preview URLs
    for img in images:
        if img.storage_key:
            img.preview_url = storage.get_url(img.storage_key, expires=3600)

    from sqlalchemy import func

    count_query = select(func.count(ImageResource.id)).where(
        ImageResource.project_id == project.id
    )
    if status_filter:
        count_query = count_query.where(ImageResource.status == status_filter.value)
    if image_type:
        count_query = count_query.where(ImageResource.image_type == image_type.value)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    pages = (total + pagination.page_size - 1) // pagination.page_size

    return {
        "items": images,
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "pages": max(pages, 1),
    }


@router.post(
    "/upload",
    response_model=ImageResourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload image",
    description="Upload a user-provided image to use in the presentation.",
    responses={
        201: {"description": "Image uploaded successfully"},
        400: {"description": "Invalid image", "model": ErrorResponse},
        413: {"description": "File too large", "model": ErrorResponse},
    },
)
async def upload_image(
    file: UploadFile = File(..., description="Image file to upload"),
    purpose: Optional[str] = Form(
        default=None, description="Purpose of the image (e.g., 'background', 'content')"
    ),
    image_type: Optional[ImageType] = Form(
        default=None, description="Type of image"
    ),
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> Any:
    """Upload an image resource.

    Args:
        file: Uploaded image file.
        purpose: Image purpose description.
        image_type: Image classification.
        project: Resolved project dependency.
        db: Database session.
        storage: Storage backend.

    Returns:
        Created image resource record.

    Raises:
        HTTPException: If upload fails or file is invalid.
    """
    content = await file.read()

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    # 20MB limit for images
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image exceeds 20MB limit",
        )

    # Validate image type from content-type
    allowed_types = {
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/gif",
        "image/svg+xml",
        "image/webp",
    }
    content_type = file.content_type or "application/octet-stream"
    if content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type: {content_type}. Allowed: {', '.join(allowed_types)}",
        )

    # Create image resource
    image_id = uuid4()
    filename = file.filename or f"image_{image_id}.png"
    storage_key = storage.image_path(project.id, image_id, filename)

    # Upload to storage
    await storage.put(storage_key, content, content_type)

    image = ImageResource(
        id=image_id,
        project_id=project.id,
        filename=filename,
        purpose=purpose,
        image_type=image_type.value if image_type else None,
        acquire_via=ImageAcquireVia.USER.value,
        status=ImageStatus.EXISTING.value,
        storage_key=storage_key,
        storage_backend="minio",
        original_storage_key=storage_key,
    )
    db.add(image)
    await db.flush()
    await db.refresh(image)

    image.preview_url = storage.get_url(storage_key, expires=3600)
    return image


@router.put(
    "/{iid}",
    response_model=ImageResourceResponse,
    summary="Update image configuration",
    description="Update image resource metadata (purpose, type, prompt, etc.).",
    responses={
        404: {"description": "Image not found", "model": ErrorResponse},
    },
)
async def update_image(
    iid: UUID,
    data: ImageResourceUpdate,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> Any:
    """Update image resource configuration.

    Args:
        iid: Image resource ID.
        data: Update data.
        project: Resolved project dependency.
        db: Database session.
        storage: Storage backend.

    Returns:
        Updated image resource.

    Raises:
        HTTPException: If image not found.
    """
    result = await db.execute(
        select(ImageResource).where(
            ImageResource.id == iid, ImageResource.project_id == project.id
        )
    )
    image = result.scalar_one_or_none()
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image resource '{iid}' not found",
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(image, field, value.value if hasattr(value, "value") else value)

    await db.flush()
    await db.refresh(image)

    if image.storage_key:
        image.preview_url = storage.get_url(image.storage_key, expires=3600)

    return image

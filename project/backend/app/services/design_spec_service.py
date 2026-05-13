"""
PPT Master Web Service - Design Spec Service.

Handles Design Spec and Eight Confirmations CRUD operations.
Provides spec content management and confirmation workflows.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import (
    ConfirmationStatus,
    ConfirmationUpdate,
    DesignSpecUpdate,
)
from app.models.spec_lock import SpecLock
from app.models.design_spec import DesignSpec
from app.models.project import Project
from app.services.storage_service import StorageBackend


class DesignSpecService:
    """Service layer for Design Spec and Eight Confirmations management."""

    def __init__(self, db: AsyncSession, storage: StorageBackend) -> None:
        self.db = db
        self.storage = storage

    # ── DesignSpec CRUD ──

    async def get_or_create(self, project_id: UUID) -> DesignSpec:
        """Get existing DesignSpec or create a new one.

        Args:
            project_id: Project UUID.

        Returns:
            DesignSpec instance.
        """
        result = await self.db.execute(
            select(DesignSpec).where(DesignSpec.project_id == project_id)
        )
        spec = result.scalar_one_or_none()

        if spec is None:
            spec = DesignSpec(
                project_id=project_id,
                confirmation_status=ConfirmationStatus.PENDING.value,
            )
            self.db.add(spec)
            await self.db.flush()
            await self.db.refresh(spec)

        return spec

    async def get_by_project(self, project_id: UUID) -> Optional[DesignSpec]:
        """Get DesignSpec by project ID.

        Args:
            project_id: Project UUID.

        Returns:
            DesignSpec instance or None.
        """
        result = await self.db.execute(
            select(DesignSpec).where(DesignSpec.project_id == project_id)
        )
        return result.scalar_one_or_none()

    async def update_spec_content(
        self, spec: DesignSpec, content: str
    ) -> DesignSpec:
        """Update the full Design Spec markdown content.

        Args:
            spec: DesignSpec instance.
            content: Full markdown content.

        Returns:
            Updated DesignSpec.
        """
        spec.spec_content = content

        # Store to storage
        storage_key = self.storage.design_spec_path(spec.project_id)
        await self.storage.put(storage_key, content, "text/markdown")
        spec.spec_storage_key = storage_key

        await self.db.flush()
        await self.db.refresh(spec)
        return spec

    async def update_spec(
        self, spec: DesignSpec, data: DesignSpecUpdate
    ) -> DesignSpec:
        """Update Design Spec (advanced - full content update).

        Args:
            spec: DesignSpec instance.
            data: Update data.

        Returns:
            Updated DesignSpec.
        """
        if data.spec_content:
            return await self.update_spec_content(spec, data.spec_content)
        return spec

    # ── Eight Confirmations ──

    async def get_confirmations(
        self, spec: DesignSpec
    ) -> Dict[str, Any]:
        """Get Eight Confirmations data.

        Args:
            spec: DesignSpec instance.

        Returns:
            Dict of confirmation fields and status.
        """
        return {
            "confirmation_canvas": spec.confirmation_canvas,
            "confirmation_page_count": spec.confirmation_page_count,
            "confirmation_audience": spec.confirmation_audience,
            "confirmation_style_mode": spec.confirmation_style_mode,
            "confirmation_style_descriptor": spec.confirmation_style_descriptor,
            "confirmation_color_scheme": spec.confirmation_color_scheme,
            "confirmation_icon_approach": spec.confirmation_icon_approach,
            "confirmation_typography": spec.confirmation_typography,
            "confirmation_image_approach": spec.confirmation_image_approach,
            "confirmation_status": spec.confirmation_status,
            "confirmed_at": spec.confirmed_at,
        }

    async def update_confirmations(
        self, spec: DesignSpec, data: ConfirmationUpdate
    ) -> DesignSpec:
        """Update Eight Confirmations fields.

        Args:
            spec: DesignSpec instance.
            data: Confirmation update data.

        Returns:
            Updated DesignSpec.
        """
        update_fields = {
            "confirmation_canvas": data.confirmation_canvas,
            "confirmation_page_count": data.confirmation_page_count,
            "confirmation_audience": data.confirmation_audience,
            "confirmation_style_mode": data.confirmation_style_mode,
            "confirmation_style_descriptor": data.confirmation_style_descriptor,
            "confirmation_color_scheme": (
                data.confirmation_color_scheme.model_dump(mode="json")
                if data.confirmation_color_scheme
                else None
            ),
            "confirmation_icon_approach": data.confirmation_icon_approach,
            "confirmation_typography": (
                data.confirmation_typography.model_dump(mode="json")
                if data.confirmation_typography
                else None
            ),
            "confirmation_image_approach": data.confirmation_image_approach,
        }

        for field, value in update_fields.items():
            if value is not None:
                setattr(spec, field, value)

        await self.db.flush()
        await self.db.refresh(spec)
        return spec

    async def confirm(self, spec: DesignSpec) -> DesignSpec:
        """Confirm the Eight Confirmations.

        This transitions the confirmation status to 'confirmed' and
        sets the confirmed_at timestamp. Does NOT auto-regenerate spec.

        Args:
            spec: DesignSpec instance.

        Returns:
            Updated DesignSpec.
        """
        spec.confirmation_status = ConfirmationStatus.CONFIRMED.value
        spec.confirmed_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(spec)
        return spec

    async def is_confirmed(self, spec: DesignSpec) -> bool:
        """Check if confirmations have been confirmed.

        Args:
            spec: DesignSpec instance.

        Returns:
            True if confirmed.
        """
        return spec.confirmation_status == ConfirmationStatus.CONFIRMED.value

    # ── Spec Generation ──

    async def store_generated_spec(
        self,
        spec: DesignSpec,
        spec_content: str,
        confirmations: Dict[str, Any],
    ) -> DesignSpec:
        """Store a strategist-generated Design Spec.

        Args:
            spec: DesignSpec instance.
            spec_content: Generated markdown content.
            confirmations: Extracted confirmation fields.

        Returns:
            Updated DesignSpec.
        """
        # Store spec content
        spec.spec_content = spec_content
        storage_key = self.storage.design_spec_path(spec.project_id)
        await self.storage.put(storage_key, spec_content, "text/markdown")
        spec.spec_storage_key = storage_key

        # Store confirmations
        for field, value in confirmations.items():
            if hasattr(spec, field) and value is not None:
                setattr(spec, field, value)

        await self.db.flush()
        await self.db.refresh(spec)
        return spec

    # ── Spec Content Retrieval ──

    async def get_spec_content(self, spec: DesignSpec) -> Optional[str]:
        """Get the full Design Spec markdown content.

        Args:
            spec: DesignSpec instance.

        Returns:
            Markdown content or None.
        """
        if spec.spec_content:
            return spec.spec_content

        if spec.spec_storage_key:
            try:
                data = await self.storage.get(spec.spec_storage_key)
                content = data.decode("utf-8")
                spec.spec_content = content
                return content
            except Exception:
                pass

        return None

    # ── Spec Lock ──

    async def get_spec_lock(self, project_id: UUID) -> Optional[Any]:
        """Get SpecLock for a project.

        Args:
            project_id: Project UUID.

        Returns:
            SpecLock instance or None.
        """
        from app.models.spec_lock import SpecLock

        result = await self.db.execute(
            select(SpecLock).where(SpecLock.project_id == project_id)
        )
        return result.scalar_one_or_none()

    async def create_spec_lock(
        self, project_id: UUID, lock_data: Dict[str, Any]
    ) -> Any:
        """Create or update SpecLock from parsed data.

        Args:
            project_id: Project UUID.
            lock_data: Parsed lock data dict.

        Returns:
            Created/updated SpecLock.
        """
        from app.models.spec_lock import SpecLock

        result = await self.db.execute(
            select(SpecLock).where(SpecLock.project_id == project_id)
        )
        lock = result.scalar_one_or_none()

        if lock is None:
            lock = SpecLock(project_id=project_id)
            self.db.add(lock)

        # Update fields
        for field in [
            "canvas_viewbox",
            "canvas_format",
            "colors",
            "typography",
            "icons",
            "images",
            "page_rhythm",
            "page_layouts",
            "page_charts",
            "forbidden",
            "lock_content",
            "lock_storage_key",
        ]:
            if field in lock_data:
                setattr(lock, field, lock_data[field])

        await self.db.flush()
        await self.db.refresh(lock)
        return lock

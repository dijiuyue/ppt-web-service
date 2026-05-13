"""
PPT Master Pipeline - Temporary workspace management.

Provides an async context manager that creates a temporary working directory
mirroring the original PPT Master skill project structure, syncs files from
database/object storage on entry, and syncs results back on exit.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from app.pipeline.constants import (
    CANVAS_FORMATS,
    DEFAULT_CANVAS_FORMAT,
    WORKSPACE_BASE_DIR,
    WORKSPACE_MAX_AGE_HOURS,
)

logger = logging.getLogger(__name__)


class WorkspaceError(Exception):
    """Raised when workspace operations fail."""


class ProjectWorkspace:
    """
    Async context manager for a project's temporary working directory.

    On entry, creates a temp directory with the same structure as the
    original PPT Master skill and populates it from DB/object storage.
    On exit, uploads modified files back and cleans up.

    Expected directory layout (mirrors original skill)::

        {temp_dir}/
            design.md              # Source content (aggregated markdown)
            design_spec.md         # Full design specification
            spec_lock.md           # Machine-readable spec lock
            images/                # Image resources
                {filename}
            svg_output/            # Raw SVG pages from executor
                {NN}_{page_name}.svg
            svg_final/             # Post-processed SVG pages
                {NN}_{page_name}.svg
            notes/                 # Speaker notes
                total.md
                {NN}_{page_name}.md
            exports/               # PPTX exports
                {filename}.pptx
            sources/               # Original source files
                {filename}

    Usage::

        async with ProjectWorkspace(project_id, db_session, storage) as ws:
            # ws.path is the temp directory
            design_spec_path = ws.path / "design_spec.md"
            # ... do work ...
    """

    def __init__(
        self,
        project_id: str,
        db_session: Any | None = None,
        storage: Any | None = None,
        canvas_format: str = DEFAULT_CANVAS_FORMAT,
        base_dir: str | None = None,
    ) -> None:
        self.project_id = project_id
        self.db = db_session
        self.storage = storage
        self.canvas_format = canvas_format
        self.base_dir = base_dir or WORKSPACE_BASE_DIR

        self.path: Path = Path()
        self._temp_dir: str | None = None
        self._original_contents: set[str] = set()

    # -- Directory structure ------------------------------------------------

    @property
    def design_md_path(self) -> Path:
        """Path to the aggregated source content markdown."""
        return self.path / "design.md"

    @property
    def design_spec_path(self) -> Path:
        """Path to the design specification markdown."""
        return self.path / "design_spec.md"

    @property
    def spec_lock_path(self) -> Path:
        """Path to the spec lock markdown."""
        return self.path / "spec_lock.md"

    @property
    def images_dir(self) -> Path:
        """Directory for image resources."""
        return self.path / "images"

    @property
    def svg_output_dir(self) -> Path:
        """Directory for raw SVG output."""
        return self.path / "svg_output"

    @property
    def svg_final_dir(self) -> Path:
        """Directory for finalized SVG output."""
        return self.path / "svg_final"

    @property
    def notes_dir(self) -> Path:
        """Directory for speaker notes."""
        return self.path / "notes"

    @property
    def exports_dir(self) -> Path:
        """Directory for PPTX exports."""
        return self.path / "exports"

    @property
    def sources_dir(self) -> Path:
        """Directory for original source files."""
        return self.path / "sources"

    # -- Sub-path helpers ---------------------------------------------------

    def svg_output_file(self, page_number: int, page_name: str) -> Path:
        """Return the path for a raw SVG output file."""
        return self.svg_output_dir / f"{page_number:02d}_{page_name}.svg"

    def svg_final_file(self, page_number: int, page_name: str) -> Path:
        """Return the path for a finalized SVG file."""
        return self.svg_final_dir / f"{page_number:02d}_{page_name}.svg"

    def note_file(self, page_number: int, page_name: str) -> Path:
        """Return the path for a per-page speaker note file."""
        return self.notes_dir / f"{page_number:02d}_{page_name}.md"

    def notes_total_path(self) -> Path:
        """Return the path for the aggregated speaker notes file."""
        return self.notes_dir / "total.md"

    def image_file(self, filename: str) -> Path:
        """Return the path for an image resource file."""
        return self.images_dir / filename

    def export_file(self, filename: str) -> Path:
        """Return the path for an export file."""
        return self.exports_dir / filename

    def source_file(self, filename: str) -> Path:
        """Return the path for a source file."""
        return self.sources_dir / filename

    # -- Async context manager ----------------------------------------------

    async def __aenter__(self) -> "ProjectWorkspace":
        """
        Create the temporary workspace and sync files from storage.

        Returns:
            Self for use in ``async with`` blocks.
        """
        os.makedirs(self.base_dir, exist_ok=True)
        self._temp_dir = tempfile.mkdtemp(
            prefix=f"ppt_{self.project_id}_",
            dir=self.base_dir,
        )
        self.path = Path(self._temp_dir)
        logger.info(
            "Workspace created for project %s at %s",
            self.project_id,
            self.path,
        )

        # Create directory structure
        await self._create_directories()

        # Snapshot original contents for later diff
        self._original_contents = self._snapshot_contents()

        # Sync from storage if db/storage available
        if self.db is not None and self.storage is not None:
            try:
                await self.sync_from_storage()
            except Exception as exc:
                logger.warning(
                    "Failed to sync workspace from storage: %s", exc
                )

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """
        Sync modified files back to storage and clean up.

        Args are the standard exception info from the context.
        """
        try:
            if self.db is not None and self.storage is not None:
                try:
                    await self.sync_to_storage()
                except Exception as exc:
                    logger.error(
                        "Failed to sync workspace to storage: %s", exc
                    )
        finally:
            await self._cleanup()

    # -- Directory creation -------------------------------------------------

    async def _create_directories(self) -> None:
        """Create the standard project directory structure."""
        dirs = [
            self.images_dir,
            self.svg_output_dir,
            self.svg_final_dir,
            self.notes_dir,
            self.exports_dir,
            self.sources_dir,
        ]
        for d in dirs:
            await asyncio.to_thread(d.mkdir, parents=True, exist_ok=True)
            logger.debug("Created directory: %s", d)

    # -- Content snapshotting -----------------------------------------------

    def _snapshot_contents(self) -> set[str]:
        """Return a set of all file paths currently in the workspace."""
        files: set[str] = set()
        if self.path.exists():
            for f in self.path.rglob("*"):
                if f.is_file():
                    files.add(str(f.relative_to(self.path)))
        return files

    def get_modified_files(self) -> set[str]:
        """Return file paths that were added or modified since entry."""
        current = self._snapshot_contents()
        return current - self._original_contents

    # -- Storage sync -------------------------------------------------------

    async def sync_from_storage(self) -> None:
        """
        Download all project files from object storage into the workspace.

        Requires ``self.db`` (async DB session) and ``self.storage``
        (StorageBackend instance) to be set.
        """
        if not self.db or not self.storage:
            logger.debug("No DB or storage configured; skipping sync_from_storage")
            return

        logger.info("Syncing workspace FROM storage for project %s", self.project_id)

        # Import models here to avoid circular imports
        from app.models import DesignSpec, ImageResource, SourceFile, SpecLock, SVGPage

        try:
            # Sync source files
            result = await self.db.execute(
                SourceFile.select().where(SourceFile.project_id == self.project_id)
            )
            source_files = result.scalars().all()
            for sf in source_files:
                if sf.storage_key:
                    data = await self.storage.get(sf.storage_key)
                    dest = self.sources_dir / sf.original_filename
                    await asyncio.to_thread(dest.write_bytes, data)
                    logger.debug("Synced source: %s", dest)

                if sf.markdown_storage_key:
                    md_data = await self.storage.get(sf.markdown_storage_key)
                    md_dest = self.path / "design.md"
                    await asyncio.to_thread(md_dest.write_bytes, md_data)
                    logger.debug("Synced design.md from storage")

            # Sync design spec
            result = await self.db.execute(
                DesignSpec.select().where(DesignSpec.project_id == self.project_id)
            )
            design_spec = result.scalar_one_or_none()
            if design_spec and design_spec.spec_storage_key:
                spec_data = await self.storage.get(design_spec.spec_storage_key)
                await asyncio.to_thread(
                    self.design_spec_path.write_bytes, spec_data
                )
                logger.debug("Synced design_spec.md")

            # Sync spec lock
            result = await self.db.execute(
                SpecLock.select().where(SpecLock.project_id == self.project_id)
            )
            spec_lock = result.scalar_one_or_none()
            if spec_lock and spec_lock.lock_storage_key:
                lock_data = await self.storage.get(spec_lock.lock_storage_key)
                await asyncio.to_thread(
                    self.spec_lock_path.write_bytes, lock_data
                )
                logger.debug("Synced spec_lock.md")

            # Sync image resources
            result = await self.db.execute(
                ImageResource.select().where(
                    ImageResource.project_id == self.project_id
                )
            )
            images = result.scalars().all()
            for img in images:
                if img.storage_key:
                    img_data = await self.storage.get(img.storage_key)
                    img_dest = self.images_dir / img.filename
                    await asyncio.to_thread(img_dest.write_bytes, img_data)
                    logger.debug("Synced image: %s", img_dest)

            # Sync SVG pages
            result = await self.db.execute(
                SVGPage.select().where(SVGPage.project_id == self.project_id)
            )
            pages = result.scalars().all()
            for page in pages:
                if page.svg_storage_key:
                    svg_data = await self.storage.get(page.svg_storage_key)
                    svg_dest = self.svg_output_dir / page.filename
                    await asyncio.to_thread(svg_dest.write_bytes, svg_data)
                    logger.debug("Synced SVG: %s", svg_dest)

        except Exception as exc:
            raise WorkspaceError(f"sync_from_storage failed: {exc}") from exc

        logger.info("Workspace sync FROM storage completed")

    async def sync_to_storage(self) -> None:
        """
        Upload modified workspace files to object storage and update DB.

        Requires ``self.db`` (async DB session) and ``self.storage``
        (StorageBackend instance) to be set.
        """
        if not self.db or not self.storage:
            logger.debug("No DB or storage configured; skipping sync_to_storage")
            return

        logger.info("Syncing workspace TO storage for project %s", self.project_id)

        from app.models import DesignSpec, ImageResource, SVGPage

        try:
            modified = self.get_modified_files()
            logger.debug("Modified files: %s", modified)

            for rel_path in modified:
                abs_path = self.path / rel_path
                if not abs_path.exists():
                    continue

                storage_key = f"projects/{self.project_id}/{rel_path}"
                data = await asyncio.to_thread(abs_path.read_bytes)
                await self.storage.put(storage_key, data)
                logger.debug("Uploaded: %s → %s", rel_path, storage_key)

                # Update DB records for known file types
                await self._update_db_for_file(rel_path, storage_key)

        except Exception as exc:
            raise WorkspaceError(f"sync_to_storage failed: {exc}") from exc

        logger.info("Workspace sync TO storage completed")

    async def _update_db_for_file(
        self, rel_path: str, storage_key: str
    ) -> None:
        """Update the database record for a known file type."""
        from app.models import DesignSpec, SVGPage

        try:
            if rel_path == "design_spec.md":
                result = await self.db.execute(
                    DesignSpec.select().where(
                        DesignSpec.project_id == self.project_id
                    )
                )
                spec = result.scalar_one_or_none()
                if spec:
                    spec.spec_storage_key = storage_key
                    content = await asyncio.to_thread(
                        (self.path / rel_path).read_text, encoding="utf-8"
                    )
                    spec.spec_content = content
                    await self.db.commit()

            elif rel_path.startswith("svg_output/") and rel_path.endswith(".svg"):
                filename = Path(rel_path).name
                result = await self.db.execute(
                    SVGPage.select().where(
                        SVGPage.project_id == self.project_id,
                        SVGPage.filename == filename,
                    )
                )
                page = result.scalar_one_or_none()
                if page:
                    page.svg_storage_key = storage_key
                    content = await asyncio.to_thread(
                        (self.path / rel_path).read_text, encoding="utf-8"
                    )
                    page.svg_content = content
                    await self.db.commit()

        except Exception as exc:
            logger.warning("Failed to update DB for %s: %s", rel_path, exc)

    # -- Cleanup ------------------------------------------------------------

    async def _cleanup(self) -> None:
        """Remove the temporary directory."""
        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                await asyncio.to_thread(
                    shutil.rmtree, self._temp_dir, ignore_errors=True
                )
                logger.info(
                    "Workspace cleaned up: %s", self._temp_dir
                )
            except Exception as exc:
                logger.error("Failed to cleanup workspace: %s", exc)
            finally:
                self._temp_dir = None

    # -- Utility helpers ----------------------------------------------------

    def write_file(self, relative_path: str, content: str | bytes) -> Path:
        """
        Write content to a file within the workspace.

        Args:
            relative_path: Path relative to the workspace root.
            content: String or bytes to write.

        Returns:
            The absolute Path of the written file.
        """
        target = self.path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            target.write_text(content, encoding="utf-8")
        else:
            target.write_bytes(content)
        return target

    def read_file(self, relative_path: str) -> str:
        """
        Read text content from a file within the workspace.

        Args:
            relative_path: Path relative to the workspace root.

        Returns:
            File content as a string.
        """
        target = self.path / relative_path
        return target.read_text(encoding="utf-8")

    def read_file_bytes(self, relative_path: str) -> bytes:
        """Read raw bytes from a file within the workspace."""
        target = self.path / relative_path
        return target.read_bytes()

    def file_exists(self, relative_path: str) -> bool:
        """Check if a file exists within the workspace."""
        return (self.path / relative_path).exists()

    def list_files(self, relative_dir: str, pattern: str = "*") -> list[Path]:
        """
        List files in a workspace subdirectory.

        Args:
            relative_dir: Directory relative to workspace root.
            pattern: Glob pattern (default "*").

        Returns:
            List of Path objects.
        """
        target_dir = self.path / relative_dir
        if not target_dir.exists():
            return []
        return sorted(target_dir.glob(pattern))

    @staticmethod
    async def cleanup_old_workspaces(
        max_age_hours: int = WORKSPACE_MAX_AGE_HOURS,
    ) -> int:
        """
        Remove workspace directories older than ``max_age_hours``.

        Returns:
            Number of directories removed.
        """
        import time

        base = Path(WORKSPACE_BASE_DIR)
        if not base.exists():
            return 0

        cutoff = time.time() - (max_age_hours * 3600)
        removed = 0

        for entry in base.iterdir():
            if not entry.is_dir():
                continue
            try:
                mtime = entry.stat().st_mtime
                if mtime < cutoff:
                    await asyncio.to_thread(
                        shutil.rmtree, str(entry), ignore_errors=True
                    )
                    removed += 1
                    logger.info("Cleaned old workspace: %s", entry)
            except Exception as exc:
                logger.warning("Failed to clean %s: %s", entry, exc)

        return removed

"""
PPT Master Web Service - Source File Service.

Handles source file uploads, file type detection, conversion
status tracking, and integration with conversion scripts.
"""

import mimetypes
import os
from pathlib import Path
from typing import Any, BinaryIO, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import ConversionStatus, FileType, SourceUrlAdd
from app.models.project import Project
from app.models.source_file import SourceFile
from app.services.storage_service import StorageBackend


# ────────────────────────────────
# File Type Detection
# ────────────────────────────────

# Extension to FileType mapping
_EXTENSION_MAP: dict[str, FileType] = {
    ".pdf": FileType.PDF,
    ".docx": FileType.DOCX,
    ".xlsx": FileType.XLSX,
    ".pptx": FileType.PPTX,
    ".md": FileType.MD,
    ".txt": FileType.TXT,
    ".html": FileType.HTML,
    ".htm": FileType.HTML,
    ".epub": FileType.EPUB,
}

# MIME type to FileType mapping
_MIME_MAP: dict[str, FileType] = {
    "application/pdf": FileType.PDF,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": FileType.DOCX,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": FileType.XLSX,
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": FileType.PPTX,
    "text/markdown": FileType.MD,
    "text/plain": FileType.TXT,
    "text/html": FileType.HTML,
    "application/epub+zip": FileType.EPUB,
}


class SourceService:
    """Service layer for source file operations."""

    def __init__(self, db: AsyncSession, storage: StorageBackend) -> None:
        self.db = db
        self.storage = storage

    # ── File Type Detection ──

    @staticmethod
    def detect_file_type(
        filename: str, content_type: Optional[str] = None
    ) -> FileType:
        """Detect file type from filename and optional content type.

        Args:
            filename: Original filename.
            content_type: Optional MIME type.

        Returns:
            Detected FileType enum value.
        """
        # First try MIME type
        if content_type:
            clean_mime = content_type.split(";")[0].strip()
            if clean_mime in _MIME_MAP:
                return _MIME_MAP[clean_mime]

        # Fall back to extension
        ext = Path(filename).suffix.lower()
        if ext in _EXTENSION_MAP:
            return _EXTENSION_MAP[ext]

        # Default to txt for unknown types
        return FileType.TXT

    @staticmethod
    def is_binary_file(file_type: FileType) -> bool:
        """Check if file type is binary (needs conversion).

        Args:
            file_type: File type to check.

        Returns:
            True if binary conversion needed.
        """
        return file_type in {FileType.PDF, FileType.DOCX, FileType.XLSX, FileType.PPTX, FileType.EPUB}

    # ── Upload Operations ──

    async def upload_file(
        self,
        project: Project,
        filename: str,
        file_data: bytes,
        content_type: Optional[str] = None,
        sort_order: int = 0,
    ) -> SourceFile:
        """Upload and store a source file.

        Args:
            project: Parent project.
            filename: Original filename.
            file_data: File binary content.
            content_type: Optional MIME type.
            sort_order: Display order.

        Returns:
            Created SourceFile instance.
        """
        file_type = self.detect_file_type(filename, content_type)
        source_id = uuid4()
        storage_key = self.storage.source_path(project.id, source_id, filename)

        # Upload to storage
        await self.storage.put(
            storage_key, file_data, content_type or "application/octet-stream"
        )

        source_file = SourceFile(
            id=source_id,
            project_id=project.id,
            original_filename=filename,
            file_type=file_type.value,
            storage_key=storage_key,
            storage_backend="minio",
            file_size=len(file_data),
            conversion_status=ConversionStatus.PENDING.value
            if self.is_binary_file(file_type)
            else ConversionStatus.COMPLETED.value,
            sort_order=sort_order,
        )
        self.db.add(source_file)
        await self.db.flush()
        await self.db.refresh(source_file)

        # Trigger conversion for binary files
        if self.is_binary_file(file_type):
            await self.trigger_conversion(source_file)

        return source_file

    async def upload_multiple(
        self,
        project: Project,
        files: list[tuple[str, bytes, Optional[str]]],
    ) -> list[SourceFile]:
        """Upload multiple source files.

        Args:
            project: Parent project.
            files: List of (filename, file_data, content_type) tuples.

        Returns:
            List of created SourceFile instances.
        """
        source_files: list[SourceFile] = []
        for i, (filename, file_data, content_type) in enumerate(files):
            sf = await self.upload_file(
                project=project,
                filename=filename,
                file_data=file_data,
                content_type=content_type,
                sort_order=i,
            )
            source_files.append(sf)
        return source_files

    # ── URL Sources ──

    async def add_url_source(
        self, project: Project, data: SourceUrlAdd
    ) -> SourceFile:
        """Add a URL source (no file upload needed).

        Args:
            project: Parent project.
            data: URL source data.

        Returns:
            Created SourceFile instance.
        """
        source_id = uuid4()
        storage_key = self.storage.source_path(
            project.id, source_id, "source.txt"
        )

        # Store the URL as content
        url_content = f"# URL Source\n\n{data.url}"
        if data.title:
            url_content = f"# {data.title}\n\n{data.url}"

        await self.storage.put(storage_key, url_content, "text/plain")

        source_file = SourceFile(
            id=source_id,
            project_id=project.id,
            original_filename=data.title or data.url,
            file_type=FileType.URL.value,
            storage_key=storage_key,
            storage_backend="minio",
            file_size=len(url_content.encode("utf-8")),
            conversion_status=ConversionStatus.COMPLETED.value,
            sort_order=data.sort_order,
        )
        self.db.add(source_file)
        await self.db.flush()
        await self.db.refresh(source_file)
        return source_file

    # ── Query Operations ──

    async def get_by_id(self, source_id: UUID) -> Optional[SourceFile]:
        """Get source file by ID.

        Args:
            source_id: Source file UUID.

        Returns:
            SourceFile instance or None.
        """
        result = await self.db.execute(
            select(SourceFile).where(SourceFile.id == source_id)
        )
        return result.scalar_one_or_none()

    async def get_list(
        self, project_id: UUID, offset: int = 0, limit: int = 100
    ) -> tuple[List[SourceFile], int]:
        """Get source files for a project.

        Args:
            project_id: Project UUID.
            offset: Query offset.
            limit: Query limit.

        Returns:
            Tuple of (source files, total count).
        """
        from sqlalchemy import func

        result = await self.db.execute(
            select(SourceFile)
            .where(SourceFile.project_id == project_id)
            .order_by(SourceFile.sort_order, SourceFile.created_at)
            .offset(offset)
            .limit(limit)
        )
        files = list(result.scalars().all())

        count_result = await self.db.execute(
            select(func.count(SourceFile.id)).where(
                SourceFile.project_id == project_id
            )
        )
        total = count_result.scalar() or 0

        return files, total

    # ── Delete ──

    async def delete(self, source_file: SourceFile) -> None:
        """Delete a source file and its storage.

        Args:
            source_file: SourceFile to delete.
        """
        # Remove from storage
        try:
            await self.storage.delete(source_file.storage_key)
            if source_file.markdown_storage_key:
                await self.storage.delete(source_file.markdown_storage_key)
        except Exception:
            pass  # Best-effort cleanup

        await self.db.delete(source_file)
        await self.db.flush()

    # ── Conversion ──

    async def trigger_conversion(self, source_file: SourceFile) -> None:
        """Trigger markdown conversion for a binary source file.

        This enqueues a Celery task to convert the file.

        Args:
            source_file: SourceFile to convert.
        """
        from app.core.celery_app import celery_app

        source_file.conversion_status = ConversionStatus.PROCESSING.value
        await self.db.flush()

        # Enqueue conversion task
        celery_app.send_task(
            "app.services.pipeline.process_source_file",
            args=[str(source_file.id)],
            queue="script_tasks",
        )

    async def update_conversion_status(
        self,
        source_file: SourceFile,
        status: ConversionStatus,
        markdown_content: Optional[str] = None,
        error: Optional[str] = None,
    ) -> SourceFile:
        """Update conversion status and result.

        Args:
            source_file: SourceFile to update.
            status: New conversion status.
            markdown_content: Converted markdown content.
            error: Error message if failed.

        Returns:
            Updated SourceFile.
        """
        source_file.conversion_status = status.value

        if status == ConversionStatus.COMPLETED and markdown_content:
            # Store converted markdown
            md_key = self.storage.source_converted_path(
                source_file.project_id, source_file.id
            )
            await self.storage.put(md_key, markdown_content, "text/markdown")
            source_file.markdown_content = markdown_content
            source_file.markdown_storage_key = md_key
        elif status == ConversionStatus.FAILED and error:
            source_file.conversion_error = error

        await self.db.flush()
        await self.db.refresh(source_file)
        return source_file

    # ── Content Access ──

    async def get_source_content(self, source_file: SourceFile) -> Optional[str]:
        """Get the markdown content of a source file.

        Args:
            source_file: SourceFile to read.

        Returns:
            Markdown content string or None.
        """
        # If already converted, return from DB
        if source_file.markdown_content:
            return source_file.markdown_content

        # Try to fetch from storage
        if source_file.markdown_storage_key:
            try:
                data = await self.storage.get(source_file.markdown_storage_key)
                return data.decode("utf-8")
            except Exception:
                pass

        # For text-based files, read from original
        if source_file.file_type in {
            FileType.MD.value,
            FileType.TXT.value,
            FileType.URL.value,
            FileType.HTML.value,
        }:
            try:
                data = await self.storage.get(source_file.storage_key)
                return data.decode("utf-8")
            except Exception:
                pass

        return None

    async def get_combined_source_content(self, project_id: UUID) -> str:
        """Get combined markdown content from all sources for a project.

        Args:
            project_id: Project UUID.

        Returns:
            Combined markdown string.
        """
        files, _ = await self.get_list(project_id)
        contents: list[str] = []

        for sf in files:
            content = await self.get_source_content(sf)
            if content:
                contents.append(f"# {sf.original_filename}\n\n{content}")

        return "\n\n---\n\n".join(contents)

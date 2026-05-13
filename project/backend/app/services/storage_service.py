"""
PPT Master Web Service - Storage Abstraction Layer.

Provides abstract StorageBackend and concrete implementations for MinIO/S3
and local filesystem storage. Includes presigned URL generation and path helpers.
"""

import hashlib
import os
import shutil
from abc import ABC, abstractmethod
from datetime import timedelta
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

# Optional MinIO import
try:
    from minio import Minio
    from minio.error import S3Error
    HAS_MINIO = True
except ImportError:
    HAS_MINIO = False

# ────────────────────────────────
# Abstract Backend
# ────────────────────────────────


class StorageBackend(ABC):
    """Abstract storage backend interface."""

    @abstractmethod
    async def put(
        self, key: str, data: bytes | str, content_type: str = "application/octet-stream"
    ) -> str:
        """Store data at the given key. Returns the storage key."""
        ...

    @abstractmethod
    async def get(self, key: str) -> bytes:
        """Retrieve data by key."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete data by key."""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        ...

    @abstractmethod
    def get_url(self, key: str, expires: int = 3600) -> str:
        """Get presigned URL for temporary access."""
        ...

    @abstractmethod
    def get_public_url(self, key: str) -> str:
        """Get public URL (if supported)."""
        ...

    # ── Path Helpers ──

    @staticmethod
    def source_path(project_id: UUID | str, source_id: UUID | str, filename: str) -> str:
        return f"projects/{project_id}/sources/{source_id}/{filename}"

    @staticmethod
    def source_converted_path(project_id: UUID | str, source_id: UUID | str) -> str:
        return f"projects/{project_id}/sources/{source_id}/converted.md"

    @staticmethod
    def image_path(project_id: UUID | str, image_id: UUID | str, filename: str) -> str:
        return f"projects/{project_id}/images/{image_id}/{filename}"

    @staticmethod
    def design_spec_path(project_id: UUID | str) -> str:
        return f"projects/{project_id}/design_spec.md"

    @staticmethod
    def spec_lock_path(project_id: UUID | str) -> str:
        return f"projects/{project_id}/spec_lock.md"

    @staticmethod
    def svg_page_path(project_id: UUID | str, page_number: int, page_name: str) -> str:
        filename = f"{page_number:02d}_{page_name}.svg"
        return f"projects/{project_id}/svg_output/{filename}"

    @staticmethod
    def svg_final_path(project_id: UUID | str, page_number: int, page_name: str) -> str:
        filename = f"{page_number:02d}_{page_name}.svg"
        return f"projects/{project_id}/svg_final/{filename}"

    @staticmethod
    def notes_path(project_id: UUID | str) -> str:
        return f"projects/{project_id}/notes/total.md"

    @staticmethod
    def note_page_path(project_id: UUID | str, page_number: int, page_name: str) -> str:
        filename = f"{page_number:02d}_{page_name}.md"
        return f"projects/{project_id}/notes/{filename}"

    @staticmethod
    def export_path(project_id: UUID | str, export_id: UUID | str, filename: str) -> str:
        return f"projects/{project_id}/exports/{export_id}/{filename}"

    @staticmethod
    def template_path(project_id: UUID | str) -> str:
        return f"projects/{project_id}/templates/"


# ────────────────────────────────
# MinIO Backend
# ────────────────────────────────


class MinioStorage(StorageBackend):
    """MinIO/S3 storage backend for production."""

    def __init__(
        self,
        endpoint: str = "localhost:9000",
        access_key: str = "minioadmin",
        secret_key: str = "minioadmin",
        bucket: str = "pptmaster",
        secure: bool = False,
    ) -> None:
        if not HAS_MINIO:
            raise ImportError("MinIO SDK not installed. Run: pip install minio")

        self.endpoint = endpoint
        self.bucket = bucket
        self.secure = secure
        self._client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Create bucket if it doesn't exist."""
        try:
            if not self._client.bucket_exists(self.bucket):
                self._client.make_bucket(self.bucket)
        except S3Error as exc:
            raise RuntimeError(f"Failed to ensure MinIO bucket: {exc}") from exc

    async def put(
        self, key: str, data: bytes | str, content_type: str = "application/octet-stream"
    ) -> str:
        if isinstance(data, str):
            data = data.encode("utf-8")
        from io import BytesIO

        stream = BytesIO(data)
        try:
            self._client.put_object(
                self.bucket,
                key,
                stream,
                length=len(data),
                content_type=content_type,
            )
        except S3Error as exc:
            raise RuntimeError(f"Failed to upload {key}: {exc}") from exc
        return key

    async def get(self, key: str) -> bytes:
        try:
            response = self._client.get_object(self.bucket, key)
            return response.read()
        except S3Error as exc:
            raise FileNotFoundError(f"Object not found: {key}") from exc

    async def delete(self, key: str) -> None:
        try:
            self._client.remove_object(self.bucket, key)
        except S3Error:
            pass  # Already deleted

    async def exists(self, key: str) -> bool:
        try:
            self._client.stat_object(self.bucket, key)
            return True
        except S3Error:
            return False

    def get_url(self, key: str, expires: int = 3600) -> str:
        """Generate presigned URL for temporary access."""
        try:
            return self._client.presigned_get_object(
                self.bucket, key, expires=timedelta(seconds=expires)
            )
        except S3Error as exc:
            raise RuntimeError(f"Failed to generate presigned URL: {exc}") from exc

    def get_public_url(self, key: str) -> str:
        scheme = "https" if self.secure else "http"
        return f"{scheme}://{self.endpoint}/{self.bucket}/{key}"


# ────────────────────────────────
# Local Filesystem Backend
# ────────────────────────────────


class LocalStorage(StorageBackend):
    """Local filesystem storage backend for development."""

    def __init__(self, base_dir: str = "./storage") -> None:
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _full_path(self, key: str) -> Path:
        # Security: prevent path traversal
        safe_key = key.replace("..", ".").lstrip("/")
        path = self.base_dir / safe_key
        # Ensure the path is under base_dir
        try:
            path.resolve().relative_to(self.base_dir)
        except ValueError as exc:
            raise ValueError(f"Invalid storage key: {key}") from exc
        return path

    async def put(
        self, key: str, data: bytes | str, content_type: str = "application/octet-stream"
    ) -> str:
        path = self._full_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        mode = "w" if isinstance(data, str) else "wb"
        encoding = "utf-8" if isinstance(data, str) else None
        with open(path, mode, encoding=encoding) as f:
            f.write(data)
        return key

    async def get(self, key: str) -> bytes:
        path = self._full_path(key)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {key}")
        return path.read_bytes()

    async def delete(self, key: str) -> None:
        path = self._full_path(key)
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)

    async def exists(self, key: str) -> bool:
        return self._full_path(key).exists()

    def get_url(self, key: str, expires: int = 3600) -> str:
        # Local storage doesn't support presigned URLs, return file path
        return f"/storage/{key}"

    def get_public_url(self, key: str) -> str:
        return f"/storage/{key}"


# ────────────────────────────────
# Storage Factory
# ────────────────────────────────


class StorageManager:
    """Manages storage backend selection and lifecycle."""

    _instance: Optional[StorageBackend] = None

    @classmethod
    def initialize(cls, backend_type: str = "local", **kwargs: Any) -> StorageBackend:
        """Initialize the storage backend singleton."""
        if cls._instance is None:
            if backend_type == "minio":
                cls._instance = MinioStorage(**kwargs)
            elif backend_type == "local":
                cls._instance = LocalStorage(**kwargs)
            else:
                raise ValueError(f"Unknown storage backend: {backend_type}")
        return cls._instance

    @classmethod
    def get(cls) -> StorageBackend:
        """Get the current storage backend instance."""
        if cls._instance is None:
            raise RuntimeError("Storage backend not initialized. Call initialize() first.")
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (for testing)."""
        cls._instance = None


def get_storage_backend() -> StorageBackend:
    """Get the configured storage backend.

    Reads STORAGE_BACKEND env var to determine which backend to use.
    """
    backend_type = os.getenv("STORAGE_BACKEND", "local")
    if backend_type == "minio":
        kwargs = {
            "endpoint": os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            "access_key": os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            "secret_key": os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            "bucket": os.getenv("MINIO_BUCKET", "pptmaster"),
            "secure": os.getenv("MINIO_SECURE", "false").lower() == "true",
        }
    else:
        kwargs = {"base_dir": os.getenv("LOCAL_STORAGE_DIR", "./storage")}

    return StorageManager.initialize(backend_type=backend_type, **kwargs)

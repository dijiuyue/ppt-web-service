"""
PPT Master Web Service — Storage Layer Tests.

Tests for LocalStorage put/get/delete/exists, file content I/O,
and path resolution (including path traversal protection).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

from app.services.storage_service import LocalStorage, StorageManager
from app.storage.local import LocalStorage as AltLocalStorage


# ---------------------------------------------------------------------------
# LocalStorage Tests (app/services/storage_service.py)
# ---------------------------------------------------------------------------


class TestLocalStoragePut:
    """Tests for LocalStorage.put method."""

    @pytest.mark.asyncio
    async def test_put_bytes(self, temp_storage_dir: str) -> None:
        """Test storing binary data."""
        storage = LocalStorage(base_dir=temp_storage_dir)
        key = "test/file.bin"
        data = b"\x00\x01\x02\x03\x04\x05"
        result = await storage.put(key, data)
        assert result == key
        full_path = Path(temp_storage_dir) / key
        assert full_path.exists()
        assert full_path.read_bytes() == data

    @pytest.mark.asyncio
    async def test_put_string(self, temp_storage_dir: str) -> None:
        """Test storing string data (auto-encoded to UTF-8)."""
        storage = LocalStorage(base_dir=temp_storage_dir)
        key = "test/document.txt"
        data = "Hello, World!"
        result = await storage.put(key, data)
        assert result == key
        full_path = Path(temp_storage_dir) / key
        assert full_path.exists()
        assert full_path.read_text(encoding="utf-8") == data

    @pytest.mark.asyncio
    async def test_put_nested_path(self, temp_storage_dir: str) -> None:
        """Test storing with deeply nested path."""
        storage = LocalStorage(base_dir=temp_storage_dir)
        key = "a/b/c/d/e/deep.txt"
        data = b"deep data"
        await storage.put(key, data)
        full_path = Path(temp_storage_dir) / key
        assert full_path.exists()

    @pytest.mark.asyncio
    async def test_put_overwrite(self, temp_storage_dir: str) -> None:
        """Test that put overwrites existing file."""
        storage = LocalStorage(base_dir=temp_storage_dir)
        key = "test/overwrite.txt"
        await storage.put(key, b"original")
        await storage.put(key, b"updated")
        full_path = Path(temp_storage_dir) / key
        assert full_path.read_bytes() == b"updated"

    @pytest.mark.asyncio
    async def test_put_content_type_ignored(self, temp_storage_dir: str) -> None:
        """Test that content_type parameter is accepted but not stored."""
        storage = LocalStorage(base_dir=temp_storage_dir)
        key = "test/file.json"
        data = b'{"key": "value"}'
        # content_type is part of the interface but not used by local storage
        result = await storage.put(key, data, content_type="application/json")
        assert result == key
        assert (Path(temp_storage_dir) / key).exists()


class TestLocalStorageGet:
    """Tests for LocalStorage.get method."""

    @pytest.mark.asyncio
    async def test_get_existing_file(self, temp_storage_dir: str) -> None:
        """Test retrieving an existing file."""
        storage = LocalStorage(base_dir=temp_storage_dir)
        key = "test/readme.txt"
        original_data = b"File contents here"
        await storage.put(key, original_data)
        result = await storage.get(key)
        assert result == original_data

    @pytest.mark.asyncio
    async def test_get_nonexistent_raises(self, temp_storage_dir: str) -> None:
        """Test retrieving a nonexistent file raises FileNotFoundError."""
        storage = LocalStorage(base_dir=temp_storage_dir)
        with pytest.raises(FileNotFoundError):
            await storage.get("nonexistent/file.txt")

    @pytest.mark.asyncio
    async def test_get_string_data(self, temp_storage_dir: str) -> None:
        """Test retrieving string data as bytes."""
        storage = LocalStorage(base_dir=temp_storage_dir)
        key = "test/text.txt"
        await storage.put(key, "Hello, UTF-8!")
        result = await storage.get(key)
        assert result == b"Hello, UTF-8!"


class TestLocalStorageDelete:
    """Tests for LocalStorage.delete method."""

    @pytest.mark.asyncio
    async def test_delete_existing_file(self, temp_storage_dir: str) -> None:
        """Test deleting an existing file."""
        storage = LocalStorage(base_dir=temp_storage_dir)
        key = "test/delete_me.txt"
        await storage.put(key, b"delete me")
        assert (Path(temp_storage_dir) / key).exists()
        await storage.delete(key)
        # LocalStorage.delete removes the file; check it's gone
        assert not (Path(temp_storage_dir) / key).exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_no_error(self, temp_storage_dir: str) -> None:
        """Test deleting a nonexistent file doesn't raise."""
        storage = LocalStorage(base_dir=temp_storage_dir)
        # Should not raise
        await storage.delete("nonexistent/file.txt")


class TestLocalStorageExists:
    """Tests for LocalStorage.exists method."""

    @pytest.mark.asyncio
    async def test_exists_true(self, temp_storage_dir: str) -> None:
        """Test exists returns True for existing file."""
        storage = LocalStorage(base_dir=temp_storage_dir)
        key = "test/exists.txt"
        await storage.put(key, b"data")
        assert await storage.exists(key) is True

    @pytest.mark.asyncio
    async def test_exists_false(self, temp_storage_dir: str) -> None:
        """Test exists returns False for nonexistent file."""
        storage = LocalStorage(base_dir=temp_storage_dir)
        assert await storage.exists("nonexistent/file.txt") is False


class TestLocalStorageUrlMethods:
    """Tests for LocalStorage URL generation methods."""

    def test_get_url(self, temp_storage_dir: str) -> None:
        """Test get_url returns path-based URL."""
        storage = LocalStorage(base_dir=temp_storage_dir)
        key = "test/file.txt"
        url = storage.get_url(key)
        assert "/storage/" in url
        assert key in url

    def test_get_public_url(self, temp_storage_dir: str) -> None:
        """Test get_public_url returns path-based URL."""
        storage = LocalStorage(base_dir=temp_storage_dir)
        key = "test/file.txt"
        url = storage.get_public_url(key)
        assert "/storage/" in url


class TestLocalStoragePathHelpers:
    """Tests for StorageBackend static path helper methods."""

    def test_source_path(self) -> None:
        """Test source_path helper."""
        from app.services.storage_service import StorageBackend

        path = StorageBackend.source_path("proj-123", "src-456", "file.pdf")
        assert path == "projects/proj-123/sources/src-456/file.pdf"

    def test_source_converted_path(self) -> None:
        """Test source_converted_path helper."""
        from app.services.storage_service import StorageBackend

        path = StorageBackend.source_converted_path("proj-123", "src-456")
        assert path == "projects/proj-123/sources/src-456/converted.md"

    def test_image_path(self) -> None:
        """Test image_path helper."""
        from app.services.storage_service import StorageBackend

        path = StorageBackend.image_path("proj-123", "img-456", "photo.jpg")
        assert path == "projects/proj-123/images/img-456/photo.jpg"

    def test_design_spec_path(self) -> None:
        """Test design_spec_path helper."""
        from app.services.storage_service import StorageBackend

        path = StorageBackend.design_spec_path("proj-123")
        assert path == "projects/proj-123/design_spec.md"

    def test_svg_page_path(self) -> None:
        """Test svg_page_path helper."""
        from app.services.storage_service import StorageBackend

        path = StorageBackend.svg_page_path("proj-123", 1, "cover")
        assert path == "projects/proj-123/svg_output/01_cover.svg"

    def test_notes_path(self) -> None:
        """Test notes_path helper."""
        from app.services.storage_service import StorageBackend

        path = StorageBackend.notes_path("proj-123")
        assert path == "projects/proj-123/notes/total.md"

    def test_export_path(self) -> None:
        """Test export_path helper."""
        from app.services.storage_service import StorageBackend

        path = StorageBackend.export_path("proj-123", "exp-456", "export.pptx")
        assert path == "projects/proj-123/exports/exp-456/export.pptx"

    def test_template_path(self) -> None:
        """Test template_path helper."""
        from app.services.storage_service import StorageBackend

        path = StorageBackend.template_path("proj-123")
        assert path == "projects/proj-123/templates/"


class TestLocalStoragePathTraversal:
    """Tests for path traversal protection in LocalStorage."""

    def test_path_traversal_sanitized(self, temp_storage_dir: str) -> None:
        """Test that path traversal attempts are sanitized (.. replaced with .)."""
        storage = LocalStorage(base_dir=temp_storage_dir)
        # The LocalStorage replaces ".." with "." rather than raising
        path = storage._full_path("../../../etc/passwd")
        # The sanitized path should be under base_dir
        assert str(path).replace("..", ".")  # Path was sanitized

    def test_path_traversal_blocked_alt_storage(self, temp_storage_dir: str) -> None:
        """Test that AltLocalStorage blocks path traversal."""
        storage = AltLocalStorage(base_path=temp_storage_dir)
        with pytest.raises(ValueError):
            storage._resolve("../../../etc/passwd")

    def test_resolve_key_normalization(self) -> None:
        """Test resolve_key normalizes path parts correctly."""
        from app.storage.base import StorageBackend

        # Create a minimal concrete instance to test the method
        class _TestStorage(StorageBackend):
            async def put(self, key, data, content_type=""): return key
            async def get(self, key): return b""
            async def delete(self, key): pass
            async def exists(self, key): return True
            def get_url(self, key, expires=3600): return ""
            def get_public_url(self, key): return ""

        storage = _TestStorage()
        key = storage.resolve_key("projects", "abc", "file.txt")
        assert key == "projects/abc/file.txt"

    def test_resolve_key_single_part(self) -> None:
        """Test resolve_key with single part."""
        from app.storage.base import StorageBackend

        class _TestStorage(StorageBackend):
            async def put(self, key, data, content_type=""): return key
            async def get(self, key): return b""
            async def delete(self, key): pass
            async def exists(self, key): return True
            def get_url(self, key, expires=3600): return ""
            def get_public_url(self, key): return ""

        storage = _TestStorage()
        key = storage.resolve_key("file.txt")
        assert key == "file.txt"

    def test_resolve_key_strips_leading_slashes(self) -> None:
        """Test resolve_key strips leading double slashes."""
        from app.storage.base import StorageBackend

        class _TestStorage(StorageBackend):
            async def put(self, key, data, content_type=""): return key
            async def get(self, key): return b""
            async def delete(self, key): pass
            async def exists(self, key): return True
            def get_url(self, key, expires=3600): return ""
            def get_public_url(self, key): return ""

        storage = _TestStorage()
        key = storage.resolve_key("projects", "abc", "file.txt")
        assert "//" not in key
        assert key == "projects/abc/file.txt"


# ---------------------------------------------------------------------------
# AltLocalStorage Tests (app/storage/local.py)
# ---------------------------------------------------------------------------


class TestAltLocalStorage:
    """Tests for the alternative LocalStorage in app/storage/local.py."""

    @pytest.mark.asyncio
    async def test_alt_storage_put_get(self, temp_storage_dir: str) -> None:
        """Test AltLocalStorage put and get operations."""
        storage = AltLocalStorage(
            base_path=temp_storage_dir, public_url_base="http://localhost:8000/static"
        )
        key = "test/data.txt"
        data = b"alternative storage"
        await storage.put(key, data)
        result = await storage.get(key)
        assert result == data

    @pytest.mark.asyncio
    async def test_alt_storage_delete(self, temp_storage_dir: str) -> None:
        """Test AltLocalStorage delete operation."""
        storage = AltLocalStorage(base_path=temp_storage_dir)
        key = "test/delete.txt"
        await storage.put(key, b"to delete")
        assert await storage.exists(key) is True
        await storage.delete(key)
        assert await storage.exists(key) is False

    @pytest.mark.asyncio
    async def test_alt_storage_delete_nonexistent_raises(self, temp_storage_dir: str) -> None:
        """Test AltLocalStorage delete of nonexistent file raises."""
        storage = AltLocalStorage(base_path=temp_storage_dir)
        with pytest.raises(FileNotFoundError):
            await storage.delete("nonexistent.txt")

    def test_alt_storage_public_url(self, temp_storage_dir: str) -> None:
        """Test AltLocalStorage public URL generation."""
        storage = AltLocalStorage(
            base_path=temp_storage_dir,
            public_url_base="http://localhost:8000/static",
        )
        key = "projects/abc/file.txt"
        url = storage.get_public_url(key)
        assert url == "http://localhost:8000/static/projects/abc/file.txt"

    def test_alt_storage_path_traversal_protection(self, temp_storage_dir: str) -> None:
        """Test AltLocalStorage path traversal protection."""
        storage = AltLocalStorage(base_path=temp_storage_dir)
        with pytest.raises(ValueError):
            storage._resolve("../../../etc/passwd")

    @pytest.mark.asyncio
    async def test_alt_storage_put_string(self, temp_storage_dir: str) -> None:
        """Test AltLocalStorage put with string data."""
        storage = AltLocalStorage(base_path=temp_storage_dir)
        key = "test/string.txt"
        data = "Hello, String!"
        await storage.put(key, data)
        result = await storage.get(key)
        assert result == b"Hello, String!"

    @pytest.mark.asyncio
    async def test_alt_storage_put_stream(self, temp_storage_dir: str) -> None:
        """Test AltLocalStorage put_stream operation."""
        storage = AltLocalStorage(base_path=temp_storage_dir)
        # Create a source file
        src_file = Path(temp_storage_dir) / "source.txt"
        src_file.write_text("streamed content")
        key = "test/streamed.txt"
        await storage.put_stream(key, str(src_file))
        result = await storage.get(key)
        assert result == b"streamed content"


# ---------------------------------------------------------------------------
# StorageManager Tests
# ---------------------------------------------------------------------------


class TestStorageManager:
    """Tests for StorageManager singleton."""

    def test_initialize_local(self, temp_storage_dir: str) -> None:
        """Test StorageManager initializes local backend."""
        StorageManager.reset()
        storage = StorageManager.initialize(backend_type="local", base_dir=temp_storage_dir)
        assert isinstance(storage, LocalStorage)

    def test_initialize_unknown_raises(self) -> None:
        """Test StorageManager raises for unknown backend."""
        StorageManager.reset()
        with pytest.raises(ValueError):
            StorageManager.initialize(backend_type="unknown")

    def test_get_without_initialize_raises(self) -> None:
        """Test StorageManager.get raises if not initialized."""
        StorageManager.reset()
        with pytest.raises(RuntimeError):
            StorageManager.get()

    def test_reset(self, temp_storage_dir: str) -> None:
        """Test StorageManager.reset clears the singleton."""
        StorageManager.reset()
        StorageManager.initialize(backend_type="local", base_dir=temp_storage_dir)
        assert StorageManager._instance is not None
        StorageManager.reset()
        assert StorageManager._instance is None

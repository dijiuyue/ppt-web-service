"""
PPT Master Web Service — Source File Service Tests.

Tests for SourceService: file upload, type detection,
URL source management, listing, deletion, and content access.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.core.schemas import (
    ConversionStatus,
    FileType,
    SourceUrlAdd,
)
from app.models.project import Project
from app.models.source_file import SourceFile
from app.services.source_service import SourceService
from app.services.storage_service import StorageBackend


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def source_service(mock_db_session: MagicMock, storage: Any) -> SourceService:
    """Create a SourceService with mocked dependencies."""
    return SourceService(db=mock_db_session, storage=storage)


# Need Any import
from typing import Any


@pytest.fixture
def sample_project_for_source() -> Project:
    """Return a sample project for source file tests."""
    return Project(
        id=uuid4(),
        name="Source Test Project",
        canvas_format="ppt169",
        status="draft",
        current_step="init",
        step_status="pending",
        llm_provider="openai",
        llm_model="gpt-4o",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# File Type Detection Tests
# ---------------------------------------------------------------------------


class TestSourceServiceDetectFileType:
    """Tests for SourceService.detect_file_type static method."""

    def test_detect_pdf_by_extension(self) -> None:
        """Test PDF detection by file extension."""
        result = SourceService.detect_file_type("document.pdf")
        assert result == FileType.PDF

    def test_detect_docx_by_extension(self) -> None:
        """Test DOCX detection by file extension."""
        result = SourceService.detect_file_type("document.docx")
        assert result == FileType.DOCX

    def test_detect_xlsx_by_extension(self) -> None:
        """Test XLSX detection by file extension."""
        result = SourceService.detect_file_type("spreadsheet.xlsx")
        assert result == FileType.XLSX

    def test_detect_pptx_by_extension(self) -> None:
        """Test PPTX detection by file extension."""
        result = SourceService.detect_file_type("presentation.pptx")
        assert result == FileType.PPTX

    def test_detect_md_by_extension(self) -> None:
        """Test MD detection by file extension."""
        result = SourceService.detect_file_type("notes.md")
        assert result == FileType.MD

    def test_detect_txt_by_extension(self) -> None:
        """Test TXT detection by file extension."""
        result = SourceService.detect_file_type("readme.txt")
        assert result == FileType.TXT

    def test_detect_html_by_extension(self) -> None:
        """Test HTML detection by file extension."""
        result = SourceService.detect_file_type("page.html")
        assert result == FileType.HTML

    def test_detect_htm_alias(self) -> None:
        """Test HTM alias maps to HTML."""
        result = SourceService.detect_file_type("page.htm")
        assert result == FileType.HTML

    def test_detect_epub_by_extension(self) -> None:
        """Test EPUB detection by file extension."""
        result = SourceService.detect_file_type("book.epub")
        assert result == FileType.EPUB

    def test_detect_by_mime_type(self) -> None:
        """Test detection by MIME type takes priority."""
        result = SourceService.detect_file_type(
            "unknown.xyz", content_type="application/pdf"
        )
        assert result == FileType.PDF

    def test_detect_pdf_mime(self) -> None:
        """Test PDF detection by MIME type."""
        result = SourceService.detect_file_type(
            "file", content_type="application/pdf"
        )
        assert result == FileType.PDF

    def test_detect_docx_mime(self) -> None:
        """Test DOCX detection by MIME type."""
        result = SourceService.detect_file_type(
            "file", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert result == FileType.DOCX

    def test_detect_txt_mime_with_charset(self) -> None:
        """Test TXT detection with charset in MIME type."""
        result = SourceService.detect_file_type(
            "file", content_type="text/plain; charset=utf-8"
        )
        assert result == FileType.TXT

    def test_detect_unknown_defaults_to_txt(self) -> None:
        """Test unknown file type defaults to TXT."""
        result = SourceService.detect_file_type("unknown.xyz")
        assert result == FileType.TXT

    def test_detect_no_extension_defaults_to_txt(self) -> None:
        """Test file without extension defaults to TXT."""
        result = SourceService.detect_file_type("README")
        assert result == FileType.TXT

    def test_detect_case_insensitive_extension(self) -> None:
        """Test detection is case-insensitive for extensions."""
        result = SourceService.detect_file_type("DOCUMENT.PDF")
        assert result == FileType.PDF

        result2 = SourceService.detect_file_type("Document.Docx")
        assert result2 == FileType.DOCX


class TestSourceServiceIsBinaryFile:
    """Tests for SourceService.is_binary_file static method."""

    def test_pdf_is_binary(self) -> None:
        """Test PDF is considered binary."""
        assert SourceService.is_binary_file(FileType.PDF) is True

    def test_docx_is_binary(self) -> None:
        """Test DOCX is considered binary."""
        assert SourceService.is_binary_file(FileType.DOCX) is True

    def test_xlsx_is_binary(self) -> None:
        """Test XLSX is considered binary."""
        assert SourceService.is_binary_file(FileType.XLSX) is True

    def test_pptx_is_binary(self) -> None:
        """Test PPTX is considered binary."""
        assert SourceService.is_binary_file(FileType.PPTX) is True

    def test_epub_is_binary(self) -> None:
        """Test EPUB is considered binary."""
        assert SourceService.is_binary_file(FileType.EPUB) is True

    def test_txt_is_not_binary(self) -> None:
        """Test TXT is not binary."""
        assert SourceService.is_binary_file(FileType.TXT) is False

    def test_md_is_not_binary(self) -> None:
        """Test MD is not binary."""
        assert SourceService.is_binary_file(FileType.MD) is False

    def test_html_is_not_binary(self) -> None:
        """Test HTML is not binary."""
        assert SourceService.is_binary_file(FileType.HTML) is False

    def test_url_is_not_binary(self) -> None:
        """Test URL is not binary."""
        assert SourceService.is_binary_file(FileType.URL) is False


# ---------------------------------------------------------------------------
# Upload File Tests
# ---------------------------------------------------------------------------


class TestSourceServiceUploadFile:
    """Tests for SourceService.upload_file method."""

    @pytest.mark.asyncio
    async def test_upload_text_file(
        self,
        source_service: SourceService,
        mock_db_session: MagicMock,
        sample_project_for_source: Project,
    ) -> None:
        """Test uploading a text file (no conversion needed)."""
        file_data = b"Hello, this is a text file."
        result = await source_service.upload_file(
            project=sample_project_for_source,
            filename="notes.txt",
            file_data=file_data,
            content_type="text/plain",
        )

        assert isinstance(result, SourceFile)
        assert result.original_filename == "notes.txt"
        assert result.file_type == FileType.TXT.value
        assert result.file_size == len(file_data)
        assert result.conversion_status == ConversionStatus.COMPLETED.value
        assert result.project_id == sample_project_for_source.id
        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_awaited()

    @pytest.mark.asyncio
    async def test_upload_pdf_file_sets_pending(
        self,
        source_service: SourceService,
        mock_db_session: MagicMock,
        sample_project_for_source: Project,
    ) -> None:
        """Test uploading a PDF sets conversion status to PENDING."""
        # Mock trigger_conversion to avoid Celery/Redis connection
        source_service.trigger_conversion = AsyncMock()
        file_data = b"%PDF-1.4 fake pdf data"
        result = await source_service.upload_file(
            project=sample_project_for_source,
            filename="document.pdf",
            file_data=file_data,
            content_type="application/pdf",
        )

        assert result.file_type == FileType.PDF.value
        assert result.conversion_status == ConversionStatus.PENDING.value
        assert result.file_size == len(file_data)
        source_service.trigger_conversion.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_upload_md_file(
        self,
        source_service: SourceService,
        mock_db_session: MagicMock,
        sample_project_for_source: Project,
    ) -> None:
        """Test uploading a markdown file."""
        file_data = b"# Heading\n\nSome content."
        result = await source_service.upload_file(
            project=sample_project_for_source,
            filename="notes.md",
            file_data=file_data,
            content_type="text/markdown",
        )

        assert result.file_type == FileType.MD.value
        assert result.conversion_status == ConversionStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_upload_with_sort_order(
        self,
        source_service: SourceService,
        mock_db_session: MagicMock,
        sample_project_for_source: Project,
    ) -> None:
        """Test uploading with custom sort order."""
        result = await source_service.upload_file(
            project=sample_project_for_source,
            filename="ordered.txt",
            file_data=b"content",
            sort_order=5,
        )

        assert result.sort_order == 5

    @pytest.mark.asyncio
    async def test_upload_without_content_type(
        self,
        source_service: SourceService,
        mock_db_session: MagicMock,
        sample_project_for_source: Project,
    ) -> None:
        """Test uploading without content type (uses extension)."""
        result = await source_service.upload_file(
            project=sample_project_for_source,
            filename="file.txt",
            file_data=b"content",
        )

        assert result.file_type == FileType.TXT.value


# ---------------------------------------------------------------------------
# Upload Multiple Files Tests
# ---------------------------------------------------------------------------


class TestSourceServiceUploadMultiple:
    """Tests for SourceService.upload_multiple method."""

    @pytest.mark.asyncio
    async def test_upload_multiple_files(
        self,
        source_service: SourceService,
        mock_db_session: MagicMock,
        sample_project_for_source: Project,
    ) -> None:
        """Test uploading multiple files."""
        files = [
            ("file1.txt", b"content1", "text/plain"),
            ("file2.txt", b"content2", "text/plain"),
            ("file3.txt", b"content3", "text/plain"),
        ]
        results = await source_service.upload_multiple(
            project=sample_project_for_source, files=files
        )

        assert len(results) == 3
        assert results[0].original_filename == "file1.txt"
        assert results[1].original_filename == "file2.txt"
        assert results[2].original_filename == "file3.txt"
        # Check sort_order is auto-assigned
        assert results[0].sort_order == 0
        assert results[1].sort_order == 1
        assert results[2].sort_order == 2


# ---------------------------------------------------------------------------
# URL Source Tests
# ---------------------------------------------------------------------------


class TestSourceServiceAddUrlSource:
    """Tests for SourceService.add_url_source method."""

    @pytest.mark.asyncio
    async def test_add_url_source_with_title(
        self,
        source_service: SourceService,
        mock_db_session: MagicMock,
        sample_project_for_source: Project,
    ) -> None:
        """Test adding a URL source with title."""
        data = SourceUrlAdd(url="https://example.com", title="Example Site")
        result = await source_service.add_url_source(
            project=sample_project_for_source, data=data
        )

        assert isinstance(result, SourceFile)
        assert result.original_filename == "Example Site"
        assert result.file_type == FileType.URL.value
        assert result.conversion_status == ConversionStatus.COMPLETED.value
        mock_db_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_url_source_without_title(
        self,
        source_service: SourceService,
        mock_db_session: MagicMock,
        sample_project_for_source: Project,
    ) -> None:
        """Test adding a URL source without title (uses URL as filename)."""
        data = SourceUrlAdd(url="https://example.com/article")
        result = await source_service.add_url_source(
            project=sample_project_for_source, data=data
        )

        assert result.original_filename == "https://example.com/article"
        assert result.file_type == FileType.URL.value

    @pytest.mark.asyncio
    async def test_add_url_source_with_sort_order(
        self,
        source_service: SourceService,
        mock_db_session: MagicMock,
        sample_project_for_source: Project,
    ) -> None:
        """Test adding a URL source with custom sort order."""
        data = SourceUrlAdd(
            url="https://example.com", title="Ordered", sort_order=3
        )
        result = await source_service.add_url_source(
            project=sample_project_for_source, data=data
        )

        assert result.sort_order == 3


# ---------------------------------------------------------------------------
# Query Operations Tests
# ---------------------------------------------------------------------------


class TestSourceServiceGetById:
    """Tests for SourceService.get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        source_service: SourceService,
        mock_db_session: MagicMock,
        sample_source_file: SourceFile,
    ) -> None:
        """Test get_by_id returns source file when found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_source_file
        mock_db_session.execute.return_value = mock_result

        result = await source_service.get_by_id(sample_source_file.id)

        assert result is sample_source_file
        assert result.original_filename == "test_document.pdf"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self, source_service: SourceService, mock_db_session: MagicMock
    ) -> None:
        """Test get_by_id returns None when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await source_service.get_by_id(uuid4())

        assert result is None


class TestSourceServiceGetList:
    """Tests for SourceService.get_list method."""

    @pytest.mark.asyncio
    async def test_get_list(
        self,
        source_service: SourceService,
        mock_db_session: MagicMock,
        sample_source_file: SourceFile,
    ) -> None:
        """Test listing source files for a project."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_source_file]
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_db_session.execute.side_effect = [mock_result, mock_count_result]

        files, total = await source_service.get_list(
            project_id=sample_source_file.project_id
        )

        assert len(files) == 1
        assert total == 1
        assert files[0].original_filename == "test_document.pdf"

    @pytest.mark.asyncio
    async def test_get_list_empty(
        self, source_service: SourceService, mock_db_session: MagicMock
    ) -> None:
        """Test listing source files returns empty when none exist."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_db_session.execute.side_effect = [mock_result, mock_count_result]

        files, total = await source_service.get_list(project_id=uuid4())

        assert len(files) == 0
        assert total == 0


# ---------------------------------------------------------------------------
# Delete Tests
# ---------------------------------------------------------------------------


class TestSourceServiceDelete:
    """Tests for SourceService.delete method."""

    @pytest.mark.asyncio
    async def test_delete_source_file(
        self,
        source_service: SourceService,
        mock_db_session: MagicMock,
        sample_source_file: SourceFile,
    ) -> None:
        """Test deleting a source file."""
        await source_service.delete(sample_source_file)

        mock_db_session.delete.assert_called_once_with(sample_source_file)
        mock_db_session.flush.assert_awaited()


# ---------------------------------------------------------------------------
# Content Access Tests
# ---------------------------------------------------------------------------


class TestSourceServiceGetSourceContent:
    """Tests for SourceService.get_source_content method."""

    @pytest.mark.asyncio
    async def test_get_content_from_markdown_content_field(
        self,
        source_service: SourceService,
        sample_source_file: SourceFile,
    ) -> None:
        """Test getting content from markdown_content field."""
        sample_source_file.markdown_content = "# Markdown Content"
        result = await source_service.get_source_content(sample_source_file)
        assert result == "# Markdown Content"

    @pytest.mark.asyncio
    async def test_get_content_no_markdown_returns_none(
        self,
        source_service: SourceService,
        sample_source_file: SourceFile,
    ) -> None:
        """Test getting content when no markdown available."""
        sample_source_file.markdown_content = None
        sample_source_file.markdown_storage_key = None
        sample_source_file.file_type = FileType.PDF.value
        result = await source_service.get_source_content(sample_source_file)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_content_for_text_file_from_storage(
        self,
        source_service: SourceService,
        sample_project_for_source: Project,
        storage: Any,
    ) -> None:
        """Test getting content for text file reads from storage."""
        file_data = b"Storage content here"
        sf = SourceFile(
            id=uuid4(),
            project_id=sample_project_for_source.id,
            original_filename="test.txt",
            file_type=FileType.TXT.value,
            storage_key=f"projects/{sample_project_for_source.id}/sources/test.txt",
            storage_backend="local",
            file_size=len(file_data),
            conversion_status=ConversionStatus.COMPLETED.value,
        )
        # Put data in storage
        await storage.put(sf.storage_key, file_data)
        result = await source_service.get_source_content(sf)
        assert result == "Storage content here"


class TestSourceServiceGetCombinedContent:
    """Tests for SourceService.get_combined_source_content method."""

    @pytest.mark.asyncio
    async def test_combined_content_empty(
        self,
        source_service: SourceService,
        mock_db_session: MagicMock,
    ) -> None:
        """Test combined content returns empty string for no sources."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_db_session.execute.side_effect = [mock_result, mock_count_result]

        result = await source_service.get_combined_source_content(uuid4())
        assert result == ""

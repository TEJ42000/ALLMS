"""Tests for the text extraction service.

This module tests the unified text extraction functionality that supports
multiple file types: PDFs, slide archives, images (OCR), DOCX, markdown,
text, HTML, and JSON files.

These extraction methods should be used by any file upload or document
processing functionality to ensure text is available for LLM operations
(quizzes, summaries, search, etc.).
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from app.services.text_extractor import (
    detect_file_type,
    extract_text,
    extract_from_text,
    extract_from_html,
    extract_from_json,
    extract_from_pdf,  # FIX #259: Import for direct PDF testing
    get_file_extension,
    ExtractionResult,
)


class TestFileTypeDetection:
    """Tests for file type detection."""

    def test_get_file_extension(self):
        """Test extracting file extension."""
        assert get_file_extension(Path("test.pdf")) == "pdf"
        assert get_file_extension(Path("test.PDF")) == "pdf"
        assert get_file_extension(Path("path/to/file.docx")) == "docx"
        assert get_file_extension(Path("no_extension")) == ""

    def test_detect_markdown_file(self, tmp_path):
        """Test detecting markdown files."""
        md_file = tmp_path / "test.md"
        md_file.write_text("# Test Markdown")
        assert detect_file_type(md_file) == "markdown"

    def test_detect_text_file(self, tmp_path):
        """Test detecting plain text files."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Plain text content")
        assert detect_file_type(txt_file) == "text"

    def test_detect_html_file(self, tmp_path):
        """Test detecting HTML files."""
        html_file = tmp_path / "test.html"
        html_file.write_text("<html><body>Test</body></html>")
        assert detect_file_type(html_file) == "html"

    def test_detect_json_file(self, tmp_path):
        """Test detecting JSON files."""
        json_file = tmp_path / "test.json"
        json_file.write_text('{"key": "value"}')
        assert detect_file_type(json_file) == "json"

    def test_detect_image_files(self, tmp_path):
        """Test detecting image files."""
        for ext in ["png", "jpg", "jpeg", "gif"]:
            img_file = tmp_path / f"test.{ext}"
            img_file.write_bytes(b"fake image data")
            assert detect_file_type(img_file) == "image"

    def test_detect_nonexistent_file(self):
        """Test detecting a file that doesn't exist."""
        assert detect_file_type(Path("/nonexistent/file.txt")) == "unknown"


class TestTextExtraction:
    """Tests for text extraction from various file types."""

    def test_extract_from_markdown(self, tmp_path):
        """Test extracting text from markdown files."""
        md_file = tmp_path / "test.md"
        content = "# Heading\n\nThis is **bold** text."
        md_file.write_text(content)

        result = extract_text(md_file, _skip_path_validation=True)

        assert result.success is True
        assert result.file_type == "md"
        assert result.text == content
        assert result.error is None
        assert "char_count" in result.metadata

    def test_extract_from_text_file(self, tmp_path):
        """Test extracting text from plain text files."""
        txt_file = tmp_path / "test.txt"
        content = "Line 1\nLine 2\nLine 3"
        txt_file.write_text(content)

        result = extract_text(txt_file, _skip_path_validation=True)

        assert result.success is True
        assert result.text == content
        assert result.metadata["line_count"] == 3

    def test_extract_from_html(self, tmp_path):
        """Test extracting text from HTML files."""
        html_file = tmp_path / "test.html"
        html_content = """
        <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Welcome</h1>
            <p>This is a paragraph.</p>
            <script>console.log('ignored');</script>
        </body>
        </html>
        """
        html_file.write_text(html_content)

        result = extract_text(html_file, _skip_path_validation=True)

        assert result.success is True
        assert "Welcome" in result.text
        assert "This is a paragraph" in result.text
        # Script content should be removed
        assert "console.log" not in result.text

    def test_extract_from_json(self, tmp_path):
        """Test extracting text from JSON files."""
        json_file = tmp_path / "test.json"
        json_content = {
            "title": "Test Document",
            "content": "This is the main content of the document.",
            "metadata": {
                "author": "John Doe",
                "description": "A test file for extraction"
            }
        }
        json_file.write_text(json.dumps(json_content))

        result = extract_text(json_file, _skip_path_validation=True)

        assert result.success is True
        assert "Test Document" in result.text
        assert "main content" in result.text
        assert result.metadata["is_structured"] is True

    def test_extract_nonexistent_file(self):
        """Test extracting from a file that doesn't exist."""
        result = extract_text(Path("/nonexistent/file.md"), _skip_path_validation=True)

        assert result.success is False
        assert "not found" in result.error.lower() or "invalid path" in result.error.lower()

    def test_extract_with_encoding_fallback(self, tmp_path):
        """Test that extraction handles different encodings."""
        txt_file = tmp_path / "test.txt"
        # Write with latin-1 encoding
        txt_file.write_bytes("Café résumé".encode("latin-1"))

        result = extract_from_text(txt_file)

        assert result.success is True
        # Should successfully read with fallback encoding


class TestExtractionResult:
    """Tests for the ExtractionResult dataclass."""

    def test_extraction_result_defaults(self):
        """Test ExtractionResult with default values."""
        result = ExtractionResult(
            file_path="test.txt",
            file_type="text",
            text="content",
            success=True
        )

        assert result.error is None
        assert result.metadata == {}
        assert result.pages is None

    def test_extraction_result_with_pages(self):
        """Test ExtractionResult with page data."""
        pages = [
            {"page_number": 1, "text": "Page 1"},
            {"page_number": 2, "text": "Page 2"},
        ]
        result = ExtractionResult(
            file_path="test.pdf",
            file_type="pdf",
            text="Page 1\nPage 2",
            success=True,
            pages=pages
        )

        assert len(result.pages) == 2
        assert result.pages[0]["page_number"] == 1


class TestDocxExtraction:
    """Tests for DOCX file extraction with fallback behavior."""

    def test_extract_text_file_with_docx_extension(self, tmp_path):
        """Test that text files with .docx extension are handled gracefully."""
        # Create a text file with .docx extension (like many in our Materials folder)
        fake_docx = tmp_path / "fake.docx"
        fake_docx.write_text("This is actually plain text, not a real DOCX.")

        result = extract_text(fake_docx, _skip_path_validation=True)

        # Should succeed by falling back to text extraction
        assert result.success is True
        assert "plain text" in result.text


class TestBatchExtraction:
    """Tests for batch extraction operations."""

    def test_extract_all_from_folder(self, tmp_path):
        """Test extracting from multiple files in a folder."""
        from app.services.text_extractor import extract_all_from_folder

        # Create test files
        (tmp_path / "file1.md").write_text("# Markdown content")
        (tmp_path / "file2.txt").write_text("Plain text content")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file3.md").write_text("Nested content")

        # Skip path validation for test files in tmp_path
        results = extract_all_from_folder(tmp_path, recursive=True, _skip_path_validation=True)

        assert len(results) == 3
        assert all(r.success for r in results)

    def test_extract_all_non_recursive(self, tmp_path):
        """Test non-recursive extraction."""
        from app.services.text_extractor import extract_all_from_folder

        (tmp_path / "file1.md").write_text("# Top level")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file2.md").write_text("Nested")

        results = extract_all_from_folder(tmp_path, recursive=False, _skip_path_validation=True)

        assert len(results) == 1

    def test_get_extraction_summary(self):
        """Test generating extraction summary."""
        from app.services.text_extractor import get_extraction_summary

        results = [
            ExtractionResult("f1.md", "md", "content1", True, metadata={}),
            ExtractionResult("f2.md", "md", "content2", True, metadata={}),
            ExtractionResult("f3.pdf", "pdf", "", False, error="Failed"),
        ]

        summary = get_extraction_summary(results)

        assert summary["total_files"] == 3
        assert summary["successful"] == 2
        assert summary["failed"] == 1
        assert len(summary["errors"]) == 1


class TestIntegrationWithRealFiles:
    """Integration tests using actual files from the Materials folder.

    These tests verify the extraction works on real course materials.
    They are skipped if the Materials folder doesn't exist.
    """

    @pytest.fixture
    def materials_path(self):
        """Get the Materials folder path, skip if not present."""
        path = Path("Materials")
        if not path.exists():
            pytest.skip("Materials folder not available")
        return path

    @pytest.mark.skip(reason="Depends on local Materials files not available in CI.")
    def test_extract_real_markdown_file(self, materials_path):
        """Test extraction from a real markdown file."""
        md_file = materials_path / "README.md"
        if not md_file.exists():
            pytest.skip("README.md not found")

        result = extract_text(md_file, _skip_path_validation=True)

        assert result.success is True
        assert len(result.text) > 0

    def test_extract_real_pdf_file(self, tmp_path):
        """Test extraction from a real PDF file.

        FIX #259: Generate PDF at test time from base64 to ensure cross-platform
        compatibility and avoid git line-ending issues.
        """
        import base64

        # Check if PyMuPDF is installed
        try:
            import fitz
        except ImportError:
            pytest.skip("PyMuPDF (fitz) not installed - required for PDF extraction")

        # FIX #259: Base64-encoded minimal PDF with embedded text
        # This PDF contains: "Test PDF Document", "unit testing", "Legal Studies"
        pdf_base64 = (
            "JVBERi0xLjQKMSAwIG9iago8PCAvVHlwZSAvQ2F0YWxvZyAvUGFnZXMgMiAwIFIgPj4KZW5k"
            "b2JqCjIgMCBvYmoKPDwgL1R5cGUgL1BhZ2VzIC9LaWRzIFszIDAgUl0gL0NvdW50IDEgPj4K"
            "ZW5kb2JqCjMgMCBvYmoKPDwgL1R5cGUgL1BhZ2UgL1BhcmVudCAyIDAgUiAvTWVkaWFCb3gg"
            "WzAgMCA2MTIgNzkyXQogICAvQ29udGVudHMgNCAwIFIgL1Jlc291cmNlcyA8PCAvRm9udCA8"
            "PCAvRjEgNSAwIFIgPj4gPj4gPj4KZW5kb2JqCjQgMCBvYmoKPDwgL0xlbmd0aCAxNzggPj4K"
            "c3RyZWFtCkJUCi9GMSAxNCBUZgoxMDAgNzAwIFRkCihUZXN0IFBERiBEb2N1bWVudCkgVGoK"
            "MCAtMjAgVGQKKFRoaXMgaXMgYSBzYW1wbGUgUERGIGZpbGUgZm9yIHVuaXQgdGVzdGluZy4p"
            "IFRqCjAgLTIwIFRkCihMZWdhbCBTdHVkaWVzIENvdXJzZSBNYXRlcmlhbCkgVGoKRVQKZW5k"
            "c3RyZWFtCmVuZG9iago1IDAgb2JqCjw8IC9UeXBlIC9Gb250IC9TdWJ0eXBlIC9UeXBlMSAv"
            "QmFzZUZvbnQgL0hlbHZldGljYSA+PgplbmRvYmoKeHJlZgowIDYKMDAwMDAwMDAwMCA2NTUz"
            "NSBmIAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwNTggMDAwMDAgbiAKMDAwMDAwMDEx"
            "NSAwMDAwMCBuIAowMDAwMDAwMjY2IDAwMDAwIG4gCjAwMDAwMDA0OTQgMDAwMDAgbiAKdHJh"
            "aWxlcgo8PCAvU2l6ZSA2IC9Sb290IDEgMCBSID4+CnN0YXJ0eHJlZgo1NzMKJSVFT0YK"
        )

        # Write PDF to temp file
        pdf_file = tmp_path / "sample.pdf"
        pdf_file.write_bytes(base64.b64decode(pdf_base64))

        # FIX #259: Use extract_from_pdf directly to bypass file type detection
        result = extract_from_pdf(pdf_file)

        assert result.success is True
        assert result.file_type == "pdf"
        assert len(result.text) > 0
        assert result.pages is not None
        # FIX #259: Verify expected content from fixture
        assert "Test PDF Document" in result.text
        assert "Legal Studies" in result.text

    @pytest.mark.skip(reason="Depends on local Materials files not available in CI.")
    def test_extract_slide_archive(self, materials_path):
        """Test extraction from a slide archive (ZIP disguised as PDF)."""
        slide_file = (
            materials_path / "Course_Materials" / "LLS" / "Lectures" /
            "LLS_2526_Lecture_week_3_Administrative_law_Final.pdf"
        )
        if not slide_file.exists():
            pytest.skip("Slide archive not found")

        result = extract_text(slide_file)

        assert result.success is True
        assert result.file_type == "slide_archive"
        assert result.pages is not None
        assert len(result.pages) > 0


class TestAPIEndpoints:
    """Tests for the text extraction API endpoints."""

    def test_extract_single_file_endpoint(self, client):
        """Test the single file extraction endpoint."""
        # Use a known markdown file
        response = client.get(
            "/api/admin/courses/materials/extract/README.md"
        )

        # May 404 if file doesn't exist in test env
        if response.status_code == 404:
            pytest.skip("Test file not available")

        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert "file_type" in data
        assert "success" in data

    def test_extract_nonexistent_file_endpoint(self, client):
        """Test extraction endpoint with nonexistent file."""
        response = client.get(
            "/api/admin/courses/materials/extract/nonexistent_file_12345.xyz"
        )

        assert response.status_code == 404

    def test_extract_batch_endpoint(self, client):
        """Test the batch extraction endpoint."""
        response = client.get(
            "/api/admin/courses/materials/extract-batch",
            params={"folder": "Syllabus", "recursive": False}
        )

        # May 404 if folder doesn't exist
        if response.status_code == 404:
            pytest.skip("Test folder not available")

        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "files" in data

    def test_extract_batch_nonexistent_folder(self, client):
        """Test batch extraction with nonexistent folder."""
        response = client.get(
            "/api/admin/courses/materials/extract-batch",
            params={"folder": "nonexistent_folder_12345"}
        )

        assert response.status_code == 404


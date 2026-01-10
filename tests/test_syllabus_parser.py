"""
Unit tests for syllabus_parser security features.

Tests cover:
- Path traversal protection in extract_text_from_folder()
- Path traversal protection in extract_text_from_pdf()
- Null byte injection protection
- Valid path acceptance

Security: These tests verify CodeQL Alert #50 fixes (CWE-22/23/36)
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Mock fitz (PyMuPDF) before importing syllabus_parser
# This prevents import errors in environments without PyMuPDF
sys.modules['fitz'] = MagicMock()

from app.services.syllabus_parser import (
    validate_path_within_base,
    extract_text_from_folder,
    extract_text_from_pdf,
    MATERIALS_BASE
)


class TestValidatePathWithinBase:
    """Tests for the validate_path_within_base() security function."""

    def test_valid_relative_path(self, tmp_path):
        """Test that valid relative paths are accepted."""
        # Create a subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        
        result = validate_path_within_base("subdir", tmp_path)
        assert result == subdir.resolve()

    def test_path_traversal_blocked(self, tmp_path):
        """Test that path traversal attempts are blocked."""
        with pytest.raises(ValueError, match="outside allowed directory"):
            validate_path_within_base("../../../etc", tmp_path)

    @pytest.mark.skipif(
        sys.platform != "win32",
        reason="Backslash is only a path separator on Windows"
    )
    def test_path_traversal_with_backslash_blocked(self, tmp_path):
        """Test that Windows-style path traversal is blocked (Windows only)."""
        with pytest.raises(ValueError, match="outside allowed directory"):
            validate_path_within_base("..\\..\\..\\windows\\system32", tmp_path)

    def test_null_byte_injection_blocked(self, tmp_path):
        """Test that null byte injection is blocked."""
        with pytest.raises(ValueError, match="null bytes"):
            validate_path_within_base("test\x00.pdf", tmp_path)

    def test_nested_path_traversal_blocked(self, tmp_path):
        """Test that nested path traversal attempts are blocked."""
        # Create a valid subdirectory
        subdir = tmp_path / "valid"
        subdir.mkdir()
        
        with pytest.raises(ValueError, match="outside allowed directory"):
            validate_path_within_base("valid/../../../etc/passwd", tmp_path)


class TestExtractTextFromFolderSecurity:
    """Tests for path validation in extract_text_from_folder()."""

    def test_path_traversal_blocked(self):
        """Test that path traversal in folder_path is blocked."""
        with pytest.raises(FileNotFoundError, match="Invalid folder path"):
            extract_text_from_folder("../../../etc")

    def test_path_traversal_with_dots_blocked(self):
        """Test that ../.. traversal is blocked."""
        with pytest.raises(FileNotFoundError, match="Invalid folder path"):
            extract_text_from_folder("../../..")

    def test_absolute_path_outside_base_blocked(self):
        """Test that absolute paths outside MATERIALS_BASE are blocked."""
        with pytest.raises(FileNotFoundError, match="Invalid folder path"):
            extract_text_from_folder("/etc/passwd")

    def test_null_byte_blocked(self):
        """Test that null bytes in folder path are blocked."""
        with pytest.raises(FileNotFoundError, match="Invalid folder path"):
            extract_text_from_folder("Syllabus\x00/../../../etc")


class TestExtractTextFromPdfSecurity:
    """Tests for path validation in extract_text_from_pdf()."""

    def test_path_traversal_blocked(self):
        """Test that path traversal in pdf_path is blocked."""
        with pytest.raises(FileNotFoundError, match="Invalid PDF path"):
            extract_text_from_pdf("../../../etc/passwd")

    def test_path_traversal_with_file_extension_blocked(self):
        """Test that path traversal with .pdf extension is still blocked."""
        with pytest.raises(FileNotFoundError, match="Invalid PDF path"):
            extract_text_from_pdf("../../secret.pdf")

    def test_absolute_path_outside_base_blocked(self):
        """Test that absolute paths outside MATERIALS_BASE are blocked."""
        with pytest.raises(FileNotFoundError, match="Invalid PDF path"):
            extract_text_from_pdf("/tmp/malicious.pdf")

    def test_null_byte_blocked(self):
        """Test that null bytes in pdf path are blocked."""
        with pytest.raises(FileNotFoundError, match="Invalid PDF path"):
            extract_text_from_pdf("test\x00.pdf")


class TestValidPathsAccepted:
    """Tests to ensure valid paths still work correctly."""

    @patch('app.services.syllabus_parser.MATERIALS_BASE')
    def test_valid_relative_folder_path_accepted(self, mock_base, tmp_path):
        """Test that valid relative folder paths are accepted (though may not exist)."""
        # Setup mock
        valid_folder = tmp_path / "Syllabus" / "LLS"
        valid_folder.mkdir(parents=True)
        
        # Create a test PDF file
        test_pdf = valid_folder / "test.pdf"
        test_pdf.write_bytes(b'%PDF-1.4\n')  # Minimal PDF header
        
        with patch('app.services.syllabus_parser.MATERIALS_BASE', tmp_path):
            # This should not raise a path validation error
            # (may raise FileNotFoundError for other reasons like no PDFs)
            try:
                extract_text_from_folder("Syllabus/LLS")
            except FileNotFoundError as e:
                # Should NOT be a path validation error
                assert "Invalid folder path" not in str(e)

    @patch('app.services.syllabus_parser.MATERIALS_BASE')
    def test_valid_relative_pdf_path_accepted(self, mock_base, tmp_path):
        """Test that valid relative PDF paths are accepted."""
        # Setup mock
        valid_folder = tmp_path / "Syllabus"
        valid_folder.mkdir(parents=True)
        test_pdf = valid_folder / "test.pdf"
        test_pdf.write_bytes(b'%PDF-1.4\n')
        
        with patch('app.services.syllabus_parser.MATERIALS_BASE', tmp_path):
            # This should not raise a path validation error
            try:
                extract_text_from_pdf("Syllabus/test.pdf")
            except Exception as e:
                # Should NOT be a path validation error
                assert "Invalid PDF path" not in str(e)


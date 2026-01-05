"""Tests for the AnthropicFileManager service.

Tests cover:
- File path validation and traversal protection
- File validation (size, type)
- Upload and file management
- Error handling
"""

import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


class TestAnthropicFileManagerPathValidation:
    """Tests for path traversal protection."""

    def test_get_local_file_path_valid(self):
        """Test that valid paths are accepted."""
        from app.services.anthropic_file_manager import AnthropicFileManager, MATERIALS_ROOT

        with patch.object(AnthropicFileManager, '__init__', lambda x: None):
            manager = AnthropicFileManager()
            manager.client = MagicMock()
            manager._firestore = None

            # Create a mock material with valid path
            material = MagicMock()
            material.storagePath = "Tier_1_Syllabus/test.pdf"

            # Should not raise
            result = manager.get_local_file_path(material)
            assert str(MATERIALS_ROOT) in str(result)

    def test_get_local_file_path_traversal_attack(self):
        """Test that path traversal attacks are blocked."""
        from app.services.anthropic_file_manager import (
            AnthropicFileManager,
            PathTraversalError
        )

        with patch.object(AnthropicFileManager, '__init__', lambda x: None):
            manager = AnthropicFileManager()
            manager.client = MagicMock()
            manager._firestore = None

            # Create a mock material with malicious path
            material = MagicMock()
            material.storagePath = "../../../etc/passwd"

            with pytest.raises(PathTraversalError):
                manager.get_local_file_path(material)

    def test_get_local_file_path_double_dot_in_middle(self):
        """Test that path traversal in the middle is blocked."""
        from app.services.anthropic_file_manager import (
            AnthropicFileManager,
            PathTraversalError
        )

        with patch.object(AnthropicFileManager, '__init__', lambda x: None):
            manager = AnthropicFileManager()
            manager.client = MagicMock()
            manager._firestore = None

            material = MagicMock()
            material.storagePath = "Tier_1_Syllabus/../../../etc/passwd"

            with pytest.raises(PathTraversalError):
                manager.get_local_file_path(material)


class TestAnthropicFileManagerFileValidation:
    """Tests for file validation before upload."""

    def test_validate_file_not_found(self, tmp_path):
        """Test validation fails for non-existent file."""
        from app.services.anthropic_file_manager import (
            AnthropicFileManager,
            LocalFileNotFoundError
        )

        with patch.object(AnthropicFileManager, '__init__', lambda x: None):
            manager = AnthropicFileManager()
            manager.client = MagicMock()
            manager._firestore = None

            non_existent = tmp_path / "does_not_exist.pdf"

            with pytest.raises(LocalFileNotFoundError):
                manager._validate_file_for_upload(non_existent)

    def test_validate_file_empty(self, tmp_path):
        """Test validation fails for empty file."""
        from app.services.anthropic_file_manager import (
            AnthropicFileManager,
            FileValidationError
        )

        with patch.object(AnthropicFileManager, '__init__', lambda x: None):
            manager = AnthropicFileManager()
            manager.client = MagicMock()
            manager._firestore = None

            empty_file = tmp_path / "empty.pdf"
            empty_file.write_text("")

            with pytest.raises(FileValidationError, match="empty"):
                manager._validate_file_for_upload(empty_file)

    def test_validate_file_unsupported_extension(self, tmp_path):
        """Test validation fails for unsupported file types."""
        from app.services.anthropic_file_manager import (
            AnthropicFileManager,
            FileValidationError
        )

        with patch.object(AnthropicFileManager, '__init__', lambda x: None):
            manager = AnthropicFileManager()
            manager.client = MagicMock()
            manager._firestore = None

            exe_file = tmp_path / "malware.exe"
            exe_file.write_text("dummy content")

            with pytest.raises(FileValidationError, match="Unsupported file type"):
                manager._validate_file_for_upload(exe_file)

    def test_validate_file_valid_pdf(self, tmp_path):
        """Test validation passes for valid PDF file."""
        from app.services.anthropic_file_manager import AnthropicFileManager

        with patch.object(AnthropicFileManager, '__init__', lambda x: None):
            manager = AnthropicFileManager()
            manager.client = MagicMock()
            manager._firestore = None

            valid_pdf = tmp_path / "valid.pdf"
            valid_pdf.write_text("dummy PDF content")

            # Should not raise
            manager._validate_file_for_upload(valid_pdf)

    def test_validate_file_valid_txt(self, tmp_path):
        """Test validation passes for valid text file."""
        from app.services.anthropic_file_manager import AnthropicFileManager

        with patch.object(AnthropicFileManager, '__init__', lambda x: None):
            manager = AnthropicFileManager()
            manager.client = MagicMock()
            manager._firestore = None

            valid_txt = tmp_path / "notes.txt"
            valid_txt.write_text("Some study notes")

            # Should not raise
            manager._validate_file_for_upload(valid_txt)


class TestAnthropicFileManagerUpload:
    """Tests for file upload functionality."""

    def test_upload_file_success(self, tmp_path):
        """Test successful file upload."""
        from app.services.anthropic_file_manager import AnthropicFileManager, MATERIALS_ROOT

        with patch.object(AnthropicFileManager, '__init__', lambda x: None):
            manager = AnthropicFileManager()

            # Mock the Anthropic client
            mock_client = MagicMock()
            mock_uploaded = MagicMock()
            mock_uploaded.id = "file_abc123"
            mock_client.beta.files.upload.return_value = mock_uploaded
            manager.client = mock_client
            manager._firestore = None

            # Create a temporary test file
            test_dir = tmp_path / "Materials" / "Tier_1_Syllabus"
            test_dir.mkdir(parents=True)
            test_file = test_dir / "test.pdf"
            test_file.write_text("PDF content")

            # Create mock material
            material = MagicMock()
            material.filename = "test.pdf"
            material.storagePath = "Tier_1_Syllabus/test.pdf"

            # Patch MATERIALS_ROOT to use tmp_path
            with patch('app.services.anthropic_file_manager.MATERIALS_ROOT', tmp_path / "Materials"):
                result = manager.upload_file(material)

            assert result == "file_abc123"
            mock_client.beta.files.upload.assert_called_once()

    def test_upload_file_api_error(self, tmp_path):
        """Test upload handles API errors gracefully."""
        from anthropic import APIError
        from app.services.anthropic_file_manager import AnthropicFileManager, UploadError

        with patch.object(AnthropicFileManager, '__init__', lambda x: None):
            manager = AnthropicFileManager()

            # Mock the Anthropic client to raise an error
            mock_client = MagicMock()
            mock_client.beta.files.upload.side_effect = APIError(
                message="API Error",
                request=MagicMock(),
                body=None
            )
            manager.client = mock_client
            manager._firestore = None

            # Create a temporary test file
            test_dir = tmp_path / "Materials" / "Tier_1_Syllabus"
            test_dir.mkdir(parents=True)
            test_file = test_dir / "test.pdf"
            test_file.write_text("PDF content")

            material = MagicMock()
            material.filename = "test.pdf"
            material.storagePath = "Tier_1_Syllabus/test.pdf"

            with patch('app.services.anthropic_file_manager.MATERIALS_ROOT', tmp_path / "Materials"):
                with pytest.raises(UploadError, match="Anthropic API error"):
                    manager.upload_file(material)


class TestAnthropicFileManagerCheckExists:
    """Tests for file existence checking."""

    def test_check_file_exists_true(self):
        """Test file exists returns True."""
        from app.services.anthropic_file_manager import AnthropicFileManager

        with patch.object(AnthropicFileManager, '__init__', lambda x: None):
            manager = AnthropicFileManager()

            mock_client = MagicMock()
            mock_client.beta.files.retrieve.return_value = MagicMock()
            manager.client = mock_client
            manager._firestore = None

            assert manager.check_file_exists("file_abc123") is True

    def test_check_file_exists_not_found(self):
        """Test file not found returns False."""
        from anthropic import NotFoundError
        from app.services.anthropic_file_manager import AnthropicFileManager

        with patch.object(AnthropicFileManager, '__init__', lambda x: None):
            manager = AnthropicFileManager()

            mock_client = MagicMock()
            mock_client.beta.files.retrieve.side_effect = NotFoundError(
                message="Not found",
                response=MagicMock(),
                body=None
            )
            manager.client = mock_client
            manager._firestore = None

            assert manager.check_file_exists("file_nonexistent") is False


class TestAdminEndpointValidation:
    """Tests for admin endpoint input validation."""

    def test_validate_course_id_internal_function(self):
        """Test _validate_course_id function directly."""
        from app.routes.admin_courses import _validate_course_id
        from fastapi import HTTPException

        # Empty string should raise
        with pytest.raises(HTTPException) as exc_info:
            _validate_course_id("   ")
        assert exc_info.value.status_code == 400
        assert "empty" in str(exc_info.value.detail).lower()

    def test_validate_course_id_special_chars_internal(self):
        """Test special characters are rejected."""
        from app.routes.admin_courses import _validate_course_id
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _validate_course_id("test;DROP TABLE")
        assert exc_info.value.status_code == 400
        assert "alphanumeric" in str(exc_info.value.detail).lower()

    def test_validate_course_id_too_long(self):
        """Test course_id that's too long is rejected."""
        from app.routes.admin_courses import _validate_course_id
        from fastapi import HTTPException

        long_id = "x" * 101
        with pytest.raises(HTTPException) as exc_info:
            _validate_course_id(long_id)
        assert exc_info.value.status_code == 400
        assert "too long" in str(exc_info.value.detail).lower()

    def test_validate_course_id_valid_format(self):
        """Test valid course_id format is accepted."""
        from app.routes.admin_courses import _validate_course_id

        # Should not raise
        result = _validate_course_id("LLS-2025-2026")
        assert result == "LLS-2025-2026"

        result = _validate_course_id("course_123_test")
        assert result == "course_123_test"

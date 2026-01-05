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


class TestEnsureFileAvailable:
    """Tests for ensure_file_available method."""

    def test_ensure_file_available_returns_existing_valid_file(self):
        """Test that valid non-expired files are reused."""
        from datetime import datetime, timezone, timedelta
        from app.services.anthropic_file_manager import AnthropicFileManager

        with patch.object(AnthropicFileManager, '__init__', lambda x: None):
            manager = AnthropicFileManager()
            manager.client = MagicMock()
            manager._firestore = MagicMock()

            # Mock check_file_exists to return True
            manager.check_file_exists = MagicMock(return_value=True)

            # Create material with valid, non-expired file ID
            material = MagicMock()
            material.anthropicFileId = "file_existing123"
            material.anthropicFileExpiry = datetime.now(timezone.utc) + timedelta(days=10)
            material.filename = "test.pdf"

            result = manager.ensure_file_available(material, "test-course")

            assert result == "file_existing123"
            manager.check_file_exists.assert_called_once_with("file_existing123")

    def test_ensure_file_available_uploads_when_expired(self, tmp_path):
        """Test that expired files trigger re-upload."""
        from datetime import datetime, timezone, timedelta
        from app.services.anthropic_file_manager import AnthropicFileManager

        with patch.object(AnthropicFileManager, '__init__', lambda x: None):
            manager = AnthropicFileManager()
            manager._firestore = MagicMock()

            # Mock upload_file to return new ID
            manager.upload_file = MagicMock(return_value="file_new456")
            manager._update_material_anthropic_fields = MagicMock()

            # Create material with expired file ID
            material = MagicMock()
            material.anthropicFileId = "file_old123"
            material.anthropicFileExpiry = datetime.now(timezone.utc) - timedelta(days=1)
            material.filename = "test.pdf"
            material.id = "material_1"

            result = manager.ensure_file_available(material, "test-course")

            assert result == "file_new456"
            manager.upload_file.assert_called_once_with(material)
            manager._update_material_anthropic_fields.assert_called_once()

    def test_ensure_file_available_uploads_when_missing(self, tmp_path):
        """Test that missing file IDs trigger upload."""
        from app.services.anthropic_file_manager import AnthropicFileManager

        with patch.object(AnthropicFileManager, '__init__', lambda x: None):
            manager = AnthropicFileManager()
            manager._firestore = MagicMock()

            # Mock upload_file
            manager.upload_file = MagicMock(return_value="file_new789")
            manager._update_material_anthropic_fields = MagicMock()

            # Create material without file ID
            material = MagicMock()
            material.anthropicFileId = None
            material.anthropicFileExpiry = None
            material.filename = "test.pdf"
            material.id = "material_2"

            result = manager.ensure_file_available(material, "test-course")

            assert result == "file_new789"
            manager.upload_file.assert_called_once_with(material)


class TestFirestoreUpdateFailures:
    """Tests for Firestore update failure scenarios."""

    def test_update_material_fields_raises_on_failure(self):
        """Test that Firestore update failures are propagated."""
        from app.services.anthropic_file_manager import (
            AnthropicFileManager,
            AnthropicFileManagerError
        )
        from datetime import datetime, timezone

        with patch.object(AnthropicFileManager, '__init__', lambda x: None):
            manager = AnthropicFileManager()

            # Mock Firestore to raise exception
            mock_firestore = MagicMock()
            mock_doc_ref = MagicMock()
            mock_doc_ref.update.side_effect = Exception("Firestore connection failed")
            mock_firestore.collection.return_value.document.return_value.collection.return_value.document.return_value = mock_doc_ref
            manager._firestore = mock_firestore

            with pytest.raises(AnthropicFileManagerError) as exc_info:
                manager._update_material_anthropic_fields(
                    course_id="test-course",
                    material_id="material_1",
                    file_id="file_123",
                    uploaded_at=datetime.now(timezone.utc),
                    expiry=datetime.now(timezone.utc),
                    error=None
                )

            # Check the error message contains relevant info
            assert "Firestore" in str(exc_info.value)
            assert "material_1" in str(exc_info.value)


class TestGenerateQuizFromCourse:
    """Tests for generate_quiz_from_course method."""

    @pytest.mark.asyncio
    async def test_generate_quiz_from_course_success(self):
        """Test successful quiz generation from course materials."""
        from unittest.mock import AsyncMock
        from app.services.files_api_service import FilesAPIService

        with patch.object(FilesAPIService, '__init__', lambda x: None):
            service = FilesAPIService()
            service._firestore = MagicMock()
            service._file_manager = MagicMock()
            service.beta_header = "files-api-2025-04-14"  # Required attribute

            # Mock material
            mock_material = MagicMock()
            mock_material.title = "Contract Law Basics"
            mock_material.filename = "contracts.pdf"

            # Mock get_course_materials_with_file_ids
            service.get_course_materials_with_file_ids = AsyncMock(
                return_value=[(mock_material, "file_abc123")]
            )

            # Mock Anthropic API response (must be async)
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text='{"questions": [{"question": "What is a contract?"}]}')]

            # Create a mock client with async beta.messages.create
            mock_client = MagicMock()
            mock_client.beta.messages.create = AsyncMock(return_value=mock_response)
            service.client = mock_client

            result = await service.generate_quiz_from_course(
                course_id="LLS-2025",
                topic="Contracts",
                num_questions=5,
                difficulty="medium"
            )

            assert "questions" in result
            service.get_course_materials_with_file_ids.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_quiz_from_course_no_materials(self):
        """Test quiz generation fails gracefully with no materials."""
        from unittest.mock import AsyncMock
        from app.services.files_api_service import FilesAPIService

        with patch.object(FilesAPIService, '__init__', lambda x: None):
            service = FilesAPIService()
            service.client = MagicMock()
            service._firestore = MagicMock()

            # Mock empty materials
            service.get_course_materials_with_file_ids = AsyncMock(return_value=[])

            with pytest.raises(ValueError) as exc_info:
                await service.generate_quiz_from_course(
                    course_id="nonexistent-course",
                    topic="Contracts",
                    num_questions=5
                )

            assert "No materials found" in str(exc_info.value)


class TestRefreshEndpointIntegration:
    """Integration tests for admin refresh endpoint."""

    def test_refresh_endpoint_validates_course_id(self):
        """Test refresh endpoint validates course_id."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)

        # Invalid course_id with special chars
        response = client.post("/admin/courses/test;DROP/anthropic-files/refresh")

        # Should fail validation (course_id has invalid chars)
        assert response.status_code in [400, 404, 422]

    def test_refresh_endpoint_handles_nonexistent_course(self):
        """Test refresh endpoint handles nonexistent course gracefully."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)

        # Valid format but non-existent course
        response = client.post("/admin/courses/nonexistent-course-12345/anthropic-files/refresh")

        # Should return error (course not found or no materials)
        assert response.status_code in [200, 404]  # 200 with 0 uploaded is valid

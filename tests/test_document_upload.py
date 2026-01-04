"""Tests for Document Upload Service."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.document_upload_service import (
    validate_file,
    generate_storage_path,
    sanitize_filename,
    save_uploaded_file,
    delete_material_file,
    list_course_materials,
    get_supported_extensions,
    get_tier_options,
    get_category_options,
    UploadError,
    MAX_FILE_SIZE,
    SUPPORTED_TYPES,
    TIER_FOLDERS,
    CATEGORY_FOLDERS,
)


class TestValidateFile:
    """Tests for file validation."""

    def test_valid_pdf(self):
        """Test validating a valid PDF file."""
        ext = validate_file("document.pdf", 1024, "application/pdf")
        assert ext == "pdf"

    def test_valid_docx(self):
        """Test validating a valid DOCX file."""
        ext = validate_file("document.docx", 1024)
        assert ext == "docx"

    def test_valid_image(self):
        """Test validating valid image files."""
        for ext_type in ['png', 'jpg', 'jpeg', 'gif', 'bmp']:
            ext = validate_file(f"image.{ext_type}", 1024)
            assert ext == ext_type

    def test_valid_text(self):
        """Test validating text files."""
        for ext_type in ['txt', 'md', 'html']:
            ext = validate_file(f"file.{ext_type}", 1024)
            assert ext == ext_type

    def test_file_too_large(self):
        """Test that oversized files are rejected."""
        with pytest.raises(UploadError) as exc_info:
            validate_file("document.pdf", MAX_FILE_SIZE + 1)
        assert "too large" in str(exc_info.value).lower()

    def test_empty_file(self):
        """Test that empty files are rejected."""
        with pytest.raises(UploadError) as exc_info:
            validate_file("document.pdf", 0)
        assert "Empty" in str(exc_info.value)

    def test_no_extension(self):
        """Test that files without extensions are rejected."""
        with pytest.raises(UploadError) as exc_info:
            validate_file("document", 1024)
        assert "extension" in str(exc_info.value).lower()

    def test_unsupported_extension(self):
        """Test that unsupported extensions are rejected."""
        with pytest.raises(UploadError) as exc_info:
            validate_file("document.xyz", 1024)
        assert "Unsupported" in str(exc_info.value)


class TestSanitizeFilename:
    """Tests for filename sanitization."""

    def test_normal_filename(self):
        """Test that normal filenames are preserved."""
        assert sanitize_filename("document.pdf") == "document.pdf"

    def test_filename_with_spaces(self):
        """Test that spaces are preserved."""
        assert sanitize_filename("my document.pdf") == "my document.pdf"

    def test_filename_with_unsafe_chars(self):
        """Test that unsafe characters are replaced."""
        result = sanitize_filename("file:name*test?.pdf")
        assert ":" not in result
        assert "*" not in result
        assert "?" not in result
        assert result.endswith(".pdf")

    def test_empty_filename(self):
        """Test that empty filenames get a default."""
        result = sanitize_filename("")
        assert result.startswith("file_")


class TestGenerateStoragePath:
    """Tests for storage path generation."""

    def test_syllabus_tier(self):
        """Test path generation for syllabus tier."""
        path = generate_storage_path("LLS", "syllabus.pdf", tier="syllabus")
        assert "Syllabus" in str(path)
        assert "LLS" in str(path)

    def test_course_materials_tier(self):
        """Test path generation for course_materials tier."""
        path = generate_storage_path("LLS", "lecture.pdf", tier="course_materials")
        assert "Course_Materials" in str(path)
        assert "LLS" in str(path)

    def test_supplementary_tier(self):
        """Test path generation for supplementary tier."""
        path = generate_storage_path("LLS", "article.pdf", tier="supplementary")
        assert "Supplementary_Sources" in str(path)
        assert "LLS" in str(path)

    def test_with_category(self):
        """Test path generation with category."""
        path = generate_storage_path(
            "LLS", "lecture1.pdf",
            tier="course_materials",
            category="lecture"
        )
        assert "Lectures" in str(path)

    def test_unique_filename_on_collision(self):
        """Test that colliding filenames get unique suffixes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a temporary Materials directory structure
            with patch('app.services.document_upload_service.MATERIALS_ROOT', Path(tmpdir)):
                # Create first path
                path1 = generate_storage_path("LLS", "test.pdf")
                path1.parent.mkdir(parents=True, exist_ok=True)
                path1.write_text("test")

                # Generate another path - should be unique
                path2 = generate_storage_path("LLS", "test.pdf")
                assert path1 != path2


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_get_supported_extensions(self):
        """Test getting supported extensions."""
        extensions = get_supported_extensions()
        assert "pdf" in extensions
        assert "docx" in extensions
        assert "png" in extensions
        assert "txt" in extensions

    def test_get_tier_options(self):
        """Test getting tier options."""
        options = get_tier_options()
        assert len(options) == 3
        values = [o["value"] for o in options]
        assert "syllabus" in values
        assert "course_materials" in values
        assert "supplementary" in values

    def test_get_category_options(self):
        """Test getting category options."""
        options = get_category_options()
        assert len(options) >= 4
        values = [o["value"] for o in options]
        assert "lecture" in values
        assert "reading" in values
        assert "case" in values


class TestSaveUploadedFile:
    """Tests for file saving."""

    @pytest.mark.asyncio
    async def test_save_text_file(self):
        """Test saving a text file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('app.services.document_upload_service.MATERIALS_ROOT', Path(tmpdir)):
                content = b"This is test content for the file."

                material = await save_uploaded_file(
                    file_content=content,
                    filename="test.txt",
                    course_id="TEST-COURSE",
                    tier="course_materials"
                )

                assert material.filename == "test.txt"
                assert material.fileSize == len(content)
                assert material.fileType == "text"
                assert material.textExtracted is True
                assert "test content" in material.extractedText

    @pytest.mark.asyncio
    async def test_save_with_metadata(self):
        """Test saving with title and description."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('app.services.document_upload_service.MATERIALS_ROOT', Path(tmpdir)):
                material = await save_uploaded_file(
                    file_content=b"content",
                    filename="doc.txt",
                    course_id="TEST",
                    title="My Document",
                    description="A test document",
                    week_number=3
                )

                assert material.title == "My Document"
                assert material.description == "A test document"
                assert material.weekNumber == 3

    @pytest.mark.asyncio
    async def test_save_invalid_file_raises(self):
        """Test that invalid files raise UploadError."""
        with pytest.raises(UploadError):
            await save_uploaded_file(
                file_content=b"",
                filename="empty.pdf",
                course_id="TEST"
            )


class TestDeleteMaterialFile:
    """Tests for file deletion."""

    @pytest.mark.asyncio
    async def test_delete_existing_file(self):
        """Test deleting an existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("content")

            result = await delete_material_file(str(test_file))
            assert result is True
            assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_file(self):
        """Test deleting a non-existent file returns False."""
        result = await delete_material_file("/nonexistent/path/file.txt")
        assert result is False


class TestListCourseMaterials:
    """Tests for listing course materials."""

    def test_list_empty_course(self):
        """Test listing materials for a course with no files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('app.services.document_upload_service.MATERIALS_ROOT', Path(tmpdir)):
                materials = list_course_materials("NONEXISTENT")
                assert materials == []

    def test_list_with_files(self):
        """Test listing materials for a course with files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            materials_root = Path(tmpdir)

            # Create some test files
            course_dir = materials_root / "Course_Materials" / "TEST"
            course_dir.mkdir(parents=True)
            (course_dir / "lecture.pdf").write_text("content")

            syllabus_dir = materials_root / "Syllabus" / "TEST"
            syllabus_dir.mkdir(parents=True)
            (syllabus_dir / "syllabus.pdf").write_text("content")

            with patch('app.services.document_upload_service.MATERIALS_ROOT', materials_root):
                materials = list_course_materials("TEST")

                assert len(materials) == 2
                filenames = [m["filename"] for m in materials]
                assert "lecture.pdf" in filenames
                assert "syllabus.pdf" in filenames


class TestConstants:
    """Tests for module constants."""

    def test_max_file_size(self):
        """Test that max file size is reasonable."""
        assert MAX_FILE_SIZE == 50 * 1024 * 1024  # 50MB

    def test_supported_types_complete(self):
        """Test that all expected types are supported."""
        expected = ['pdf', 'docx', 'doc', 'txt', 'md', 'html', 'png', 'jpg', 'jpeg']
        for ext in expected:
            assert ext in SUPPORTED_TYPES

    def test_tier_folders_mapping(self):
        """Test tier to folder mapping."""
        assert TIER_FOLDERS["syllabus"] == "Syllabus"
        assert TIER_FOLDERS["course_materials"] == "Course_Materials"
        assert TIER_FOLDERS["supplementary"] == "Supplementary_Sources"

    def test_category_folders_mapping(self):
        """Test category to folder mapping."""
        assert CATEGORY_FOLDERS["lecture"] == "Lectures"
        assert CATEGORY_FOLDERS["reading"] == "Readings"
        assert CATEGORY_FOLDERS["case"] == "Cases"

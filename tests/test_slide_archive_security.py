"""Security tests for slide_archive.py path validation.

Tests that all file operations in slide_archive.py properly validate paths
to prevent path traversal attacks (CWE-22/23/36).
"""

import pytest
from pathlib import Path
import zipfile
import json
from unittest.mock import patch, MagicMock

from app.services.slide_archive import (
    is_slide_archive,
    get_file_type,
    extract_slide_archive,
    MATERIALS_BASE
)


class TestIsSlideArchiveSecurity:
    """Security tests for is_slide_archive() function."""

    def test_blocks_path_traversal_with_dots(self):
        """Test that path traversal with ../ is blocked."""
        result = is_slide_archive(Path("../../../etc/passwd"))
        assert result is False

    def test_blocks_path_traversal_with_backslash(self):
        r"""Test that path traversal with ..\ is blocked (Windows)."""
        result = is_slide_archive(Path("..\\..\\..\\etc\\passwd"))
        assert result is False

    def test_blocks_null_byte_injection(self):
        """Test that null byte injection is blocked."""
        result = is_slide_archive(Path("test\x00.zip"))
        assert result is False

    def test_blocks_absolute_path_outside_base(self):
        """Test that absolute paths outside MATERIALS_BASE are blocked."""
        result = is_slide_archive(Path("/etc/passwd"))
        assert result is False

    def test_blocks_nested_path_traversal(self):
        """Test that nested path traversal (valid/../../../etc) is blocked."""
        result = is_slide_archive(Path("Materials/../../../etc/passwd"))
        assert result is False

    def test_accepts_valid_relative_path(self, tmp_path):
        """Test that valid relative paths within MATERIALS_BASE are accepted."""
        # Create a valid ZIP file with manifest.json
        test_zip = tmp_path / "test_archive.zip"
        with zipfile.ZipFile(test_zip, 'w') as zf:
            zf.writestr('manifest.json', json.dumps({'pages': []}))
        
        # Mock MATERIALS_BASE to be tmp_path
        with patch('app.services.slide_archive.MATERIALS_BASE', tmp_path):
            result = is_slide_archive(test_zip)
            assert result is True

    def test_returns_false_for_nonexistent_file(self):
        """Test that nonexistent files return False (not an error)."""
        result = is_slide_archive(Path("nonexistent_file.zip"))
        assert result is False

    def test_returns_false_for_invalid_zip(self, tmp_path):
        """Test that invalid ZIP files return False."""
        # Create a file that's not a ZIP
        test_file = tmp_path / "not_a_zip.txt"
        test_file.write_text("This is not a ZIP file")
        
        with patch('app.services.slide_archive.MATERIALS_BASE', tmp_path):
            result = is_slide_archive(test_file)
            assert result is False

    def test_returns_false_for_zip_without_manifest(self, tmp_path):
        """Test that ZIP files without manifest.json return False."""
        test_zip = tmp_path / "no_manifest.zip"
        with zipfile.ZipFile(test_zip, 'w') as zf:
            zf.writestr('other_file.txt', 'content')
        
        with patch('app.services.slide_archive.MATERIALS_BASE', tmp_path):
            result = is_slide_archive(test_zip)
            assert result is False


class TestGetFileTypeSecurity:
    """Security tests for get_file_type() function."""

    def test_blocks_path_traversal(self):
        """Test that path traversal is blocked in get_file_type()."""
        result = get_file_type(Path("../../../etc/passwd"))
        assert result == 'unknown'

    def test_blocks_null_byte_injection(self):
        """Test that null byte injection is blocked."""
        result = get_file_type(Path("test\x00.pdf"))
        assert result == 'unknown'

    def test_blocks_absolute_path_outside_base(self):
        """Test that absolute paths outside MATERIALS_BASE are blocked."""
        result = get_file_type(Path("/tmp/malicious.pdf"))
        assert result == 'unknown'

    def test_accepts_valid_pdf_path(self, tmp_path):
        """Test that valid PDF paths are accepted."""
        # Create a valid PDF file
        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b'%PDF-1.4\n')
        
        with patch('app.services.slide_archive.MATERIALS_BASE', tmp_path):
            result = get_file_type(test_pdf)
            assert result == 'pdf'

    def test_accepts_valid_slide_archive_path(self, tmp_path):
        """Test that valid slide archive paths are accepted."""
        # Create a valid slide archive
        test_zip = tmp_path / "test_archive.zip"
        with zipfile.ZipFile(test_zip, 'w') as zf:
            zf.writestr('manifest.json', json.dumps({'pages': []}))
        
        with patch('app.services.slide_archive.MATERIALS_BASE', tmp_path):
            result = get_file_type(test_zip)
            assert result == 'slide_archive'

    def test_returns_unknown_for_nonexistent_file(self):
        """Test that nonexistent files return 'unknown'."""
        result = get_file_type(Path("nonexistent.pdf"))
        assert result == 'unknown'

    def test_returns_unknown_for_unsupported_type(self, tmp_path):
        """Test that unsupported file types return 'unknown'."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Not a PDF or slide archive")
        
        with patch('app.services.slide_archive.MATERIALS_BASE', tmp_path):
            result = get_file_type(test_file)
            assert result == 'unknown'


class TestExtractSlideArchiveSecurity:
    """Security tests for extract_slide_archive() function."""

    def test_blocks_path_traversal(self):
        """Test that path traversal is blocked in extract_slide_archive()."""
        result = extract_slide_archive(Path("../../../etc/passwd"))
        assert result is None

    def test_blocks_null_byte_injection(self):
        """Test that null byte injection is blocked."""
        result = extract_slide_archive(Path("test\x00.zip"))
        assert result is None

    def test_blocks_absolute_path_outside_base(self):
        """Test that absolute paths outside MATERIALS_BASE are blocked."""
        result = extract_slide_archive(Path("/tmp/malicious.zip"))
        assert result is None

    def test_accepts_valid_slide_archive(self, tmp_path):
        """Test that valid slide archives are extracted successfully."""
        # Create a valid slide archive
        test_zip = tmp_path / "test_archive.zip"
        manifest = {
            'num_pages': 2,
            'pages': [
                {
                    'page_number': 1,
                    'image': {'path': 'slide_1.png', 'dimensions': {'width': 800, 'height': 600}},
                    'text': {'path': 'slide_1.txt'},
                    'has_visual_content': True
                },
                {
                    'page_number': 2,
                    'image': {'path': 'slide_2.png', 'dimensions': {'width': 800, 'height': 600}},
                    'text': {'path': 'slide_2.txt'},
                    'has_visual_content': True
                }
            ]
        }
        
        with zipfile.ZipFile(test_zip, 'w') as zf:
            zf.writestr('manifest.json', json.dumps(manifest))
            zf.writestr('slide_1.txt', 'Slide 1 content')
            zf.writestr('slide_2.txt', 'Slide 2 content')
        
        with patch('app.services.slide_archive.MATERIALS_BASE', tmp_path):
            result = extract_slide_archive(test_zip, use_cache=False)
            assert result is not None
            assert result.num_pages == 2
            assert len(result.slides) == 2
            assert result.slides[0].text_content == 'Slide 1 content'
            assert result.slides[1].text_content == 'Slide 2 content'

    def test_returns_none_for_nonexistent_file(self):
        """Test that nonexistent files return None."""
        result = extract_slide_archive(Path("nonexistent.zip"))
        assert result is None

    def test_returns_none_for_invalid_archive(self, tmp_path):
        """Test that invalid archives return None."""
        # Create a file that's not a valid slide archive
        test_file = tmp_path / "not_archive.txt"
        test_file.write_text("Not a slide archive")
        
        with patch('app.services.slide_archive.MATERIALS_BASE', tmp_path):
            result = extract_slide_archive(test_file)
            assert result is None


class TestGetSlideImageSecurity:
    """Security tests for get_slide_image() function."""

    def test_blocks_path_traversal(self):
        """Test that path traversal is blocked in get_slide_image()."""
        from app.services.slide_archive import get_slide_image

        result = get_slide_image(Path("../../../etc/passwd"), 1)
        assert result is None

    def test_blocks_null_byte_injection(self):
        """Test that null byte injection is blocked."""
        from app.services.slide_archive import get_slide_image

        result = get_slide_image(Path("test\x00.zip"), 1)
        assert result is None

    def test_blocks_absolute_path_outside_base(self):
        """Test that absolute paths outside MATERIALS_BASE are blocked."""
        from app.services.slide_archive import get_slide_image

        result = get_slide_image(Path("/tmp/malicious.zip"), 1)
        assert result is None

    def test_accepts_valid_slide_archive(self, tmp_path):
        """Test that valid slide archives return images successfully."""
        from app.services.slide_archive import get_slide_image

        # Create a valid slide archive with an image
        test_zip = tmp_path / "test_archive.zip"
        manifest = {
            'num_pages': 1,
            'pages': [
                {
                    'page_number': 1,
                    'image': {
                        'path': 'slide_1.png',
                        'media_type': 'image/png',
                        'dimensions': {'width': 800, 'height': 600}
                    },
                    'text': {'path': 'slide_1.txt'},
                    'has_visual_content': True
                }
            ]
        }

        # Create a simple PNG image (1x1 pixel)
        png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde'

        with zipfile.ZipFile(test_zip, 'w') as zf:
            zf.writestr('manifest.json', json.dumps(manifest))
            zf.writestr('slide_1.png', png_data)

        with patch('app.services.slide_archive.MATERIALS_BASE', tmp_path):
            result = get_slide_image(test_zip, 1)
            assert result is not None
            image_bytes, media_type = result
            assert image_bytes == png_data
            assert media_type == 'image/png'

    def test_returns_none_for_nonexistent_file(self):
        """Test that nonexistent files return None."""
        from app.services.slide_archive import get_slide_image

        result = get_slide_image(Path("nonexistent.zip"), 1)
        assert result is None

    def test_returns_none_for_invalid_page_number(self, tmp_path):
        """Test that invalid page numbers return None."""
        from app.services.slide_archive import get_slide_image

        # Create a valid slide archive
        test_zip = tmp_path / "test_archive.zip"
        manifest = {
            'num_pages': 1,
            'pages': [
                {
                    'page_number': 1,
                    'image': {'path': 'slide_1.png', 'media_type': 'image/png'},
                    'text': {'path': 'slide_1.txt'}
                }
            ]
        }

        with zipfile.ZipFile(test_zip, 'w') as zf:
            zf.writestr('manifest.json', json.dumps(manifest))
            zf.writestr('slide_1.png', b'fake image data')

        with patch('app.services.slide_archive.MATERIALS_BASE', tmp_path):
            # Request page 999 which doesn't exist
            result = get_slide_image(test_zip, 999)
            assert result is None


class TestPathValidationConsistency:
    """Tests to ensure validated paths are used consistently."""

    def test_is_slide_archive_uses_validated_path(self, tmp_path):
        """Verify that is_slide_archive uses validated path, not original."""
        # Create a valid ZIP with manifest
        test_zip = tmp_path / "test.zip"
        with zipfile.ZipFile(test_zip, 'w') as zf:
            zf.writestr('manifest.json', json.dumps({'pages': []}))

        # Mock validate_path_within_base to return a different path
        mock_validated = tmp_path / "validated.zip"
        with zipfile.ZipFile(mock_validated, 'w') as zf:
            zf.writestr('manifest.json', json.dumps({'pages': []}))

        with patch('app.services.slide_archive.validate_path_within_base') as mock_validate:
            mock_validate.return_value = mock_validated

            result = is_slide_archive(test_zip)

            # Should use validated path (which has manifest)
            assert result is True
            mock_validate.assert_called_once_with(str(test_zip), MATERIALS_BASE)

    def test_get_file_type_uses_validated_path(self, tmp_path):
        """Verify that get_file_type uses validated path, not original."""
        # Create a PDF file
        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b'%PDF-1.4\n')
        
        # Mock validate_path_within_base to return a different path
        mock_validated = tmp_path / "validated.pdf"
        mock_validated.write_bytes(b'%PDF-1.4\n')
        
        with patch('app.services.slide_archive.validate_path_within_base') as mock_validate:
            mock_validate.return_value = mock_validated
            
            result = get_file_type(test_pdf)
            
            # Should use validated path (which is a PDF)
            assert result == 'pdf'
            mock_validate.assert_called_once_with(str(test_pdf), MATERIALS_BASE)

    def test_extract_slide_archive_uses_validated_path(self, tmp_path):
        """Verify that extract_slide_archive uses validated path, not original."""
        # Create a valid slide archive
        test_zip = tmp_path / "test.zip"
        manifest = {'num_pages': 1, 'pages': []}
        with zipfile.ZipFile(test_zip, 'w') as zf:
            zf.writestr('manifest.json', json.dumps(manifest))

        # Mock validate_path_within_base to return a different path
        mock_validated = tmp_path / "validated.zip"
        with zipfile.ZipFile(mock_validated, 'w') as zf:
            zf.writestr('manifest.json', json.dumps(manifest))

        with patch('app.services.slide_archive.validate_path_within_base') as mock_validate:
            mock_validate.return_value = mock_validated

            result = extract_slide_archive(test_zip, use_cache=False)

            # Should use validated path
            assert result is not None
            # Verify validate was called
            assert mock_validate.call_count >= 1  # Called in extract_slide_archive and is_slide_archive

    def test_get_slide_image_uses_validated_path(self, tmp_path):
        """Verify that get_slide_image uses validated path, not original."""
        from app.services.slide_archive import get_slide_image

        # Create a valid slide archive with image
        test_zip = tmp_path / "test.zip"
        manifest = {
            'pages': [{
                'page_number': 1,
                'image': {'path': 'slide_1.png', 'media_type': 'image/png'}
            }]
        }
        png_data = b'\x89PNG\r\n\x1a\n'

        with zipfile.ZipFile(test_zip, 'w') as zf:
            zf.writestr('manifest.json', json.dumps(manifest))
            zf.writestr('slide_1.png', png_data)

        # Mock validate_path_within_base to return a different path
        mock_validated = tmp_path / "validated.zip"
        with zipfile.ZipFile(mock_validated, 'w') as zf:
            zf.writestr('manifest.json', json.dumps(manifest))
            zf.writestr('slide_1.png', png_data)

        with patch('app.services.slide_archive.validate_path_within_base') as mock_validate:
            mock_validate.return_value = mock_validated

            result = get_slide_image(test_zip, 1)

            # Should use validated path
            assert result is not None
            image_bytes, media_type = result
            assert image_bytes == png_data
            assert media_type == 'image/png'
            # Verify validate was called
            mock_validate.assert_called_once_with(str(test_zip), MATERIALS_BASE)


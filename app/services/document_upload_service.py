"""Document Upload Service for Course Materials.

Handles file uploads to course material folders with:
- File validation (type, size)
- Storage path generation
- Automatic text extraction
- Firestore metadata storage
"""

import logging
import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

from app.models.course_models import UploadedMaterial, MaterialUploadResponse
from app.services.text_extractor import extract_text, detect_file_type

logger = logging.getLogger(__name__)

# Configuration
MATERIALS_ROOT = Path("Materials")
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Supported file types and their MIME types
SUPPORTED_TYPES = {
    'pdf': ['application/pdf'],
    'docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
    'doc': ['application/msword'],
    'pptx': ['application/vnd.openxmlformats-officedocument.presentationml.presentation'],
    'txt': ['text/plain'],
    'md': ['text/markdown', 'text/plain'],
    'html': ['text/html'],
    'png': ['image/png'],
    'jpg': ['image/jpeg'],
    'jpeg': ['image/jpeg'],
    'gif': ['image/gif'],
    'bmp': ['image/bmp'],
}

# Tier folder mapping
TIER_FOLDERS = {
    'syllabus': 'Syllabus',
    'course_materials': 'Course_Materials',
    'supplementary': 'Supplementary_Sources',
}

# Category subfolders for course_materials tier
CATEGORY_FOLDERS = {
    'lecture': 'Lectures',
    'reading': 'Readings',
    'case': 'Cases',
    'exam': 'Exams',
    'assignment': 'Assignments',
}


class UploadError(Exception):
    """Custom exception for upload errors."""
    pass


def validate_file(filename: str, file_size: int, content_type: Optional[str] = None) -> str:
    """Validate uploaded file.

    Args:
        filename: Original filename
        file_size: File size in bytes
        content_type: MIME type if provided

    Returns:
        Detected file extension

    Raises:
        UploadError: If validation fails
    """
    # Check file size
    if file_size > MAX_FILE_SIZE:
        raise UploadError(f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB")

    if file_size == 0:
        raise UploadError("Empty file")

    # Get extension
    ext = Path(filename).suffix.lower().lstrip('.')
    if not ext:
        raise UploadError("File must have an extension")

    # Check if extension is supported
    if ext not in SUPPORTED_TYPES:
        supported = ', '.join(SUPPORTED_TYPES.keys())
        raise UploadError(f"Unsupported file type: .{ext}. Supported: {supported}")

    # Validate MIME type if provided
    if content_type:
        expected_mimes = SUPPORTED_TYPES.get(ext, [])
        # Be lenient - some browsers send generic types
        if content_type not in expected_mimes and content_type != 'application/octet-stream':
            logger.warning(
                "MIME type mismatch: expected %s for .%s, got %s",
                expected_mimes, ext, content_type
            )

    return ext


def generate_storage_path(
    course_id: str,
    filename: str,
    tier: str = 'course_materials',
    category: Optional[str] = None
) -> Path:
    """Generate storage path for uploaded file.

    Args:
        course_id: Course identifier
        filename: Original filename
        tier: Material tier ('syllabus', 'course_materials', 'supplementary')
        category: Optional category for course_materials ('lecture', 'reading', etc.)

    Returns:
        Path where file should be stored
    """
    # Get tier folder
    tier_folder = TIER_FOLDERS.get(tier, 'Course_Materials')

    # Build path
    base_path = MATERIALS_ROOT / tier_folder / course_id

    # Add category subfolder if applicable
    if tier == 'course_materials' and category:
        category_folder = CATEGORY_FOLDERS.get(category, category.title())
        base_path = base_path / category_folder

    # Ensure unique filename
    safe_filename = sanitize_filename(filename)
    target_path = base_path / safe_filename

    # If file exists, add UUID suffix
    if target_path.exists():
        stem = target_path.stem
        suffix = target_path.suffix
        unique_id = uuid.uuid4().hex[:8]
        safe_filename = f"{stem}_{unique_id}{suffix}"
        target_path = base_path / safe_filename

    return target_path


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage.

    Removes or replaces unsafe characters while preserving readability.
    """
    # Keep alphanumeric, spaces, dots, hyphens, underscores
    safe_chars = []
    for char in filename:
        if char.isalnum() or char in ' .-_':
            safe_chars.append(char)
        elif char in '/\\:*?"<>|':
            safe_chars.append('_')

    result = ''.join(safe_chars).strip()

    # Ensure not empty
    if not result or result == '.':
        result = f"file_{uuid.uuid4().hex[:8]}"

    return result


async def save_uploaded_file(
    file_content: bytes,
    filename: str,
    course_id: str,
    tier: str = 'course_materials',
    category: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    week_number: Optional[int] = None,
    content_type: Optional[str] = None
) -> UploadedMaterial:
    """Save uploaded file and extract text.

    Args:
        file_content: Raw file bytes
        filename: Original filename
        course_id: Course to associate with
        tier: Material tier
        category: Material category
        title: Display title
        description: Material description
        week_number: Associated week number
        content_type: MIME type

    Returns:
        UploadedMaterial record

    Raises:
        UploadError: If upload fails
    """
    # Validate file
    file_ext = validate_file(filename, len(file_content), content_type)

    # Generate storage path
    storage_path = generate_storage_path(course_id, filename, tier, category)

    # Create directories
    storage_path.parent.mkdir(parents=True, exist_ok=True)

    # Save file
    try:
        storage_path.write_bytes(file_content)
        logger.info("Saved file to %s", storage_path)
    except Exception as e:
        raise UploadError(f"Failed to save file: {e}") from e

    # Detect file type for extraction
    detected_type = detect_file_type(storage_path)

    # Extract text
    extraction_result = extract_text(storage_path)

    # Determine MIME type
    mime_type = content_type or mimetypes.guess_type(filename)[0] or 'application/octet-stream'

    # Create material record
    material = UploadedMaterial(
        id=str(uuid.uuid4()),
        filename=filename,
        storagePath=str(storage_path),
        tier=tier,
        category=category,
        fileType=detected_type,
        fileSize=len(file_content),
        mimeType=mime_type,
        uploadedAt=datetime.now(timezone.utc),
        textExtracted=extraction_result.success,
        extractedText=extraction_result.text if extraction_result.success else None,
        textLength=len(extraction_result.text) if extraction_result.success else None,
        extractionError=extraction_result.error if not extraction_result.success else None,
        pageCount=extraction_result.metadata.get('num_pages') if extraction_result.metadata else None,
        title=title or filename,
        description=description,
        weekNumber=week_number,
    )

    return material


async def delete_material_file(storage_path: str) -> bool:
    """Delete a material file from storage.

    Args:
        storage_path: Path to the file

    Returns:
        True if deleted, False if not found
    """
    path = Path(storage_path)
    if path.exists():
        try:
            path.unlink()
            logger.info("Deleted file: %s", storage_path)

            # Clean up empty parent directories
            parent = path.parent
            while parent != MATERIALS_ROOT and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent

            return True
        except Exception as e:
            logger.error("Failed to delete file %s: %s", storage_path, e)
            raise UploadError(f"Failed to delete file: {e}") from e
    return False


def list_course_materials(course_id: str) -> List[Dict[str, Any]]:
    """List all material files for a course.

    Scans the Materials folders for files belonging to the course.

    Args:
        course_id: Course identifier

    Returns:
        List of material info dicts
    """
    materials = []

    for tier, folder in TIER_FOLDERS.items():
        course_folder = MATERIALS_ROOT / folder / course_id
        if course_folder.exists():
            for file_path in course_folder.rglob('*'):
                if file_path.is_file():
                    # Determine category from path
                    category = None
                    if tier == 'course_materials':
                        relative = file_path.relative_to(course_folder)
                        if len(relative.parts) > 1:
                            category = relative.parts[0].lower()

                    materials.append({
                        'path': str(file_path),
                        'filename': file_path.name,
                        'tier': tier,
                        'category': category,
                        'size': file_path.stat().st_size,
                        'modified': datetime.fromtimestamp(
                            file_path.stat().st_mtime,
                            tz=timezone.utc
                        ).isoformat(),
                    })

    return materials


def get_supported_extensions() -> List[str]:
    """Get list of supported file extensions."""
    return list(SUPPORTED_TYPES.keys())


def get_tier_options() -> List[Dict[str, str]]:
    """Get available tier options for UI."""
    return [
        {'value': 'syllabus', 'label': 'Syllabus'},
        {'value': 'course_materials', 'label': 'Course Materials'},
        {'value': 'supplementary', 'label': 'Supplementary Sources'},
    ]


def get_category_options() -> List[Dict[str, str]]:
    """Get available category options for UI."""
    return [
        {'value': 'lecture', 'label': 'Lecture'},
        {'value': 'reading', 'label': 'Reading'},
        {'value': 'case', 'label': 'Case Study'},
        {'value': 'exam', 'label': 'Exam/Practice'},
        {'value': 'assignment', 'label': 'Assignment'},
    ]

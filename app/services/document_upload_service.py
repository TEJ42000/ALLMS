"""Document Upload Service.

Handles file uploads for course materials:
- File validation (type, size)
- Storage in Materials folder structure
- Text extraction using TextExtractor
- Metadata storage in Firestore
"""

import logging
import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from app.models.course_models import UploadedMaterial
from app.services.text_extractor import extract_text, detect_file_type
from app.services.gcp_service import get_firestore_client

logger = logging.getLogger(__name__)

# Configuration
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MATERIALS_ROOT = Path("Materials")

# Supported file types
SUPPORTED_EXTENSIONS = {
    'pdf', 'docx', 'pptx',  # Documents
    'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp',  # Images
    'txt', 'md', 'html', 'htm',  # Text
}

# Tier to folder mapping
TIER_FOLDERS = {
    'syllabus': 'Syllabus',
    'course_materials': 'Course_Materials',
    'supplementary': 'Supplementary_Sources',
}

# Category to subfolder mapping (for course_materials tier)
CATEGORY_FOLDERS = {
    'lecture': 'Lectures',
    'reading': 'Readings',
    'case': 'Cases',
}


class DocumentUploadError(Exception):
    """Base exception for document upload errors."""
    pass


class FileValidationError(DocumentUploadError):
    """File validation failed."""
    pass


class StorageError(DocumentUploadError):
    """File storage failed."""
    pass


class ExtractionError(DocumentUploadError):
    """Text extraction failed."""
    pass


def validate_file(
    filename: str,
    file_size: int,
    allowed_extensions: Optional[set] = None
) -> Tuple[str, str]:
    """Validate uploaded file.
    
    Args:
        filename: Original filename
        file_size: File size in bytes
        allowed_extensions: Set of allowed extensions (default: SUPPORTED_EXTENSIONS)
    
    Returns:
        Tuple of (file_extension, mime_type)
    
    Raises:
        FileValidationError: If validation fails
    """
    if allowed_extensions is None:
        allowed_extensions = SUPPORTED_EXTENSIONS
    
    # Check file size
    if file_size > MAX_FILE_SIZE:
        raise FileValidationError(
            f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds maximum "
            f"allowed size ({MAX_FILE_SIZE / 1024 / 1024:.0f}MB)"
        )
    
    if file_size == 0:
        raise FileValidationError("File is empty")
    
    # Check extension
    file_path = Path(filename)
    extension = file_path.suffix.lower().lstrip('.')
    
    if not extension:
        raise FileValidationError("File has no extension")
    
    if extension not in allowed_extensions:
        raise FileValidationError(
            f"File type '.{extension}' is not supported. "
            f"Allowed types: {', '.join(sorted(allowed_extensions))}"
        )
    
    # Get MIME type
    mime_type, _ = mimetypes.guess_type(filename)
    if not mime_type:
        mime_type = 'application/octet-stream'
    
    return extension, mime_type


def generate_storage_path(
    course_id: str,
    filename: str,
    tier: str,
    category: Optional[str] = None
) -> Path:
    """Generate storage path for uploaded file.
    
    Args:
        course_id: Course ID
        filename: Original filename
        tier: Material tier ('syllabus', 'course_materials', 'supplementary')
        category: Optional category for course_materials tier
    
    Returns:
        Path object for storage location
    
    Raises:
        ValueError: If tier or category is invalid
    """
    if tier not in TIER_FOLDERS:
        raise ValueError(f"Invalid tier: {tier}. Must be one of {list(TIER_FOLDERS.keys())}")
    
    # Start with tier folder
    tier_folder = TIER_FOLDERS[tier]
    path_parts = [MATERIALS_ROOT, tier_folder]
    
    # Add course ID
    path_parts.append(course_id)
    
    # Add category subfolder if specified (for course_materials)
    if tier == 'course_materials' and category:
        if category not in CATEGORY_FOLDERS:
            raise ValueError(
                f"Invalid category: {category}. "
                f"Must be one of {list(CATEGORY_FOLDERS.keys())}"
            )
        path_parts.append(CATEGORY_FOLDERS[category])
    
    # Add filename
    path_parts.append(filename)
    
    return Path(*path_parts)


def ensure_directory(file_path: Path) -> None:
    """Ensure directory exists for file path.
    
    Args:
        file_path: Full file path
    """
    directory = file_path.parent
    directory.mkdir(parents=True, exist_ok=True)
    logger.info(f"Ensured directory exists: {directory}")


async def save_file(
    file_content: bytes,
    storage_path: Path
) -> None:
    """Save file to storage.
    
    Args:
        file_content: File content as bytes
        storage_path: Path where file should be saved
    
    Raises:
        StorageError: If file save fails
    """
    try:
        ensure_directory(storage_path)
        storage_path.write_bytes(file_content)
        logger.info(f"Saved file to: {storage_path}")
    except Exception as e:
        logger.error(f"Failed to save file to {storage_path}: {e}")
        raise StorageError(f"Failed to save file: {str(e)}")


def extract_text_from_file(file_path: Path) -> Tuple[bool, Optional[str], Optional[str]]:
    """Extract text from uploaded file.
    
    Args:
        file_path: Path to file
    
    Returns:
        Tuple of (success, extracted_text, error_message)
    """
    try:
        result = extract_text(file_path)
        
        if result.success:
            return True, result.text, None
        else:
            return False, None, result.error
    
    except Exception as e:
        logger.error(f"Text extraction failed for {file_path}: {e}")
        return False, None, str(e)


# Summary generation settings
MAX_TEXT_FOR_SUMMARY = 50000  # Max characters to send to LLM for summarization
SUMMARY_MAX_TOKENS = 300  # Max tokens for summary response


async def generate_document_summary(
    extracted_text: str,
    filename: str,
    tier: str,
    category: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """Generate an AI summary of the document content.

    Args:
        extracted_text: The extracted text from the document
        filename: Original filename for context
        tier: Material tier for context
        category: Optional category for context

    Returns:
        Tuple of (success, summary_text)
    """
    if not extracted_text or len(extracted_text.strip()) < 100:
        logger.debug(f"Text too short for summary: {len(extracted_text) if extracted_text else 0} chars")
        return False, None

    try:
        from app.services.anthropic_client import get_simple_response

        # Truncate text if too long
        text_for_summary = extracted_text[:MAX_TEXT_FOR_SUMMARY]
        if len(extracted_text) > MAX_TEXT_FOR_SUMMARY:
            text_for_summary += "\n\n[Text truncated for summarization...]"

        # Build context
        context_parts = [f"Document: {filename}"]
        if tier:
            context_parts.append(f"Type: {tier.replace('_', ' ').title()}")
        if category:
            context_parts.append(f"Category: {category.title()}")
        context = " | ".join(context_parts)

        # Create prompt
        prompt = f"""Summarize the following document in 2-4 sentences. Focus on the main topics, key concepts, and purpose of the document. Be concise and informative.

{context}

Document content:
{text_for_summary}

Summary:"""

        summary = await get_simple_response(
            prompt=prompt,
            max_tokens=SUMMARY_MAX_TOKENS,
            temperature=0.3  # Lower temperature for more focused summaries
        )

        # Clean up the summary
        summary = summary.strip()

        logger.info(f"Generated summary for {filename}: {len(summary)} chars")
        return True, summary

    except Exception as e:
        logger.error(f"Failed to generate summary for {filename}: {e}")
        return False, None


async def store_material_metadata(
    course_id: str,
    material: UploadedMaterial
) -> None:
    """Store material metadata in Firestore.
    
    Args:
        course_id: Course ID
        material: UploadedMaterial object
    
    Raises:
        StorageError: If Firestore storage fails
    """
    try:
        db = get_firestore_client()
        
        # Store in uploadedMaterials subcollection
        doc_ref = db.collection('courses').document(course_id).collection('uploadedMaterials').document(material.id)
        
        # Convert to dict
        material_dict = material.model_dump(mode='json')
        
        doc_ref.set(material_dict)
        logger.info(f"Stored material metadata for {material.id} in course {course_id}")
    
    except Exception as e:
        logger.error(f"Failed to store material metadata: {e}")
        raise StorageError(f"Failed to store metadata: {str(e)}")


async def upload_document(
    course_id: str,
    filename: str,
    file_content: bytes,
    tier: str,
    category: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    week_number: Optional[int] = None,
    uploaded_by: Optional[str] = None,
    extract_text_flag: bool = True,
    generate_summary_flag: bool = True
) -> UploadedMaterial:
    """Upload a document to course materials.

    Args:
        course_id: Course ID
        filename: Original filename
        file_content: File content as bytes
        tier: Material tier ('syllabus', 'course_materials', 'supplementary')
        category: Optional category for course_materials tier
        title: Optional display title
        description: Optional description
        week_number: Optional week number to link to
        uploaded_by: Optional user ID
        extract_text_flag: Whether to extract text (default: True)
        generate_summary_flag: Whether to generate AI summary (default: True)

    Returns:
        UploadedMaterial object

    Raises:
        FileValidationError: If file validation fails
        StorageError: If file storage fails
    """
    # Validate file
    file_extension, mime_type = validate_file(filename, len(file_content))

    # Generate unique ID
    material_id = str(uuid.uuid4())

    # Generate storage path
    storage_path = generate_storage_path(course_id, filename, tier, category)

    # Save file
    await save_file(file_content, storage_path)

    # Detect file type
    file_type = detect_file_type(storage_path)

    # Extract text if requested
    text_extracted = False
    extracted_text = None
    text_length = None
    extraction_error = None

    if extract_text_flag:
        success, text, error = extract_text_from_file(storage_path)
        text_extracted = success
        extracted_text = text
        text_length = len(text) if text else None
        extraction_error = error

    # Generate AI summary if text was extracted and summary requested
    summary = None
    summary_generated = False

    if generate_summary_flag and text_extracted and extracted_text:
        summary_success, summary_text = await generate_document_summary(
            extracted_text=extracted_text,
            filename=filename,
            tier=tier,
            category=category
        )
        if summary_success:
            summary = summary_text
            summary_generated = True

    # Create material object
    material = UploadedMaterial(
        id=material_id,
        filename=filename,
        storagePath=str(storage_path),
        tier=tier,
        category=category,
        fileType=file_type,
        fileSize=len(file_content),
        mimeType=mime_type,
        uploadedAt=datetime.now(timezone.utc),
        uploadedBy=uploaded_by,
        textExtracted=text_extracted,
        extractedText=extracted_text,
        textLength=text_length,
        extractionError=extraction_error,
        title=title or filename,
        description=description,
        weekNumber=week_number,
        summary=summary,
        summaryGenerated=summary_generated
    )

    # Store metadata in Firestore
    await store_material_metadata(course_id, material)

    logger.info(f"Successfully uploaded document: {filename} to {storage_path}")

    return material


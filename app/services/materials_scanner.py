"""Materials Scanner Service for Course Management.

Scans course material folders and extracts metadata from files.
Can optionally use Anthropic API to generate better titles from filenames.
"""

import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from app.services.gcp_service import get_anthropic_api_key
from app.services.usage_tracking_service import get_usage_tracking_service

logger = logging.getLogger(__name__)


async def _track_system_usage(
    response,
    model: str,
    operation_type: str,
) -> None:
    """Track usage for system operations (no user context)."""
    try:
        usage = response.usage
        await get_usage_tracking_service().record_usage(
            user_email="system@internal",
            user_id="system",
            model=model,
            operation_type=operation_type,
            input_tokens=getattr(usage, 'input_tokens', 0) or 0,
            output_tokens=getattr(usage, 'output_tokens', 0) or 0,
            cache_creation_tokens=getattr(usage, 'cache_creation_input_tokens', 0) or 0,
            cache_read_tokens=getattr(usage, 'cache_read_input_tokens', 0) or 0,
            course_id=None,
            request_metadata={"source": "materials_scanner"},
        )
    except Exception as e:
        logger.warning("Failed to track system usage: %s", e)

# Base path for materials
MATERIALS_BASE = Path("Materials/Course_Materials")

# Folders to skip when scanning
SKIP_FOLDERS = {"LLS Essential", "__pycache__", ".git", ".DS_Store"}

# File extensions to include
VALID_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md"}


class ScannedMaterial(BaseModel):
    """A material discovered during folder scan."""
    file: str  # Relative path from Materials/Course_Materials/{subject}/
    filename: str
    category: str  # Folder name (e.g., "Lectures", "Readings", "Core_Materials")
    size_bytes: int
    title: Optional[str] = None  # AI-generated or parsed from filename
    week: Optional[int] = None  # Extracted week number if present
    material_type: str = "other"  # lecture, reading, textbook, case, exam, etc.


class ScanResult(BaseModel):
    """Result of scanning a course's material folders."""
    subject: str
    total_files: int
    materials: List[ScannedMaterial]
    categories: Dict[str, int]  # Category name -> file count


def _extract_week_from_filename(filename: str) -> Optional[int]:
    """Try to extract week number from filename."""
    # Common patterns: week_1, week1, wk1, wk_1, week 1
    # Must be careful about patterns like "2020week202" which is week 2, not 202
    patterns = [
        r'week[_\s]?(\d{1,2})(?!\d)',  # week_1, week1, week 12 (1-2 digits, not followed by more)
        r'wk[_\s]?(\d{1,2})(?!\d)',     # wk1, wk_1 (1-2 digits)
        r'_w(\d{1,2})(?!\d)',           # _w1, _w12 (1-2 digits)
    ]
    for pattern in patterns:
        match = re.search(pattern, filename.lower())
        if match:
            week = int(match.group(1))
            if 1 <= week <= 52:  # Valid week range
                return week
    return None


def _guess_material_type(category: str, filename: str) -> str:
    """Guess material type based on folder and filename."""
    category_lower = category.lower()
    filename_lower = filename.lower()
    
    if "lecture" in category_lower or "lecture" in filename_lower:
        return "lecture"
    elif "reading" in category_lower:
        return "reading"
    elif "core" in category_lower or "textbook" in filename_lower or "reader" in filename_lower:
        return "textbook"
    elif "case" in category_lower or "case" in filename_lower:
        return "case_study"
    elif "exam" in category_lower or "mock" in filename_lower:
        return "exam"
    elif "notes" in filename_lower:
        return "notes"
    elif "study" in category_lower or "guide" in filename_lower:
        return "study_guide"
    return "other"


def _clean_filename_to_title(filename: str) -> str:
    """Convert filename to a readable title."""
    # Remove extension
    name = os.path.splitext(filename)[0]
    # Replace underscores and multiple spaces
    name = re.sub(r'[_]+', ' ', name)
    name = re.sub(r'%20', ' ', name)
    name = re.sub(r'20(\d{2})(\d{2})', r'\1-\2', name)  # Fix year patterns like 2025-2026
    # Clean up extra spaces
    name = re.sub(r'\s+', ' ', name).strip()
    # Title case
    return name.title()


def scan_materials_folder(subject: str) -> ScanResult:
    """
    Scan a subject folder for materials.
    
    Args:
        subject: Subject folder name (e.g., "LLS", "Criminal_Law")
        
    Returns:
        ScanResult with all discovered materials
    """
    subject_path = MATERIALS_BASE / subject
    
    if not subject_path.exists():
        logger.warning("Subject folder not found: %s", subject_path)
        return ScanResult(subject=subject, total_files=0, materials=[], categories={})
    
    materials: List[ScannedMaterial] = []
    categories: Dict[str, int] = {}
    
    # Walk through all subdirectories
    for root, dirs, files in os.walk(subject_path):
        # Skip folders in SKIP_FOLDERS
        dirs[:] = [d for d in dirs if d not in SKIP_FOLDERS]
        
        root_path = Path(root)
        category = root_path.relative_to(subject_path).parts[0] if root_path != subject_path else "Root"
        
        # Skip if we're in a skip folder
        if any(skip in str(root_path) for skip in SKIP_FOLDERS):
            continue
            
        for filename in files:
            # Check extension
            ext = os.path.splitext(filename)[1].lower()
            if ext not in VALID_EXTENSIONS:
                continue
                
            file_path = root_path / filename
            relative_path = file_path.relative_to(subject_path)
            
            # Get file size
            try:
                size = file_path.stat().st_size
            except OSError:
                size = 0
            
            material = ScannedMaterial(
                file=str(relative_path),
                filename=filename,
                category=category,
                size_bytes=size,
                title=_clean_filename_to_title(filename),
                week=_extract_week_from_filename(filename),
                material_type=_guess_material_type(category, filename)
            )
            materials.append(material)
            categories[category] = categories.get(category, 0) + 1
    
    return ScanResult(
        subject=subject,
        total_files=len(materials),
        materials=materials,
        categories=categories
    )


async def enhance_titles_with_ai(materials: List[ScannedMaterial]) -> List[ScannedMaterial]:
    """
    Use Anthropic API to generate better titles from filenames.

    Args:
        materials: List of scanned materials with basic titles

    Returns:
        Materials with AI-enhanced titles
    """
    if not materials:
        return materials

    try:
        client = AsyncAnthropic(api_key=get_anthropic_api_key())

        # Build prompt with all filenames
        filenames = [m.filename for m in materials]
        prompt = f"""Given these academic course material filenames, generate clear, human-readable titles.

Filenames:
{chr(10).join(f'{i+1}. {fn}' for i, fn in enumerate(filenames))}

For each filename, provide a clean title that:
- Removes file extensions and underscores
- Fixes encoding issues (like %20 for spaces)
- Expands abbreviations if obvious
- Keeps week numbers if present (e.g., "Week 3: Administrative Law")
- Is concise but descriptive

Respond with ONLY numbered titles, one per line:
1. [title for first file]
2. [title for second file]
..."""

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        # Track system usage
        await _track_system_usage(
            response=response,
            model="claude-sonnet-4-20250514",
            operation_type="title_enhancement",
        )

        # Parse response
        text = response.content[0].text
        lines = [line.strip() for line in text.strip().split('\n') if line.strip()]

        for i, line in enumerate(lines):
            if i < len(materials):
                # Remove numbering prefix like "1. "
                title = re.sub(r'^\d+\.\s*', '', line)
                materials[i].title = title

    except Exception as e:
        logger.warning("AI title enhancement failed, using basic titles: %s", e)

    return materials


def convert_to_materials_registry(scan_result: ScanResult) -> Dict:
    """
    Convert scan result to MaterialsRegistry format for Firestore.

    Args:
        scan_result: Result from scan_materials_folder

    Returns:
        Dictionary matching MaterialsRegistry structure
    """
    registry = {
        "coreTextbooks": [],
        "lectures": [],
        "readings": [],
        "caseStudies": [],
        "mockExams": [],
        "other": []
    }

    for mat in scan_result.materials:
        size_mb = f"{mat.size_bytes / (1024 * 1024):.1f}MB"

        if mat.material_type == "textbook":
            registry["coreTextbooks"].append({
                "title": mat.title,
                "file": mat.file,
                "size": size_mb,
                "type": "primary" if "reader" in mat.filename.lower() else "supplementary",
                "description": ""
            })
        elif mat.material_type == "lecture":
            registry["lectures"].append({
                "title": mat.title,
                "week": mat.week,  # None if no week detected - course-wide material
                "file": mat.file,
                "size": size_mb
            })
        elif mat.material_type == "reading":
            registry["readings"].append({
                "title": mat.title,
                "week": mat.week,  # None if no week detected - course-wide material
                "file": mat.file,
                "size": size_mb
            })
        elif mat.material_type == "case_study":
            registry["caseStudies"].append({
                "title": mat.title,
                "court": "",
                "file": mat.file,
                "size": size_mb,
                "relevantRights": [],
                "topics": []
            })
        elif mat.material_type == "exam":
            registry["mockExams"].append({
                "title": mat.title,
                "file": mat.file,
                "size": size_mb,
                "type": "practice"
            })
        else:
            registry["other"].append({
                "title": mat.title,
                "file": mat.file,
                "size": size_mb,
                "category": mat.category
            })

    return registry


def convert_to_course_materials(
    scan_result: ScanResult,
    subject: str
) -> List["CourseMaterial"]:
    """Convert scan result to unified CourseMaterial objects.

    Args:
        scan_result: Result from scan_materials_folder
        subject: The subject/folder name being scanned

    Returns:
        List of CourseMaterial objects ready for Firestore
    """
    from datetime import datetime, timezone
    from app.models.course_models import CourseMaterial
    from app.services.course_materials_service import generate_material_id

    materials = []
    now = datetime.now(timezone.utc)

    for mat in scan_result.materials:
        # Build full storage path relative to Materials/
        storage_path = f"Course_Materials/{subject}/{mat.file}"
        material_id = generate_material_id(storage_path)

        # Map material_type to category
        category_map = {
            "textbook": "textbook",
            "lecture": "lecture",
            "reading": "reading",
            "case_study": "case",
            "exam": "exam",
            "other": "other"
        }
        category = category_map.get(mat.material_type, "other")

        # Detect file type from extension
        ext = Path(mat.filename).suffix.lower()
        file_type_map = {
            ".pdf": "pdf",
            ".docx": "docx",
            ".doc": "docx",
            ".txt": "text",
            ".md": "markdown",
            ".zip": "slide_archive"
        }
        file_type = file_type_map.get(ext, "unknown")

        course_material = CourseMaterial(
            id=material_id,
            filename=mat.filename,
            storagePath=storage_path,
            fileSize=mat.size_bytes,
            fileType=file_type,
            mimeType=None,  # Will be detected on access
            tier="course_materials",
            category=category,
            title=mat.title or mat.filename,
            description=None,
            weekNumber=mat.week,
            source="scanned",
            uploadedBy=None,
            textExtracted=False,
            extractedText=None,
            textLength=0,
            extractionError=None,
            summary=None,
            summaryGenerated=False,
            createdAt=now,
            updatedAt=now
        )
        materials.append(course_material)

    return materials


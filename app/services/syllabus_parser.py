"""
Syllabus PDF parser service.

Extracts text from PDF syllabi for AI-based course data extraction.
"""

import logging
import os
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# Base path for materials (same as materials_scanner.py)
MATERIALS_BASE = Path("Materials").resolve()


def validate_path_within_base(user_path: str, base_path: Path) -> Path:
    """
    Validate that a user-provided path is within the allowed base directory.

    This function prevents path traversal attacks by ensuring the resolved
    path is within the base directory.

    Args:
        user_path: User-provided path (relative to base_path)
        base_path: The base directory that paths must be within

    Returns:
        Resolved absolute path

    Raises:
        ValueError: If path is invalid or outside base directory
    """
    # Reject paths with null bytes (can bypass some checks)
    if "\x00" in user_path:
        raise ValueError("Invalid path: null bytes not allowed")

    # Build the path and resolve it
    try:
        full_path = (base_path / user_path).resolve()
    except (ValueError, OSError) as e:
        raise ValueError(f"Invalid path: {e}")

    # Security: Ensure the resolved path is under base_path
    # Using relative_to() raises ValueError if path is not under base_path
    try:
        full_path.relative_to(base_path)
    except ValueError:
        # Path is not under base_path - potential path traversal
        logger.warning("Path traversal attempt blocked: %s -> %s", user_path, full_path)
        raise ValueError("Access denied: path outside allowed directory")

    return full_path


def get_syllabus_directory() -> Path:
    """Get the syllabus directory path."""
    return MATERIALS_BASE / "Syllabus"


def scan_syllabi(subject: Optional[str] = None) -> list[dict]:
    """
    Scan for syllabus folders in the Materials/Syllabus directory.

    Args:
        subject: Optional subject folder to scan. If None, scans all subjects.

    Returns:
        List of syllabus folder info dicts with keys: subject, path, files, total_pages
    """
    syllabus_dir = get_syllabus_directory()

    if not syllabus_dir.exists():
        return []

    results = []

    # Get subjects to scan
    if subject:
        # Validate subject to prevent path traversal
        # Subject should be a simple folder name, not a path
        if "/" in subject or "\\" in subject or ".." in subject:
            logger.warning("Invalid subject name rejected: %s", subject)
            return []
        try:
            # Validate the full path is within syllabus directory
            subj_dir = validate_path_within_base(subject, syllabus_dir)
            subjects = [subject]
        except ValueError:
            logger.warning("Subject path validation failed: %s", subject)
            return []
    else:
        subjects = [d.name for d in syllabus_dir.iterdir() if d.is_dir()]

    for subj in subjects:
        # For user-provided subjects, we already validated above
        # For auto-discovered subjects, they come from iterdir() so are safe
        if subject:
            subj_dir = syllabus_dir / subj  # Already validated
        else:
            subj_dir = syllabus_dir / subj
        if not subj_dir.exists():
            continue

        # Find all PDFs in this folder
        pdf_files = []
        total_pages = 0

        for pdf_file in subj_dir.glob("*.pdf"):
            try:
                doc = fitz.open(pdf_file)
                page_count = len(doc)
                doc.close()

                pdf_files.append({
                    "filename": pdf_file.name,
                    "path": str(pdf_file.relative_to(MATERIALS_BASE)),
                    "pages": page_count
                })
                total_pages += page_count
            except Exception as e:
                # Skip files that can't be opened
                continue

        if pdf_files:  # Only include folders with PDFs
            results.append({
                "subject": subj,
                "path": f"Syllabus/{subj}",
                "files": pdf_files,
                "total_pages": total_pages
            })

    return results


def extract_text_from_folder(
    folder_path: str,
    max_pages_per_file: Optional[int] = None,
    return_details: bool = False
) -> str | dict:
    """
    Extract text from all PDF files in a folder.

    Args:
        folder_path: Path to the folder (relative to materials base or absolute)
        max_pages_per_file: Maximum number of pages to extract per file (None = all pages)
        return_details: If True, return dict with text and file info. If False, return only text.

    Returns:
        If return_details=False: Combined extracted text from all PDFs
        If return_details=True: Dict with {text, files, folder_path}
    """
    # Security: Validate path to prevent path traversal attacks (CWE-22/23/36)
    # Use validate_path_within_base() to ensure all paths are within MATERIALS_BASE
    try:
        full_path = validate_path_within_base(folder_path, MATERIALS_BASE)
    except ValueError as e:
        # Re-raise as FileNotFoundError to maintain API compatibility
        # but log the security event
        logger.warning("Path validation failed for folder_path=%s: %s", folder_path, e)
        raise FileNotFoundError(f"Invalid folder path: {folder_path}") from e

    # lgtm[py/path-injection] - full_path is sanitized by validate_path_within_base()
    if not full_path.exists() or not full_path.is_dir():  # CodeQL: path validated above
        raise FileNotFoundError(f"Folder not found: {full_path}")

    # Find all PDFs and sort by name for consistent ordering
    # lgtm[py/path-injection] - full_path is sanitized by validate_path_within_base()
    pdf_files = sorted(full_path.glob("*.pdf"))  # CodeQL: path validated above

    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in: {full_path}")

    all_text_parts = []
    file_names = []

    for pdf_file in pdf_files:
        try:
            doc = fitz.open(pdf_file)
            pages_to_extract = min(len(doc), max_pages_per_file) if max_pages_per_file else len(doc)
            file_names.append(pdf_file.name)

            all_text_parts.append(f"\n{'='*60}\n=== FILE: {pdf_file.name} ===\n{'='*60}\n")

            for i in range(pages_to_extract):
                page = doc[i]
                text = page.get_text()
                all_text_parts.append(f"=== Page {i + 1} ===\n{text}")

            doc.close()
        except Exception as e:
            all_text_parts.append(f"\n[Error reading {pdf_file.name}: {str(e)}]\n")

    combined_text = "\n\n".join(all_text_parts)

    if return_details:
        return {
            "text": combined_text,
            "files": file_names,
            "folder_path": folder_path
        }
    return combined_text


def extract_text_from_pdf(pdf_path: str, max_pages: Optional[int] = None) -> str:
    """
    Extract text content from a PDF file.

    Args:
        pdf_path: Path to the PDF file (relative to materials base or absolute)
        max_pages: Maximum number of pages to extract (None = all pages)

    Returns:
        Extracted text content
    """
    # Security: Validate path to prevent path traversal attacks (CWE-22/23/36)
    # Use validate_path_within_base() to ensure all paths are within MATERIALS_BASE
    try:
        full_path = validate_path_within_base(pdf_path, MATERIALS_BASE)
    except ValueError as e:
        # Re-raise as FileNotFoundError to maintain API compatibility
        logger.warning("Path validation failed for pdf_path=%s: %s", pdf_path, e)
        raise FileNotFoundError(f"Invalid PDF path: {pdf_path}") from e

    if not full_path.exists():
        raise FileNotFoundError(f"PDF not found: {full_path}")
    
    doc = fitz.open(full_path)
    
    try:
        text_parts = []
        pages_to_extract = min(len(doc), max_pages) if max_pages else len(doc)
        
        for i in range(pages_to_extract):
            page = doc[i]
            text = page.get_text()
            text_parts.append(f"=== Page {i + 1} ===\n{text}")
        
        return "\n\n".join(text_parts)
    finally:
        doc.close()


def extract_syllabus_text(subject: str, filename: str) -> str:
    """
    Extract text from a syllabus PDF.
    
    Args:
        subject: Subject folder name (e.g., "LLS")
        filename: PDF filename
        
    Returns:
        Extracted text content
    """
    pdf_path = f"Syllabus/{subject}/{filename}"
    return extract_text_from_pdf(pdf_path)


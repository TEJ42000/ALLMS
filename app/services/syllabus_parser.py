"""
Syllabus PDF parser service.

Extracts text from PDF syllabi for AI-based course data extraction.
"""

import os
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

# Base path for materials (same as materials_scanner.py)
MATERIALS_BASE = Path("Materials")


def get_syllabus_directory() -> Path:
    """Get the syllabus directory path."""
    return MATERIALS_BASE / "Syllabus"


def scan_syllabi(subject: Optional[str] = None) -> list[dict]:
    """
    Scan for syllabus PDFs in the Materials/Syllabus directory.
    
    Args:
        subject: Optional subject folder to scan. If None, scans all subjects.
        
    Returns:
        List of syllabus info dicts with keys: subject, filename, path, pages
    """
    syllabus_dir = get_syllabus_directory()
    
    if not syllabus_dir.exists():
        return []
    
    results = []
    
    # Get subjects to scan
    if subject:
        subjects = [subject]
    else:
        subjects = [d.name for d in syllabus_dir.iterdir() if d.is_dir()]
    
    for subj in subjects:
        subj_dir = syllabus_dir / subj
        if not subj_dir.exists():
            continue
            
        for pdf_file in subj_dir.glob("*.pdf"):
            try:
                doc = fitz.open(pdf_file)
                page_count = len(doc)
                doc.close()
                
                results.append({
                    "subject": subj,
                    "filename": pdf_file.name,
                    "path": str(pdf_file.relative_to(MATERIALS_BASE)),
                    "pages": page_count
                })
            except Exception as e:
                # Skip files that can't be opened
                continue
    
    return results


def extract_text_from_pdf(pdf_path: str, max_pages: Optional[int] = None) -> str:
    """
    Extract text content from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file (relative to materials base or absolute)
        max_pages: Maximum number of pages to extract (None = all pages)
        
    Returns:
        Extracted text content
    """
    # Handle both relative and absolute paths
    if os.path.isabs(pdf_path):
        full_path = Path(pdf_path)
    else:
        full_path = MATERIALS_BASE / pdf_path
    
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


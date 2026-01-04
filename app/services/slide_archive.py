"""Slide Archive Service for handling ZIP-based slide archives.

These files appear to be PDFs but are actually ZIP archives containing:
- JPEG images of each slide/page
- Text files with extracted text from each slide
- A manifest.json describing the structure

This service provides:
- Detection of slide archives vs real PDFs
- Extraction of slide content (images, text, metadata)
- Caching of extracted content for performance
"""

import json
import logging
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Base path for materials
MATERIALS_ROOT = Path("Materials")

# Cache for extracted archives (in-memory for now)
_archive_cache: Dict[str, "SlideArchiveData"] = {}


class SlideInfo(BaseModel):
    """Information about a single slide."""
    page_number: int
    image_path: str
    text_path: str
    width: int
    height: int
    has_visual_content: bool
    text_content: Optional[str] = None


class SlideArchiveData(BaseModel):
    """Extracted data from a slide archive."""
    file_path: str
    num_pages: int
    slides: List[SlideInfo]
    is_valid: bool = True


def is_slide_archive(file_path: Path) -> bool:
    """Check if a file is a slide archive (ZIP with manifest.json)."""
    if not file_path.exists():
        return False
    
    try:
        with zipfile.ZipFile(file_path, 'r') as zf:
            return 'manifest.json' in zf.namelist()
    except (zipfile.BadZipFile, Exception):
        return False


def get_file_type(file_path: Path) -> str:
    """Determine the actual file type of a .pdf file.
    
    Returns: 'pdf', 'slide_archive', or 'unknown'
    """
    if not file_path.exists():
        return 'unknown'
    
    # Check if it's a real PDF by reading magic bytes
    try:
        with open(file_path, 'rb') as f:
            header = f.read(8)
            if header.startswith(b'%PDF'):
                return 'pdf'
    except Exception:
        pass
    
    # Check if it's a slide archive
    if is_slide_archive(file_path):
        return 'slide_archive'
    
    return 'unknown'


def extract_slide_archive(file_path: Path, use_cache: bool = True) -> Optional[SlideArchiveData]:
    """Extract content from a slide archive.
    
    Args:
        file_path: Path to the slide archive file
        use_cache: Whether to use cached data if available
        
    Returns:
        SlideArchiveData with all slide information, or None if invalid
    """
    cache_key = str(file_path)
    
    if use_cache and cache_key in _archive_cache:
        return _archive_cache[cache_key]
    
    if not is_slide_archive(file_path):
        return None
    
    try:
        with zipfile.ZipFile(file_path, 'r') as zf:
            # Read manifest
            manifest_data = json.loads(zf.read('manifest.json'))
            
            slides = []
            for page in manifest_data.get('pages', []):
                # Read text content
                text_content = None
                text_path = page.get('text', {}).get('path', '')
                if text_path and text_path in zf.namelist():
                    try:
                        text_content = zf.read(text_path).decode('utf-8')
                    except Exception:
                        pass
                
                slide = SlideInfo(
                    page_number=page.get('page_number', 0),
                    image_path=page.get('image', {}).get('path', ''),
                    text_path=text_path,
                    width=page.get('image', {}).get('dimensions', {}).get('width', 0),
                    height=page.get('image', {}).get('dimensions', {}).get('height', 0),
                    has_visual_content=page.get('has_visual_content', True),
                    text_content=text_content
                )
                slides.append(slide)
            
            archive_data = SlideArchiveData(
                file_path=str(file_path),
                num_pages=manifest_data.get('num_pages', len(slides)),
                slides=slides
            )
            
            # Cache the result
            _archive_cache[cache_key] = archive_data
            return archive_data
            
    except Exception as e:
        logger.error("Failed to extract slide archive %s: %s", file_path, e)
        return None


def get_slide_image(file_path: Path, page_number: int) -> Optional[Tuple[bytes, str]]:
    """Get a slide image from an archive.

    Args:
        file_path: Path to the slide archive
        page_number: 1-based page number

    Returns:
        Tuple of (image_bytes, media_type) or None if not found
    """
    try:
        with zipfile.ZipFile(file_path, 'r') as zf:
            # Read manifest to find the image path
            manifest_data = json.loads(zf.read('manifest.json'))

            for page in manifest_data.get('pages', []):
                if page.get('page_number') == page_number:
                    image_path = page.get('image', {}).get('path', '')
                    media_type = page.get('image', {}).get('media_type', 'image/jpeg')

                    if image_path and image_path in zf.namelist():
                        return zf.read(image_path), media_type

            return None
    except Exception as e:
        logger.error("Failed to get slide image from %s page %d: %s", file_path, page_number, e)
        return None


def get_all_text(file_path: Path) -> str:
    """Get all text content from a slide archive, concatenated.

    This is useful for indexing and search.

    Args:
        file_path: Path to the slide archive

    Returns:
        All text content joined with newlines
    """
    archive_data = extract_slide_archive(file_path)
    if not archive_data:
        return ""

    texts = []
    for slide in archive_data.slides:
        if slide.text_content:
            texts.append(f"--- Page {slide.page_number} ---")
            texts.append(slide.text_content)

    return "\n".join(texts)


def get_slide_text(file_path: Path, page_number: int) -> Optional[str]:
    """Get text content for a specific slide.

    Args:
        file_path: Path to the slide archive
        page_number: 1-based page number

    Returns:
        Text content or None if not found
    """
    archive_data = extract_slide_archive(file_path)
    if not archive_data:
        return None

    for slide in archive_data.slides:
        if slide.page_number == page_number:
            return slide.text_content

    return None


def clear_cache(file_path: Optional[Path] = None):
    """Clear the archive cache.

    Args:
        file_path: Specific file to clear, or None to clear all
    """
    global _archive_cache
    if file_path:
        cache_key = str(file_path)
        if cache_key in _archive_cache:
            del _archive_cache[cache_key]
    else:
        _archive_cache = {}


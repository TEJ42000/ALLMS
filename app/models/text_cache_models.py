"""Pydantic models for Text Cache System.

These models represent cached extracted text stored in Firestore.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class TextCacheEntry(BaseModel):
    """Cached extracted text entry stored in Firestore."""
    
    # File identification
    file_path: str = Field(..., description="Path relative to Materials/")
    file_hash: str = Field(..., description="MD5 hash of file content for change detection")
    file_size: int = Field(..., description="File size in bytes")
    file_modified: datetime = Field(..., description="File modification timestamp")
    
    # Extraction results
    file_type: str = Field(..., description="Detected file type (pdf, docx, image, etc.)")
    text: str = Field(..., description="Extracted text content")
    text_length: int = Field(..., description="Character count of extracted text")
    page_count: Optional[int] = Field(None, description="Number of pages (if applicable)")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    extraction_success: bool = Field(..., description="Whether extraction was successful")
    extraction_error: Optional[str] = Field(None, description="Error message if failed")
    
    # Timestamps
    cached_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = Field(default=0, description="Number of cache hits")
    
    # Organization
    subject: Optional[str] = Field(None, description="Subject/course (derived from path)")
    tier: Optional[str] = Field(None, description="Material tier (Syllabus, Course_Materials)")
    
    @field_validator('file_path')
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        """Ensure file path doesn't contain path traversal."""
        if '..' in v or v.startswith('/'):
            raise ValueError("Invalid file path")
        return v


class CacheStats(BaseModel):
    """Statistics about the text cache."""
    
    total_entries: int = Field(..., description="Total cached entries")
    total_characters: int = Field(..., description="Total characters of cached text")
    total_size_bytes: int = Field(..., description="Total original file size")
    
    # By status
    successful_extractions: int = Field(default=0)
    failed_extractions: int = Field(default=0)
    
    # By file type
    by_file_type: Dict[str, int] = Field(default_factory=dict)
    
    # By subject
    by_subject: Dict[str, int] = Field(default_factory=dict)
    
    # Cache health
    stale_entries: int = Field(default=0, description="Entries where file has changed")
    oldest_entry: Optional[datetime] = Field(None)
    newest_entry: Optional[datetime] = Field(None)
    
    # Performance
    cache_hit_rate: Optional[float] = Field(None, description="Percentage of cache hits")
    total_access_count: int = Field(default=0)


class CachePopulateRequest(BaseModel):
    """Request to populate cache for a folder."""
    
    folder_path: str = Field(..., description="Folder path relative to Materials/")
    recursive: bool = Field(default=True, description="Include subdirectories")
    force_refresh: bool = Field(default=False, description="Re-extract even if cached")
    
    @field_validator('folder_path')
    @classmethod
    def validate_folder_path(cls, v: str) -> str:
        """Ensure folder path is safe."""
        if '..' in v:
            raise ValueError("Invalid folder path")
        return v.strip('/')


class CachePopulateResponse(BaseModel):
    """Response from cache population."""
    
    total_files: int = Field(..., description="Total files found")
    cached: int = Field(..., description="Files successfully cached")
    skipped: int = Field(..., description="Files skipped (already cached)")
    failed: int = Field(..., description="Files that failed extraction")
    errors: List[Dict[str, str]] = Field(default_factory=list)


class CacheInvalidateRequest(BaseModel):
    """Request to invalidate cache entries."""
    
    file_path: Optional[str] = Field(None, description="Specific file to invalidate")
    folder_path: Optional[str] = Field(None, description="Folder to invalidate")
    all_stale: bool = Field(default=False, description="Invalidate all stale entries")


class CacheInvalidateResponse(BaseModel):
    """Response from cache invalidation."""
    
    invalidated: int = Field(..., description="Number of entries invalidated")
    message: str


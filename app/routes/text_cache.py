"""API Routes for Text Cache Management.

Provides endpoints for managing the Firestore text cache:
- Cache statistics
- Bulk population
- Cache invalidation
- Single file cache operations
"""

import logging
import pathlib

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.models.text_cache_models import (
    CacheStats,
    CachePopulateRequest,
    CachePopulateResponse,
    CacheInvalidateRequest,
    CacheInvalidateResponse,
)
from app.services.text_cache_service import (
    get_text_cache_service,
    extract_text_cached,
    populate_cache_for_folder,
)
from app.services.gcp_service import is_firestore_available

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/cache", tags=["Text Cache"])

# Base directory for materials
MATERIALS_BASE = pathlib.Path("Materials").resolve()


def validate_cache_path(file_path: str) -> pathlib.Path:
    """Validate a file path for cache operations."""
    if "\x00" in file_path or ".." in file_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path")

    full_path = (MATERIALS_BASE / file_path).resolve()
    try:
        full_path.relative_to(MATERIALS_BASE)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Path outside Materials")

    return full_path


# ============================================================================
# Cache Statistics
# ============================================================================


@router.get("/stats", response_model=CacheStats)
async def get_cache_stats():
    """Get statistics about the text cache."""
    if not is_firestore_available():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Firestore not available")

    cache = get_text_cache_service()
    stats = cache.get_stats()
    stats.stale_entries = cache.count_stale_entries()
    return stats


@router.get("/health")
async def cache_health():
    """Check cache health status."""
    available = is_firestore_available()
    cache = get_text_cache_service() if available else None

    return {
        "firestore_available": available,
        "cache_available": cache.is_available if cache else False,
        "status": "healthy" if available else "degraded",
    }


# ============================================================================
# Cache Population
# ============================================================================


class PopulateAllRequest(BaseModel):
    """Request to populate cache for all materials."""
    force_refresh: bool = False


@router.post("/populate", response_model=CachePopulateResponse)
async def populate_cache(request: CachePopulateRequest):
    """Populate cache for a specific folder."""
    if not is_firestore_available():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Firestore not available")

    full_path = validate_cache_path(request.folder_path)
    try:
        relative_folder = str(full_path.relative_to(MATERIALS_BASE))
    except ValueError:
        # This should not happen because validate_cache_path already enforces containment,
        # but we guard defensively and treat it as the base folder.
        relative_folder = ""
    if not relative_folder:
        # Use empty string to represent the base Materials folder, matching existing semantics.
        relative_folder = ""

    result = populate_cache_for_folder(
        folder_path=relative_folder, recursive=request.recursive,
        force_refresh=request.force_refresh,
    )

    return result


@router.post("/populate/all", response_model=CachePopulateResponse)
async def populate_all_cache(request: PopulateAllRequest):
    """Populate cache for all materials in the Materials folder."""
    if not is_firestore_available():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Firestore not available")

    result = populate_cache_for_folder(
        folder_path="", recursive=True, force_refresh=request.force_refresh,
    )

    return result


# ============================================================================
# Cache Invalidation
# ============================================================================


@router.post("/invalidate", response_model=CacheInvalidateResponse)
async def invalidate_cache(request: CacheInvalidateRequest):
    """Invalidate cache entries."""
    if not is_firestore_available():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Firestore not available")

    cache = get_text_cache_service()

    if request.all_stale:
        removed = cache.invalidate_stale()
        return CacheInvalidateResponse(invalidated=removed, message=f"Removed {removed} stale entries")

    if request.file_path:
        validate_cache_path(request.file_path)
        success = cache.invalidate(request.file_path)
        return CacheInvalidateResponse(invalidated=1 if success else 0, message="Invalidated" if success else "Not found")

    if request.folder_path:
        validate_cache_path(request.folder_path)
        count = cache.invalidate_folder(request.folder_path)
        return CacheInvalidateResponse(invalidated=count, message=f"Invalidated {count} entries")

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Must specify file, folder, or all_stale")


@router.delete("/clear")
async def clear_all_cache():
    """Clear entire cache. Use with caution!"""
    if not is_firestore_available():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Firestore not available")

    cache = get_text_cache_service()
    count = cache.invalidate_folder("")

    return {"cleared": count, "message": f"Cleared {count} cache entries"}


# ============================================================================
# Single File Operations
# ============================================================================


@router.get("/file/{file_path:path}")
async def get_cached_file(file_path: str):
    """Get cached text for a single file. Returns cached or extracts fresh."""
    if not is_firestore_available():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Firestore not available")

    full_path = validate_cache_path(file_path)

    if not full_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File not found: {file_path}")

    cache = get_text_cache_service()
    cached_entry = cache.get_cached(file_path)

    if cached_entry and cache.is_cache_valid(file_path, cached_entry):
        return {
            "file_path": file_path, "cached": True, "file_type": cached_entry.file_type,
            "text": cached_entry.text, "text_length": cached_entry.text_length, "from_cache": True,
            "cached_at": cached_entry.cached_at.isoformat(), "access_count": cached_entry.access_count,
        }

    result = extract_text_cached(full_path, use_cache=True)

    return {
        "file_path": file_path, "cached": result.success, "file_type": result.file_type,
        "text": result.text, "text_length": len(result.text), "from_cache": False,
        "extraction_error": result.error,
    }


@router.post("/file/{file_path:path}/refresh")
async def refresh_file_cache(file_path: str):
    """Force refresh cache for a single file."""
    if not is_firestore_available():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Firestore not available")

    full_path = validate_cache_path(file_path)

    if not full_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File not found: {file_path}")

    cache = get_text_cache_service()
    cache.invalidate(file_path)

    result = extract_text_cached(full_path, use_cache=True)

    return {
        "file_path": file_path, "refreshed": result.success, "file_type": result.file_type,
        "text_length": len(result.text), "error": result.error,
    }

"""Text Cache Service for Firestore.

Caches extracted text from course materials in Firestore for faster access.
Provides cache management, invalidation, and bulk population.
"""

import hashlib
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from google.cloud.firestore_v1 import FieldFilter

from app.models.text_cache_models import (
    TextCacheEntry,
    CacheStats,
    CachePopulateResponse,
)
from app.services.gcp_service import get_firestore_client, is_firestore_available
from app.services.text_extractor import (
    extract_text,
    ExtractionResult,
    MATERIALS_ROOT,
)

logger = logging.getLogger(__name__)

# Firestore collection name
TEXT_CACHE_COLLECTION = "material_text_cache"

# Maximum text length to store (to avoid Firestore document size limits)
# Firestore max doc size is 1MB, we use 900KB to be safe
MAX_TEXT_LENGTH = 900_000


def _compute_file_hash(file_path: Path) -> str:
    """Compute MD5 hash of file content for change detection."""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.warning("Failed to compute hash for %s: %s", file_path, e)
        return ""


def _path_to_doc_id(file_path: str) -> str:
    """Convert file path to a valid Firestore document ID.

    Firestore document IDs cannot contain forward slashes.
    """
    return hashlib.sha256(file_path.encode()).hexdigest()[:64]


def _extract_subject_and_tier(file_path: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract subject and tier from file path.

    Examples:
        "Syllabus/LLS/syllabus.pdf" -> ("LLS", "Syllabus")
        "Course_Materials/Criminal_Law/Lectures/lecture.pdf" -> ("Criminal_Law", "Course_Materials")
    """
    parts = Path(file_path).parts
    tier = parts[0] if len(parts) > 0 else None
    subject = parts[1] if len(parts) > 1 else None
    return subject, tier


class TextCacheService:
    """Service for caching extracted text in Firestore."""

    def __init__(self):
        """Initialize the text cache service."""
        self.db = get_firestore_client()
        self._collection = None
        if self.db is not None:
            self._collection = self.db.collection(TEXT_CACHE_COLLECTION)
        else:
            logger.warning("Firestore not available - cache will be disabled")

    @property
    def is_available(self) -> bool:
        """Check if cache is available."""
        return self.db is not None

    def get_cached(self, file_path: str) -> Optional[TextCacheEntry]:
        """Get cached text for a file.

        Args:
            file_path: Path relative to Materials/

        Returns:
            Cached entry if exists and valid, None otherwise
        """
        if not self.is_available:
            return None

        doc_id = _path_to_doc_id(file_path)
        doc_ref = self._collection.document(doc_id)

        try:
            doc = doc_ref.get()
            if not doc.exists:
                return None

            data = doc.to_dict()
            entry = TextCacheEntry(**data)

            # Update access stats
            doc_ref.update({
                "last_accessed": datetime.now(timezone.utc),
                "access_count": entry.access_count + 1,
            })

            return entry
        except Exception as e:
            logger.error("Error getting cached text for %s: %s", file_path, e)
            return None

    def is_cache_valid(self, file_path: str, entry: TextCacheEntry) -> bool:
        """Check if cached entry is still valid (file hasn't changed).

        Args:
            file_path: Path relative to Materials/
            entry: Cached entry to validate

        Returns:
            True if cache is valid, False if file has changed
        """
        full_path = MATERIALS_ROOT / file_path

        if not full_path.exists():
            return False

        # Check file hash
        current_hash = _compute_file_hash(full_path)
        return current_hash == entry.file_hash

    def cache_extraction(
        self,
        file_path: str,
        result: ExtractionResult,
        file_hash: str,
        file_size: int,
        file_modified: datetime,
    ) -> bool:
        """Cache an extraction result."""
        if not self.is_available:
            return False

        # Truncate text if too long
        text = result.text
        if len(text) > MAX_TEXT_LENGTH:
            text = text[:MAX_TEXT_LENGTH] + "\n\n[Text truncated for storage...]"

        subject, tier = _extract_subject_and_tier(file_path)

        entry = TextCacheEntry(
            file_path=file_path, file_hash=file_hash, file_size=file_size,
            file_modified=file_modified, file_type=result.file_type, text=text,
            text_length=len(result.text), page_count=result.metadata.get("num_pages"),
            metadata=result.metadata, extraction_success=result.success,
            extraction_error=result.error, subject=subject, tier=tier,
        )

        doc_id = _path_to_doc_id(file_path)
        try:
            self._collection.document(doc_id).set(entry.model_dump())
            return True
        except Exception as e:
            logger.error("Failed to cache extraction for %s: %s", file_path, e)
            return False

    def invalidate(self, file_path: str) -> bool:
        """Invalidate (delete) a cached entry."""
        if not self.is_available:
            return False
        doc_id = _path_to_doc_id(file_path)
        try:
            self._collection.document(doc_id).delete()
            return True
        except Exception as e:
            logger.error("Failed to invalidate cache for %s: %s", file_path, e)
            return False

    def invalidate_folder(self, folder_path: str) -> int:
        """Invalidate all cached entries in a folder."""
        if not self.is_available:
            return 0
        count = 0
        try:
            docs = self._collection.stream()
            for doc in docs:
                data = doc.to_dict()
                if data.get("file_path", "").startswith(folder_path):
                    doc.reference.delete()
                    count += 1
        except Exception as e:
            logger.error("Error invalidating folder cache %s: %s", folder_path, e)
        return count

    def get_stats(self) -> CacheStats:
        """Get statistics about the cache."""
        if not self.is_available:
            return CacheStats(total_entries=0, total_characters=0, total_size_bytes=0)

        stats = CacheStats(total_entries=0, total_characters=0, total_size_bytes=0)
        by_file_type: Dict[str, int] = {}
        by_subject: Dict[str, int] = {}
        oldest: Optional[datetime] = None
        newest: Optional[datetime] = None

        try:
            docs = self._collection.stream()
            for doc in docs:
                data = doc.to_dict()
                stats.total_entries += 1
                stats.total_characters += data.get("text_length", 0)
                stats.total_size_bytes += data.get("file_size", 0)
                stats.total_access_count += data.get("access_count", 0)

                if data.get("extraction_success"):
                    stats.successful_extractions += 1
                else:
                    stats.failed_extractions += 1

                file_type = data.get("file_type", "unknown")
                by_file_type[file_type] = by_file_type.get(file_type, 0) + 1
                subject = data.get("subject") or "unknown"
                by_subject[subject] = by_subject.get(subject, 0) + 1

                cached_at = data.get("cached_at")
                if cached_at:
                    if oldest is None or cached_at < oldest:
                        oldest = cached_at
                    if newest is None or cached_at > newest:
                        newest = cached_at

            stats.by_file_type = by_file_type
            stats.by_subject = by_subject
            stats.oldest_entry = oldest
            stats.newest_entry = newest

            if stats.total_access_count > 0 and stats.total_entries > 0:
                stats.cache_hit_rate = stats.total_access_count / stats.total_entries
        except Exception as e:
            logger.error("Error getting cache stats: %s", e)

        return stats

    def count_stale_entries(self) -> int:
        """Count entries where the source file has changed."""
        if not self.is_available:
            return 0
        stale_count = 0
        try:
            docs = self._collection.stream()
            for doc in docs:
                data = doc.to_dict()
                file_path = data.get("file_path", "")
                full_path = MATERIALS_ROOT / file_path
                if not full_path.exists():
                    stale_count += 1
                    continue
                cached_hash = data.get("file_hash", "")
                current_hash = _compute_file_hash(full_path)
                if cached_hash != current_hash:
                    stale_count += 1
        except Exception as e:
            logger.error("Error counting stale entries: %s", e)
        return stale_count

    def invalidate_stale(self) -> int:
        """Remove all stale cache entries."""
        if not self.is_available:
            return 0
        removed = 0
        try:
            docs = self._collection.stream()
            for doc in docs:
                data = doc.to_dict()
                file_path = data.get("file_path", "")
                full_path = MATERIALS_ROOT / file_path
                is_stale = not full_path.exists()
                if not is_stale:
                    cached_hash = data.get("file_hash", "")
                    current_hash = _compute_file_hash(full_path)
                    if cached_hash != current_hash:
                        is_stale = True
                if is_stale:
                    doc.reference.delete()
                    removed += 1
        except Exception as e:
            logger.error("Error invalidating stale entries: %s", e)
        return removed


def get_text_cache_service() -> TextCacheService:
    """Get a TextCacheService instance."""
    return TextCacheService()


def extract_text_cached(file_path: Path, use_cache: bool = True) -> ExtractionResult:
    """Extract text with caching support.

    This is the main entry point that wraps extract_text with caching.
    """
    # Normalize path to be relative to Materials
    if file_path.is_absolute():
        try:
            rel_path = str(file_path.relative_to(MATERIALS_ROOT.resolve()))
        except ValueError:
            return extract_text(file_path)
    else:
        path_str = str(file_path)
        if path_str.startswith("Materials/"):
            rel_path = path_str[len("Materials/"):]
            file_path = MATERIALS_ROOT / rel_path
        else:
            rel_path = path_str
            file_path = MATERIALS_ROOT / rel_path

    cache = get_text_cache_service()

    # Try to get from cache
    if use_cache and cache.is_available:
        cached = cache.get_cached(rel_path)
        if cached and cache.is_cache_valid(rel_path, cached):
            logger.debug("Cache hit for %s", rel_path)
            return ExtractionResult(
                file_path=cached.file_path, file_type=cached.file_type,
                text=cached.text, success=cached.extraction_success,
                error=cached.extraction_error, metadata=cached.metadata, pages=None,
            )

    # Extract fresh
    full_path = MATERIALS_ROOT / rel_path
    if not full_path.exists():
        return ExtractionResult(
            file_path=rel_path, file_type="unknown", text="", success=False,
            error=f"File not found: {rel_path}",
        )

    result = extract_text(full_path)

    # Cache the result
    if use_cache and cache.is_available and result.success:
        stat = full_path.stat()
        file_hash = _compute_file_hash(full_path)
        file_modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        cache.cache_extraction(
            file_path=rel_path, result=result, file_hash=file_hash,
            file_size=stat.st_size, file_modified=file_modified,
        )

    return result


def populate_cache_for_folder(
    folder_path: str, recursive: bool = True, force_refresh: bool = False,
) -> CachePopulateResponse:
    """Populate cache for all files in a folder."""
    from app.services.text_extractor import extract_all_from_folder

    full_path = MATERIALS_ROOT / folder_path
    if not full_path.exists() or not full_path.is_dir():
        return CachePopulateResponse(
            total_files=0, cached=0, skipped=0, failed=0,
            errors=[{"error": f"Folder not found: {folder_path}"}],
        )

    cache = get_text_cache_service()

    # Find all files
    files = list(full_path.rglob("*") if recursive else full_path.glob("*"))
    files = [f for f in files if f.is_file()]

    total_files = len(files)
    cached = 0
    skipped = 0
    failed = 0
    errors: List[Dict[str, str]] = []

    for file_path in files:
        try:
            rel_path = str(file_path.relative_to(MATERIALS_ROOT))

            # Check if already cached and valid
            if not force_refresh and cache.is_available:
                existing = cache.get_cached(rel_path)
                if existing and cache.is_cache_valid(rel_path, existing):
                    skipped += 1
                    continue

            result = extract_text_cached(file_path, use_cache=True)

            if result.success:
                cached += 1
            else:
                failed += 1
                errors.append({"file": rel_path, "error": result.error or "Unknown error"})
        except Exception as e:
            failed += 1
            errors.append({"file": str(file_path), "error": str(e)})

    logger.info(
        "Cache population complete for %s: %d cached, %d skipped, %d failed",
        folder_path, cached, skipped, failed
    )

    return CachePopulateResponse(
        total_files=total_files, cached=cached, skipped=skipped,
        failed=failed, errors=errors[:100],
    )

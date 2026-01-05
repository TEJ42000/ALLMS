"""Study Guide Persistence Service for storing and retrieving study guides.

This service manages:
1. Storing generated study guides in Firestore for reuse
2. Detecting duplicate study guides via content hashing
3. Retrieving study guide history

Firestore Collections:
- courses/{courseId}/studyGuides/{guideId} - Stored study guides
"""

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.services.gcp_service import get_firestore_client

logger = logging.getLogger(__name__)

# Length of content hash for duplicate detection
CONTENT_HASH_LENGTH = 16


class StudyGuidePersistenceService:
    """Service for persisting study guides to Firestore."""

    def __init__(self):
        """Initialize the study guide persistence service."""
        self._firestore = get_firestore_client()

    def _generate_content_hash(self, content: str) -> str:
        """Generate a hash from study guide content for duplicate detection.

        Args:
            content: Study guide markdown content

        Returns:
            SHA-256 hash string (truncated)
        """
        return hashlib.sha256(content.encode()).hexdigest()[:CONTENT_HASH_LENGTH]

    def _generate_title(
        self,
        course_id: str,
        week_numbers: Optional[List[int]],
        sequence_number: int,
        created_at: datetime
    ) -> str:
        """Generate a study guide title.

        Args:
            course_id: Course ID
            week_numbers: Week numbers covered (if any)
            sequence_number: Which number guide this is (1-based)
            created_at: Creation timestamp

        Returns:
            Formatted title like "Study Guide - Week 1-3 (Jan 05)"
        """
        date_str = created_at.strftime("%b %d")

        if week_numbers and len(week_numbers) > 0:
            if len(week_numbers) == 1:
                week_str = f"Week {week_numbers[0]}"
            else:
                week_str = f"Weeks {min(week_numbers)}-{max(week_numbers)}"
        else:
            week_str = "All Weeks"

        base_title = f"Study Guide - {week_str}"

        if sequence_number <= 1:
            return f"{base_title} ({date_str})"
        else:
            return f"{base_title} #{sequence_number} ({date_str})"

    async def _count_similar_guides(
        self,
        course_id: str,
        week_numbers: Optional[List[int]]
    ) -> int:
        """Count existing guides with similar week coverage.

        Args:
            course_id: Course ID
            week_numbers: Week numbers filter

        Returns:
            Number of existing guides with similar coverage
        """
        if not self._firestore:
            return 0

        guides_ref = self._firestore.collection("courses").document(course_id) \
            .collection("studyGuides")

        # For simplicity, just count all guides for the course
        docs = list(guides_ref.stream())
        return len(docs)

    async def save_study_guide(
        self,
        course_id: str,
        content: str,
        week_numbers: Optional[List[int]] = None,
        title: Optional[str] = None
    ) -> Dict:
        """Save a generated study guide to Firestore.

        Args:
            course_id: Course ID
            content: Markdown content of the study guide
            week_numbers: Week numbers covered
            title: Optional title (auto-generated if not provided)

        Returns:
            Dictionary with saved guide data including ID
        """
        if not self._firestore:
            raise RuntimeError("Firestore not available")

        guide_id = str(uuid.uuid4())
        content_hash = self._generate_content_hash(content)
        now = datetime.now(timezone.utc)

        # Generate title if not provided
        if not title:
            existing_count = await self._count_similar_guides(course_id, week_numbers)
            title = self._generate_title(course_id, week_numbers, existing_count + 1, now)

        # Calculate word count
        word_count = len(content.split())

        guide_data = {
            "id": guide_id,
            "courseId": course_id,
            "title": title,
            "content": content,
            "weekNumbers": week_numbers,
            "contentHash": content_hash,
            "createdAt": now,
            "wordCount": word_count
        }

        # Save to Firestore
        doc_ref = self._firestore.collection("courses").document(course_id) \
            .collection("studyGuides").document(guide_id)
        doc_ref.set(guide_data)

        logger.info("Saved study guide %s for course %s", guide_id, course_id)
        return guide_data

    async def find_duplicate_guide(
        self,
        course_id: str,
        content: str
    ) -> Optional[Dict]:
        """Check if a study guide with the same content already exists.

        Args:
            course_id: Course ID
            content: Study guide content

        Returns:
            Existing guide data if duplicate found, None otherwise
        """
        if not self._firestore:
            return None

        content_hash = self._generate_content_hash(content)

        guides_ref = self._firestore.collection("courses").document(course_id) \
            .collection("studyGuides")
        query = guides_ref.where("contentHash", "==", content_hash)

        for doc in query.stream():
            data = doc.to_dict()
            return self._firestore_to_dict(data)

        return None

    def _firestore_to_dict(self, data: Dict) -> Dict:
        """Convert Firestore document to dictionary with snake_case keys.

        Args:
            data: Raw Firestore document data

        Returns:
            Dictionary with converted keys and datetime
        """
        created_at = data.get("createdAt")
        if hasattr(created_at, 'isoformat'):
            created_at_str = created_at.isoformat()
        else:
            created_at_str = str(created_at) if created_at else None

        return {
            "id": data.get("id"),
            "course_id": data.get("courseId"),
            "title": data.get("title"),
            "content": data.get("content"),
            "week_numbers": data.get("weekNumbers"),
            "content_hash": data.get("contentHash"),
            "created_at": created_at_str,
            "word_count": data.get("wordCount", 0)
        }

    async def list_study_guides(
        self,
        course_id: str,
        limit: int = 20
    ) -> List[Dict]:
        """List study guides for a course.

        Args:
            course_id: Course ID
            limit: Maximum number of results

        Returns:
            List of study guide summaries (without full content)
        """
        if not self._firestore:
            return []

        guides_ref = self._firestore.collection("courses").document(course_id) \
            .collection("studyGuides")
        query = guides_ref.order_by("createdAt", direction="DESCENDING").limit(limit)

        guides = []
        for doc in query.stream():
            data = doc.to_dict()
            # Return summary without full content
            guides.append({
                "id": data.get("id"),
                "course_id": data.get("courseId"),
                "title": data.get("title"),
                "week_numbers": data.get("weekNumbers"),
                "created_at": data.get("createdAt").isoformat() if data.get("createdAt") else None,
                "word_count": data.get("wordCount", 0)
            })

        return guides

    async def get_study_guide(
        self,
        course_id: str,
        guide_id: str
    ) -> Optional[Dict]:
        """Get a specific study guide by ID.

        Args:
            course_id: Course ID
            guide_id: Study guide ID

        Returns:
            Study guide data or None if not found
        """
        if not self._firestore:
            return None

        doc_ref = self._firestore.collection("courses").document(course_id) \
            .collection("studyGuides").document(guide_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        return self._firestore_to_dict(doc.to_dict())

    async def delete_study_guide(
        self,
        course_id: str,
        guide_id: str
    ) -> bool:
        """Delete a study guide.

        Args:
            course_id: Course ID
            guide_id: Study guide ID

        Returns:
            True if deleted, False if not found
        """
        if not self._firestore:
            return False

        doc_ref = self._firestore.collection("courses").document(course_id) \
            .collection("studyGuides").document(guide_id)

        if not doc_ref.get().exists:
            return False

        doc_ref.delete()
        logger.info("Deleted study guide %s from course %s", guide_id, course_id)
        return True


# Singleton instance
_service_instance: Optional[StudyGuidePersistenceService] = None


def get_study_guide_persistence_service() -> StudyGuidePersistenceService:
    """Get or create the study guide persistence service singleton.

    Returns:
        StudyGuidePersistenceService instance
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = StudyGuidePersistenceService()
    return _service_instance


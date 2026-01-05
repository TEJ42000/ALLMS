"""Assessment Persistence Service for storing and retrieving essay assessments.

This service manages:
1. Storing generated essay questions in Firestore
2. Storing user essay attempts and evaluations
3. Retrieving assessment history for users
4. Supporting retakes of assessments

Firestore Collections:
- courses/{courseId}/assessments/{assessmentId} - Stored essay assessments
- assessmentAttempts/{attemptId} - User essay attempt results
"""

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from app.services.gcp_service import get_firestore_client

logger = logging.getLogger(__name__)

CONTENT_HASH_LENGTH = 16


class AssessmentPersistenceService:
    """Service for persisting essay assessments and attempts to Firestore."""

    def __init__(self):
        """Initialize the assessment persistence service."""
        self._firestore = get_firestore_client()

    def _generate_content_hash(self, question: str, topic: str) -> str:
        """Generate a hash from question and topic for duplicate detection."""
        content = f"{topic}|{question}"
        return hashlib.sha256(content.encode()).hexdigest()[:CONTENT_HASH_LENGTH]

    def _generate_assessment_title(
        self,
        topic: str,
        sequence_number: int,
        created_at: datetime
    ) -> str:
        """Generate a unique assessment title."""
        date_str = created_at.strftime("%b %d")
        base_title = f"{topic} Essay"
        if sequence_number <= 1:
            return f"{base_title} ({date_str})"
        return f"{base_title} #{sequence_number} ({date_str})"

    async def _count_similar_assessments(
        self,
        course_id: str,
        topic: str
    ) -> int:
        """Count existing assessments with the same topic."""
        if not self._firestore:
            return 0
        assessments_ref = self._firestore.collection("courses").document(course_id) \
            .collection("assessments")
        query = assessments_ref.where("topic", "==", topic)
        docs = list(query.stream())
        return len(docs)

    async def save_assessment(
        self,
        course_id: str,
        user_id: str,
        question: str,
        topic: str,
        week_number: Optional[int] = None,
        expected_paragraphs: str = "3-7",
        key_concepts: Optional[List[str]] = None,
        title: Optional[str] = None
    ) -> Dict:
        """Save a generated essay assessment to Firestore."""
        if not self._firestore:
            raise RuntimeError("Firestore not available")

        assessment_id = str(uuid.uuid4())
        content_hash = self._generate_content_hash(question, topic)
        now = datetime.now(timezone.utc)

        if not title:
            existing_count = await self._count_similar_assessments(course_id, topic)
            title = self._generate_assessment_title(topic, existing_count + 1, now)

        assessment_data = {
            "id": assessment_id,
            "courseId": course_id,
            "userId": user_id,
            "question": question,
            "topic": topic,
            "weekNumber": week_number,
            "expectedParagraphs": expected_paragraphs,
            "keyConcepts": key_concepts or [],
            "contentHash": content_hash,
            "createdAt": now,
            "title": title
        }

        doc_ref = self._firestore.collection("courses").document(course_id) \
            .collection("assessments").document(assessment_id)
        doc_ref.set(assessment_data)

        logger.info("Saved assessment %s for course %s", assessment_id, course_id)
        return assessment_data

    async def get_assessment(self, course_id: str, assessment_id: str) -> Optional[Dict]:
        """Get a specific assessment by ID."""
        if not self._firestore:
            return None
        doc_ref = self._firestore.collection("courses").document(course_id) \
            .collection("assessments").document(assessment_id)
        doc = doc_ref.get()
        if not doc.exists:
            return None
        return doc.to_dict()

    async def list_assessments(
        self,
        course_id: str,
        user_id: Optional[str] = None,
        topic: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """List available assessments for a course."""
        if not self._firestore:
            return []

        assessments_ref = self._firestore.collection("courses").document(course_id) \
            .collection("assessments")
        query = assessments_ref.order_by("createdAt", direction="DESCENDING")
        docs = query.limit(limit).stream()

        assessments = []
        for doc in docs:
            data = doc.to_dict()
            if user_id and data.get("userId") != user_id:
                continue
            if topic and data.get("topic") != topic:
                continue
            # Get attempt stats
            attempts = await self.get_assessment_attempts(course_id, data.get("id"))
            grades = [a.get("grade") for a in attempts if a.get("grade")]
            assessments.append({
                "id": data.get("id"),
                "courseId": data.get("courseId"),
                "topic": data.get("topic"),
                "question": data.get("question", "")[:200] + "..." if len(data.get("question", "")) > 200 else data.get("question", ""),
                "title": data.get("title"),
                "createdAt": data.get("createdAt"),
                "attemptCount": len(attempts),
                "bestGrade": max(grades) if grades else None,
                "latestGrade": grades[0] if grades else None
            })
        return assessments

    async def save_attempt(
        self,
        assessment_id: str,
        course_id: str,
        user_id: str,
        answer: str,
        grade: int,
        feedback: str,
        strengths: List[str],
        improvements: List[str]
    ) -> Dict:
        """Save a user's essay attempt result."""
        if not self._firestore:
            raise RuntimeError("Firestore not available")

        attempt_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        attempt_data = {
            "id": attempt_id,
            "assessmentId": assessment_id,
            "courseId": course_id,
            "userId": user_id,
            "answer": answer,
            "grade": grade,
            "feedback": feedback,
            "strengths": strengths,
            "improvements": improvements,
            "submittedAt": now
        }

        doc_ref = self._firestore.collection("assessmentAttempts").document(attempt_id)
        doc_ref.set(attempt_data)

        logger.info(
            "Saved attempt %s: user=%s, grade=%d/10",
            attempt_id, user_id, grade
        )
        return attempt_data

    async def get_assessment_attempts(
        self,
        course_id: str,
        assessment_id: str,
        user_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Get all attempts for a specific assessment."""
        if not self._firestore:
            return []

        attempts_ref = self._firestore.collection("assessmentAttempts")
        query = attempts_ref.where("assessmentId", "==", assessment_id)

        if user_id:
            query = query.where("userId", "==", user_id)

        query = query.order_by("submittedAt", direction="DESCENDING").limit(limit)
        docs = query.stream()

        attempts = []
        for doc in docs:
            attempts.append(doc.to_dict())
        return attempts

    async def get_user_assessment_history(
        self,
        user_id: str,
        course_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Get a user's essay assessment history."""
        if not self._firestore:
            return []

        attempts_ref = self._firestore.collection("assessmentAttempts")
        query = attempts_ref.where("userId", "==", user_id)

        if course_id:
            query = query.where("courseId", "==", course_id)

        query = query.order_by("submittedAt", direction="DESCENDING").limit(limit)
        docs = query.stream()

        history = []
        for doc in docs:
            data = doc.to_dict()
            # Fetch assessment metadata
            assessment = await self.get_assessment(
                data.get("courseId"),
                data.get("assessmentId")
            )
            history.append({
                "attemptId": data.get("id"),
                "assessmentId": data.get("assessmentId"),
                "courseId": data.get("courseId"),
                "topic": assessment.get("topic") if assessment else "Unknown",
                "question": assessment.get("question") if assessment else "Unknown",
                "grade": data.get("grade"),
                "submittedAt": data.get("submittedAt")
            })
        return history

    async def get_attempt(self, attempt_id: str) -> Optional[Dict]:
        """Get a specific attempt by ID."""
        if not self._firestore:
            return None
        doc_ref = self._firestore.collection("assessmentAttempts").document(attempt_id)
        doc = doc_ref.get()
        if not doc.exists:
            return None
        return doc.to_dict()


# Singleton instance
_assessment_persistence_service = None


def get_assessment_persistence_service() -> AssessmentPersistenceService:
    """Get the singleton assessment persistence service instance."""
    global _assessment_persistence_service
    if _assessment_persistence_service is None:
        _assessment_persistence_service = AssessmentPersistenceService()
    return _assessment_persistence_service


"""Quiz Persistence Service for storing and retrieving quizzes and results.

This service manages:
1. Storing generated quizzes in Firestore for reuse
2. Detecting duplicate quizzes via content hashing
3. Storing user quiz attempt results
4. Retrieving quiz history for users

Firestore Collections:
- courses/{courseId}/quizzes/{quizId} - Stored quizzes
- quizResults/{resultId} - User quiz attempt results
"""

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from app.services.gcp_service import get_firestore_client

logger = logging.getLogger(__name__)

# Length of content hash for duplicate detection
# 16 hex characters (64 bits) provides sufficient uniqueness for typical course sizes
CONTENT_HASH_LENGTH = 16


class QuizPersistenceService:
    """Service for persisting quizzes and results to Firestore."""

    def __init__(self):
        """Initialize the quiz persistence service."""
        self._firestore = get_firestore_client()

    def _generate_content_hash(self, questions: List[Dict]) -> str:
        """Generate a hash from quiz questions for duplicate detection.

        The hash is based on sorted question texts to detect duplicates
        regardless of question order.

        Args:
            questions: List of question dictionaries

        Returns:
            SHA-256 hash string
        """
        # Extract and sort question texts
        question_texts = sorted([q.get("question", "") for q in questions])
        content = "|".join(question_texts)
        return hashlib.sha256(content.encode()).hexdigest()[:CONTENT_HASH_LENGTH]

    async def save_quiz(
        self,
        course_id: str,
        topic: str,
        difficulty: str,
        questions: List[Dict],
        week_number: Optional[int] = None,
        title: Optional[str] = None
    ) -> Dict:
        """Save a generated quiz to Firestore.

        Args:
            course_id: Course ID
            topic: Quiz topic
            difficulty: Difficulty level
            questions: List of question dictionaries
            week_number: Optional week filter used
            title: Optional quiz title

        Returns:
            Dictionary with saved quiz data including ID
        """
        if not self._firestore:
            raise RuntimeError("Firestore not available")

        # Validate questions have valid correct_index values
        for i, question in enumerate(questions):
            options = question.get("options", [])
            correct_index = question.get("correct_index", 0)
            if correct_index < 0 or correct_index >= len(options):
                raise ValueError(
                    f"Question {i + 1} has invalid correct_index {correct_index} "
                    f"for {len(options)} options"
                )

        quiz_id = str(uuid.uuid4())
        content_hash = self._generate_content_hash(questions)
        now = datetime.now(timezone.utc)

        quiz_data = {
            "id": quiz_id,
            "courseId": course_id,
            "topic": topic,
            "difficulty": difficulty,
            "weekNumber": week_number,
            "numQuestions": len(questions),
            "questions": questions,
            "contentHash": content_hash,
            "createdAt": now,
            "title": title or f"{topic} Quiz - {difficulty.capitalize()}"
        }

        # Save to Firestore
        doc_ref = self._firestore.collection("courses").document(course_id) \
            .collection("quizzes").document(quiz_id)
        doc_ref.set(quiz_data)

        logger.info("Saved quiz %s for course %s", quiz_id, course_id)
        return quiz_data

    async def find_duplicate_quiz(
        self,
        course_id: str,
        topic: str,
        difficulty: str,
        questions: List[Dict],
        week_number: Optional[int] = None
    ) -> Optional[Dict]:
        """Check if a quiz with the same content already exists.

        Args:
            course_id: Course ID
            topic: Quiz topic
            difficulty: Difficulty level
            questions: List of question dictionaries
            week_number: Optional week filter

        Returns:
            Existing quiz data if duplicate found, None otherwise
        """
        if not self._firestore:
            return None

        content_hash = self._generate_content_hash(questions)

        # Query for quizzes with same hash
        quizzes_ref = self._firestore.collection("courses").document(course_id) \
            .collection("quizzes")

        query = quizzes_ref.where("contentHash", "==", content_hash)
        if week_number is not None:
            query = query.where("weekNumber", "==", week_number)

        docs = query.limit(1).stream()
        for doc in docs:
            logger.info("Found duplicate quiz %s", doc.id)
            return doc.to_dict()

        return None

    async def list_quizzes(
        self,
        course_id: str,
        topic: Optional[str] = None,
        difficulty: Optional[str] = None,
        week_number: Optional[int] = None,
        limit: int = 20
    ) -> List[Dict]:
        """List available quizzes for a course.

        Args:
            course_id: Course ID
            topic: Optional topic filter
            difficulty: Optional difficulty filter
            week_number: Optional week filter
            limit: Maximum number of quizzes to return

        Returns:
            List of quiz summary dictionaries
        """
        if not self._firestore:
            return []

        quizzes_ref = self._firestore.collection("courses").document(course_id) \
            .collection("quizzes")

        query = quizzes_ref.order_by("createdAt", direction="DESCENDING")
        docs = query.limit(limit).stream()

        quizzes = []
        for doc in docs:
            data = doc.to_dict()
            # Apply filters (Firestore doesn't support multiple inequality filters)
            if topic and data.get("topic") != topic:
                continue
            if difficulty and data.get("difficulty") != difficulty:
                continue
            if week_number is not None and data.get("weekNumber") != week_number:
                continue

            # Return summary (exclude full questions for list)
            quizzes.append({
                "id": data.get("id"),
                "courseId": data.get("courseId"),
                "topic": data.get("topic"),
                "difficulty": data.get("difficulty"),
                "weekNumber": data.get("weekNumber"),
                "numQuestions": data.get("numQuestions"),
                "createdAt": data.get("createdAt"),
                "title": data.get("title")
            })

        return quizzes

    async def get_quiz(self, course_id: str, quiz_id: str) -> Optional[Dict]:
        """Get a specific quiz by ID.

        Args:
            course_id: Course ID
            quiz_id: Quiz ID

        Returns:
            Quiz data dictionary or None if not found
        """
        if not self._firestore:
            return None

        doc_ref = self._firestore.collection("courses").document(course_id) \
            .collection("quizzes").document(quiz_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        return doc.to_dict()

    async def save_quiz_result(
        self,
        quiz_id: str,
        course_id: str,
        user_id: str,
        answers: List[int],
        score: int,
        total_questions: int,
        time_taken_seconds: Optional[int] = None
    ) -> Dict:
        """Save a user's quiz attempt result.

        Args:
            quiz_id: Quiz ID
            course_id: Course ID
            user_id: User ID (simulated)
            answers: List of user's answer indices
            score: Number of correct answers
            total_questions: Total number of questions
            time_taken_seconds: Optional time taken

        Returns:
            Dictionary with saved result data
        """
        if not self._firestore:
            raise RuntimeError("Firestore not available")

        result_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        percentage = (score / total_questions * 100) if total_questions > 0 else 0

        result_data = {
            "id": result_id,
            "quizId": quiz_id,
            "courseId": course_id,
            "userId": user_id,
            "answers": answers,
            "score": score,
            "totalQuestions": total_questions,
            "percentage": round(percentage, 1),
            "timeTakenSeconds": time_taken_seconds,
            "completedAt": now
        }

        # Save to quizResults collection
        doc_ref = self._firestore.collection("quizResults").document(result_id)
        doc_ref.set(result_data)

        logger.info(
            "Saved quiz result %s: user=%s, score=%d/%d (%.1f%%)",
            result_id, user_id, score, total_questions, percentage
        )
        return result_data

    async def get_user_quiz_history(
        self,
        user_id: str,
        course_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Get a user's quiz history.

        Args:
            user_id: User ID
            course_id: Optional course filter
            limit: Maximum results to return

        Returns:
            List of quiz result dictionaries with quiz metadata, sorted by
            completedAt descending (most recent first)

        Note:
            Requires Firestore composite index on quizResults:
            (userId ASC, completedAt DESC)
        """
        if not self._firestore:
            return []

        results_ref = self._firestore.collection("quizResults")
        query = results_ref.where("userId", "==", user_id)

        if course_id:
            query = query.where("courseId", "==", course_id)

        query = query.order_by("completedAt", direction="DESCENDING").limit(limit)
        docs = query.stream()

        history = []
        for doc in docs:
            data = doc.to_dict()
            # Fetch quiz metadata
            quiz = await self.get_quiz(data.get("courseId"), data.get("quizId"))
            history.append({
                "resultId": data.get("id"),
                "quizId": data.get("quizId"),
                "courseId": data.get("courseId"),
                "topic": quiz.get("topic") if quiz else "Unknown",
                "quizTitle": quiz.get("title") if quiz else None,
                "difficulty": quiz.get("difficulty") if quiz else "Unknown",
                "score": data.get("score"),
                "totalQuestions": data.get("totalQuestions"),
                "percentage": data.get("percentage"),
                "completedAt": data.get("completedAt")
            })

        return history

    async def calculate_score(
        self,
        quiz_id: str,
        course_id: str,
        answers: List[int]
    ) -> Tuple[int, int, List[Dict]]:
        """Calculate score for a quiz submission.

        Args:
            quiz_id: Quiz ID
            course_id: Course ID
            answers: User's answer indices

        Returns:
            Tuple of (score, total_questions, question_results)

        Raises:
            ValueError: If quiz not found or answer count mismatch
        """
        quiz = await self.get_quiz(course_id, quiz_id)
        if not quiz:
            raise ValueError(f"Quiz {quiz_id} not found")

        questions = quiz.get("questions", [])
        if len(answers) != len(questions):
            raise ValueError(
                f"Expected {len(questions)} answers, got {len(answers)}"
            )

        score = 0
        results = []
        for i, (q, user_answer) in enumerate(zip(questions, answers)):
            correct_index = q.get("correct_index", 0)
            is_correct = user_answer == correct_index
            if is_correct:
                score += 1

            results.append({
                "questionIndex": i,
                "userAnswer": user_answer,
                "correctAnswer": correct_index,
                "isCorrect": is_correct,
                "explanation": q.get("explanation", "")
            })

        return score, len(questions), results


# Singleton instance
_quiz_persistence_service = None


def get_quiz_persistence_service() -> QuizPersistenceService:
    """Get the singleton quiz persistence service instance."""
    global _quiz_persistence_service
    if _quiz_persistence_service is None:
        _quiz_persistence_service = QuizPersistenceService()
    return _quiz_persistence_service


"""Tests for Quiz Persistence Service and API endpoints.

Tests cover:
- Quiz storage and retrieval
- Duplicate detection via content hashing
- Quiz result saving and scoring
- User quiz history
- API endpoints for quiz management
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.quiz_persistence_service import QuizPersistenceService


class TestContentHashing:
    """Tests for content hash generation."""

    def test_generate_content_hash_same_questions(self):
        """Same questions should produce same hash."""
        service = QuizPersistenceService()

        questions1 = [
            {"question": "What is contract law?"},
            {"question": "Define negligence."}
        ]
        questions2 = [
            {"question": "What is contract law?"},
            {"question": "Define negligence."}
        ]

        hash1 = service._generate_content_hash(questions1)
        hash2 = service._generate_content_hash(questions2)

        assert hash1 == hash2

    def test_generate_content_hash_different_order_same_hash(self):
        """Different order should produce same hash (sorted)."""
        service = QuizPersistenceService()

        questions1 = [
            {"question": "What is contract law?"},
            {"question": "Define negligence."}
        ]
        questions2 = [
            {"question": "Define negligence."},
            {"question": "What is contract law?"}
        ]

        hash1 = service._generate_content_hash(questions1)
        hash2 = service._generate_content_hash(questions2)

        assert hash1 == hash2

    def test_generate_content_hash_different_questions(self):
        """Different questions should produce different hash."""
        service = QuizPersistenceService()

        questions1 = [{"question": "What is contract law?"}]
        questions2 = [{"question": "What is tort law?"}]

        hash1 = service._generate_content_hash(questions1)
        hash2 = service._generate_content_hash(questions2)

        assert hash1 != hash2

    def test_generate_content_hash_length(self):
        """Hash should be 16 characters (truncated SHA-256)."""
        service = QuizPersistenceService()
        questions = [{"question": "Test question"}]

        hash_value = service._generate_content_hash(questions)

        assert len(hash_value) == 16


class TestSaveQuiz:
    """Tests for quiz saving functionality."""

    @pytest.mark.asyncio
    async def test_save_quiz_success(self):
        """Test successful quiz save."""
        service = QuizPersistenceService()

        mock_firestore = MagicMock()
        mock_doc = MagicMock()
        mock_firestore.collection.return_value.document.return_value.collection.return_value.document.return_value = mock_doc
        service._firestore = mock_firestore

        questions = [
            {"question": "Q1", "options": ["A", "B"], "correct_index": 0}
        ]

        result = await service.save_quiz(
            course_id="test-course",
            topic="Contract Law",
            difficulty="medium",
            questions=questions,
            week_number=3,
            title="Week 3 Quiz"
        )

        assert result["courseId"] == "test-course"
        assert result["topic"] == "Contract Law"
        assert result["difficulty"] == "medium"
        assert result["weekNumber"] == 3
        assert result["numQuestions"] == 1
        assert len(result["id"]) > 0
        assert len(result["contentHash"]) == 16
        mock_doc.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_quiz_no_firestore(self):
        """Test save quiz fails gracefully without Firestore."""
        service = QuizPersistenceService()
        service._firestore = None

        with pytest.raises(RuntimeError) as exc_info:
            await service.save_quiz(
                course_id="test-course",
                topic="Test",
                difficulty="easy",
                questions=[]
            )

        assert "Firestore not available" in str(exc_info.value)


class TestGetQuiz:
    """Tests for quiz retrieval."""

    @pytest.mark.asyncio
    async def test_get_quiz_found(self):
        """Test getting an existing quiz."""
        service = QuizPersistenceService()

        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "id": "quiz-123",
            "topic": "Contract Law",
            "questions": []
        }

        mock_firestore = MagicMock()
        mock_firestore.collection.return_value.document.return_value.collection.return_value.document.return_value.get.return_value = mock_doc
        service._firestore = mock_firestore

        result = await service.get_quiz("course-1", "quiz-123")

        assert result is not None
        assert result["id"] == "quiz-123"
        assert result["topic"] == "Contract Law"

    @pytest.mark.asyncio
    async def test_get_quiz_not_found(self):
        """Test getting a non-existent quiz."""
        service = QuizPersistenceService()

        mock_doc = MagicMock()
        mock_doc.exists = False

        mock_firestore = MagicMock()
        mock_firestore.collection.return_value.document.return_value.collection.return_value.document.return_value.get.return_value = mock_doc
        service._firestore = mock_firestore

        result = await service.get_quiz("course-1", "nonexistent")

        assert result is None


class TestSaveQuizResult:
    """Tests for saving quiz results."""

    @pytest.mark.asyncio
    async def test_save_result_success(self):
        """Test successful result save."""
        service = QuizPersistenceService()

        mock_doc = MagicMock()
        mock_firestore = MagicMock()
        mock_firestore.collection.return_value.document.return_value = mock_doc
        service._firestore = mock_firestore

        result = await service.save_quiz_result(
            quiz_id="quiz-123",
            course_id="course-1",
            user_id="user-abc",
            answers=[0, 1, 2, 0],
            score=3,
            total_questions=4,
            time_taken_seconds=120
        )

        assert result["quizId"] == "quiz-123"
        assert result["courseId"] == "course-1"
        assert result["userId"] == "user-abc"
        assert result["score"] == 3
        assert result["totalQuestions"] == 4
        assert result["percentage"] == 75.0
        assert result["timeTakenSeconds"] == 120
        mock_doc.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_result_calculates_percentage(self):
        """Test percentage calculation."""
        service = QuizPersistenceService()

        mock_firestore = MagicMock()
        service._firestore = mock_firestore

        result = await service.save_quiz_result(
            quiz_id="q1",
            course_id="c1",
            user_id="u1",
            answers=[0, 0, 0],
            score=2,
            total_questions=3
        )

        assert result["percentage"] == 66.7


class TestCalculateScore:
    """Tests for score calculation."""

    @pytest.mark.asyncio
    async def test_calculate_score_all_correct(self):
        """Test scoring when all answers correct."""
        service = QuizPersistenceService()

        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "questions": [
                {"question": "Q1", "correct_index": 0, "explanation": "A"},
                {"question": "Q2", "correct_index": 1, "explanation": "B"},
                {"question": "Q3", "correct_index": 2, "explanation": "C"}
            ]
        }

        mock_firestore = MagicMock()
        mock_firestore.collection.return_value.document.return_value.collection.return_value.document.return_value.get.return_value = mock_doc
        service._firestore = mock_firestore

        score, total, results = await service.calculate_score(
            quiz_id="quiz-1",
            course_id="course-1",
            answers=[0, 1, 2]
        )

        assert score == 3
        assert total == 3
        assert all(r["isCorrect"] for r in results)

    @pytest.mark.asyncio
    async def test_calculate_score_partial(self):
        """Test scoring with some wrong answers."""
        service = QuizPersistenceService()

        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "questions": [
                {"question": "Q1", "correct_index": 0, "explanation": "A"},
                {"question": "Q2", "correct_index": 1, "explanation": "B"}
            ]
        }

        mock_firestore = MagicMock()
        mock_firestore.collection.return_value.document.return_value.collection.return_value.document.return_value.get.return_value = mock_doc
        service._firestore = mock_firestore

        score, total, results = await service.calculate_score(
            quiz_id="quiz-1",
            course_id="course-1",
            answers=[0, 0]  # Second answer wrong
        )

        assert score == 1
        assert total == 2
        assert results[0]["isCorrect"] is True
        assert results[1]["isCorrect"] is False

    @pytest.mark.asyncio
    async def test_calculate_score_quiz_not_found(self):
        """Test error when quiz not found."""
        service = QuizPersistenceService()

        mock_doc = MagicMock()
        mock_doc.exists = False

        mock_firestore = MagicMock()
        mock_firestore.collection.return_value.document.return_value.collection.return_value.document.return_value.get.return_value = mock_doc
        service._firestore = mock_firestore

        with pytest.raises(ValueError) as exc_info:
            await service.calculate_score("q1", "c1", [0, 1])

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_calculate_score_answer_count_mismatch(self):
        """Test error when answer count doesn't match questions."""
        service = QuizPersistenceService()

        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "questions": [
                {"question": "Q1", "correct_index": 0},
                {"question": "Q2", "correct_index": 1}
            ]
        }

        mock_firestore = MagicMock()
        mock_firestore.collection.return_value.document.return_value.collection.return_value.document.return_value.get.return_value = mock_doc
        service._firestore = mock_firestore

        with pytest.raises(ValueError) as exc_info:
            await service.calculate_score("q1", "c1", [0])  # Only 1 answer for 2 questions

        assert "Expected 2 answers" in str(exc_info.value)


class TestListQuizzes:
    """Tests for listing quizzes."""

    @pytest.mark.asyncio
    async def test_list_quizzes_success(self):
        """Test listing quizzes for a course."""
        service = QuizPersistenceService()

        mock_doc1 = MagicMock()
        mock_doc1.to_dict.return_value = {
            "id": "quiz-1",
            "courseId": "course-1",
            "topic": "Contract Law",
            "difficulty": "medium",
            "weekNumber": 1,
            "numQuestions": 10,
            "createdAt": datetime.now(timezone.utc),
            "title": "Week 1 Quiz"
        }

        mock_doc2 = MagicMock()
        mock_doc2.to_dict.return_value = {
            "id": "quiz-2",
            "courseId": "course-1",
            "topic": "Tort Law",
            "difficulty": "hard",
            "weekNumber": 2,
            "numQuestions": 5,
            "createdAt": datetime.now(timezone.utc),
            "title": "Week 2 Quiz"
        }

        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_doc1, mock_doc2]
        mock_query.limit.return_value = mock_query

        mock_firestore = MagicMock()
        mock_firestore.collection.return_value.document.return_value.collection.return_value.order_by.return_value = mock_query
        service._firestore = mock_firestore

        result = await service.list_quizzes("course-1", limit=20)

        assert len(result) == 2
        assert result[0]["id"] == "quiz-1"
        assert result[1]["id"] == "quiz-2"

    @pytest.mark.asyncio
    async def test_list_quizzes_with_filter(self):
        """Test listing quizzes with topic filter."""
        service = QuizPersistenceService()

        mock_doc1 = MagicMock()
        mock_doc1.to_dict.return_value = {
            "id": "quiz-1",
            "courseId": "course-1",
            "topic": "Contract Law",
            "difficulty": "medium",
            "numQuestions": 10,
            "createdAt": datetime.now(timezone.utc)
        }

        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_doc1]
        mock_query.limit.return_value = mock_query

        mock_firestore = MagicMock()
        mock_firestore.collection.return_value.document.return_value.collection.return_value.order_by.return_value = mock_query
        service._firestore = mock_firestore

        # Filter for Contract Law only
        result = await service.list_quizzes("course-1", topic="Contract Law")

        assert len(result) == 1
        assert result[0]["topic"] == "Contract Law"

    @pytest.mark.asyncio
    async def test_list_quizzes_empty(self):
        """Test listing when no quizzes exist."""
        service = QuizPersistenceService()
        service._firestore = None

        result = await service.list_quizzes("course-1")

        assert result == []


class TestFindDuplicateQuiz:
    """Tests for duplicate quiz detection."""

    @pytest.mark.asyncio
    async def test_find_duplicate_found(self):
        """Test finding a duplicate quiz."""
        service = QuizPersistenceService()

        questions = [{"question": "What is contract law?"}]
        content_hash = service._generate_content_hash(questions)

        mock_doc = MagicMock()
        mock_doc.id = "existing-quiz"
        mock_doc.to_dict.return_value = {
            "id": "existing-quiz",
            "contentHash": content_hash,
            "topic": "Contract Law"
        }

        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value.stream.return_value = [mock_doc]

        mock_firestore = MagicMock()
        mock_firestore.collection.return_value.document.return_value.collection.return_value = mock_query
        service._firestore = mock_firestore

        result = await service.find_duplicate_quiz(
            course_id="course-1",
            topic="Contract Law",
            difficulty="medium",
            questions=questions
        )

        assert result is not None
        assert result["id"] == "existing-quiz"

    @pytest.mark.asyncio
    async def test_find_duplicate_not_found(self):
        """Test when no duplicate exists."""
        service = QuizPersistenceService()

        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value.stream.return_value = []

        mock_firestore = MagicMock()
        mock_firestore.collection.return_value.document.return_value.collection.return_value = mock_query
        service._firestore = mock_firestore

        result = await service.find_duplicate_quiz(
            course_id="course-1",
            topic="Contract Law",
            difficulty="medium",
            questions=[{"question": "New unique question"}]
        )

        assert result is None


# ============================================================================
# API Endpoint Tests
# ============================================================================

class TestQuizManagementAPI:
    """Tests for quiz management API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)

    def test_list_quizzes_endpoint(self, client):
        """Test GET /api/quizzes/courses/{course_id}."""
        with patch('app.routes.quiz_management.get_quiz_persistence_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.list_quizzes = AsyncMock(return_value=[
                {"id": "q1", "topic": "Contract Law", "numQuestions": 10}
            ])
            mock_get_service.return_value = mock_service

            response = client.get("/api/quizzes/courses/test-course")

            assert response.status_code == 200
            data = response.json()
            assert "quizzes" in data
            assert data["count"] == 1

    def test_get_quiz_endpoint_found(self, client):
        """Test GET /api/quizzes/courses/{course_id}/{quiz_id}."""
        with patch('app.routes.quiz_management.get_quiz_persistence_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_quiz = AsyncMock(return_value={
                "id": "quiz-123",
                "topic": "Contract Law",
                "questions": []
            })
            mock_get_service.return_value = mock_service

            response = client.get("/api/quizzes/courses/test-course/quiz-123")

            assert response.status_code == 200
            data = response.json()
            assert data["quiz"]["id"] == "quiz-123"

    def test_get_quiz_endpoint_not_found(self, client):
        """Test GET quiz returns 404 when not found."""
        with patch('app.routes.quiz_management.get_quiz_persistence_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_quiz = AsyncMock(return_value=None)
            mock_get_service.return_value = mock_service

            response = client.get("/api/quizzes/courses/test-course/nonexistent")

            assert response.status_code == 404

    def test_create_quiz_endpoint(self, client):
        """Test POST /api/quizzes/courses/{course_id}."""
        with patch('app.routes.quiz_management.get_quiz_persistence_service') as mock_persistence, \
             patch('app.routes.quiz_management.get_files_api_service') as mock_files:

            mock_files_service = MagicMock()
            mock_files_service.generate_quiz_from_course = AsyncMock(return_value={
                "questions": [{"question": "Q1", "correct_index": 0}]
            })
            mock_files.return_value = mock_files_service

            mock_persist_service = MagicMock()
            mock_persist_service.find_duplicate_quiz = AsyncMock(return_value=None)
            mock_persist_service.save_quiz = AsyncMock(return_value={
                "id": "new-quiz",
                "topic": "Contract Law",
                "questions": [{"question": "Q1"}]
            })
            mock_persistence.return_value = mock_persist_service

            response = client.post(
                "/api/quizzes/courses/test-course",
                json={
                    "course_id": "test-course",
                    "topic": "Contract Law",
                    "num_questions": 5,
                    "difficulty": "medium"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["is_new"] is True
            assert data["quiz"]["id"] == "new-quiz"

    def test_create_quiz_returns_existing_duplicate(self, client):
        """Test that duplicate quiz returns existing instead of creating new."""
        with patch('app.routes.quiz_management.get_quiz_persistence_service') as mock_persistence, \
             patch('app.routes.quiz_management.get_files_api_service') as mock_files:

            mock_files_service = MagicMock()
            mock_files_service.generate_quiz_from_course = AsyncMock(return_value={
                "questions": [{"question": "Q1"}]
            })
            mock_files.return_value = mock_files_service

            mock_persist_service = MagicMock()
            mock_persist_service.find_duplicate_quiz = AsyncMock(return_value={
                "id": "existing-quiz",
                "topic": "Contract Law"
            })
            mock_persistence.return_value = mock_persist_service

            response = client.post(
                "/api/quizzes/courses/test-course",
                json={
                    "course_id": "test-course",
                    "num_questions": 5,
                    "difficulty": "medium",
                    "allow_duplicate": False
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["is_new"] is False
            assert data["quiz"]["id"] == "existing-quiz"

    def test_get_quiz_history_endpoint(self, client):
        """Test GET /api/quizzes/history/{user_id}."""
        with patch('app.routes.quiz_management.get_quiz_persistence_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_user_quiz_history = AsyncMock(return_value=[
                {
                    "resultId": "r1",
                    "quizId": "q1",
                    "score": 8,
                    "totalQuestions": 10,
                    "percentage": 80.0
                }
            ])
            mock_get_service.return_value = mock_service

            response = client.get("/api/quizzes/history/user-123")

            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1
            assert data["history"][0]["score"] == 8


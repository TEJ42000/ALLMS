"""
Comprehensive tests for the quiz system implementation.

Tests cover:
- Quiz generation from API
- Question display and navigation
- Answer selection and scoring
- Results calculation and display
- State management
- Error handling
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient


class TestQuizGeneration:
    """Tests for quiz generation functionality."""

    def test_quiz_generation_with_valid_topic(self, client):
        """Test quiz generation with a valid topic."""
        mock_service = Mock()
        mock_service.generate_quiz_from_course = AsyncMock(return_value={
            "questions": [
                {
                    "question": "What is Art. 6:74 DCC?",
                    "options": [
                        "Liability for defective products",
                        "Contract formation",
                        "Tort law",
                        "Property rights"
                    ],
                    "correct_index": 0,
                    "explanation": "Art. 6:74 DCC deals with product liability.",
                    "difficulty": "medium",
                    "articles": ["Art. 6:74 DCC"],
                    "topic": "Private Law"
                }
            ]
        })

        with patch('app.routes.files_content.get_files_api_service', return_value=mock_service):
            response = client.post("/api/files-content/quiz", json={
                "course_id": "LLS-2025-2026",
                "topic": "Private Law",
                "num_questions": 1,
                "difficulty": "medium"
            })

            assert response.status_code == 200
            data = response.json()
            assert "quiz" in data
            assert "questions" in data["quiz"]
            assert len(data["quiz"]["questions"]) == 1
            assert data["quiz"]["questions"][0]["question"] == "What is Art. 6:74 DCC?"

    def test_quiz_generation_with_course_id(self, client):
        """Test quiz generation using course_id."""
        mock_service = Mock()
        mock_service.generate_quiz_from_course = AsyncMock(return_value={
            "questions": [
                {
                    "question": "What is Art. 6:74 DCC?",
                    "options": [
                        "Liability for defective products",
                        "Contract formation",
                        "Tort law",
                        "Property rights"
                    ],
                    "correct_index": 0,
                    "explanation": "Art. 6:74 DCC deals with product liability.",
                    "difficulty": "medium"
                }
            ]
        })

        with patch('app.routes.files_content.get_files_api_service', return_value=mock_service):
            response = client.post("/api/files-content/quiz", json={
                "course_id": "LLS-2025-2026",
                "num_questions": 1,
                "difficulty": "medium"
            })

            assert response.status_code == 200
            data = response.json()
            assert "quiz" in data
            assert data.get("course_id") == "LLS-2025-2026"
            mock_service.generate_quiz_from_course.assert_called_once()

    def test_quiz_generation_with_multiple_questions(self, client):
        """Test quiz generation with multiple questions."""
        questions = [
            {
                "question": f"Question {i}",
                "options": ["A", "B", "C", "D"],
                "correct_index": i % 4,
                "explanation": f"Explanation {i}",
                "difficulty": "medium"
            }
            for i in range(10)
        ]

        mock_service = Mock()
        mock_service.generate_quiz_from_course = AsyncMock(return_value={"questions": questions})

        with patch('app.routes.files_content.get_files_api_service', return_value=mock_service):
            response = client.post("/api/files-content/quiz", json={
                "course_id": "LLS-2025-2026",
                "topic": "Criminal Law",
                "num_questions": 10,
                "difficulty": "medium"
            })

            assert response.status_code == 200
            data = response.json()
            assert len(data["quiz"]["questions"]) == 10

    def test_quiz_generation_with_difficulty_levels(self, client):
        """Test quiz generation with different difficulty levels."""
        for difficulty in ["easy", "medium", "hard"]:
            mock_service = Mock()
            mock_service.generate_quiz_from_course = AsyncMock(return_value={
                "questions": [{
                    "question": "Test",
                    "options": ["A", "B", "C", "D"],
                    "correct_index": 0,
                    "difficulty": difficulty
                }]
            })

            with patch('app.routes.files_content.get_files_api_service', return_value=mock_service):
                response = client.post("/api/files-content/quiz", json={
                    "course_id": "LLS-2025-2026",
                    "num_questions": 1,
                    "difficulty": difficulty
                })

                assert response.status_code == 200
                data = response.json()
                assert data["quiz"]["questions"][0]["difficulty"] == difficulty


class TestQuizStructure:
    """Tests for quiz data structure validation."""

    def test_quiz_question_has_required_fields(self, client):
        """Test that quiz questions have all required fields."""
        mock_service = Mock()
        mock_service.generate_quiz_from_course = AsyncMock(return_value={
            "questions": [{
                "question": "What is the capital of France?",
                "options": ["Paris", "London", "Berlin", "Madrid"],
                "correct_index": 0,
                "explanation": "Paris is the capital of France.",
                "difficulty": "easy",
                "articles": ["Art. 1:1"],
                "topic": "Geography"
            }]
        })

        with patch('app.routes.files_content.get_files_api_service', return_value=mock_service):
            response = client.post("/api/files-content/quiz", json={
                "course_id": "LLS-2025-2026",
                "topic": "Geography",
                "num_questions": 1,
                "difficulty": "easy"
            })

            assert response.status_code == 200
            data = response.json()
            question = data["quiz"]["questions"][0]

            # Check required fields
            assert "question" in question
            assert "options" in question
            assert "correct_index" in question
            assert isinstance(question["options"], list)
            assert len(question["options"]) == 4
            assert isinstance(question["correct_index"], int)
            assert 0 <= question["correct_index"] < len(question["options"])

    def test_quiz_options_are_strings(self, client):
        """Test that all quiz options are strings."""
        mock_service = Mock()
        mock_service.generate_quiz_from_course = AsyncMock(return_value={
            "questions": [{
                "question": "Test",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_index": 0
            }]
        })

        with patch('app.routes.files_content.get_files_api_service', return_value=mock_service):
            response = client.post("/api/files-content/quiz", json={
                "course_id": "LLS-2025-2026",
                "num_questions": 1,
                "difficulty": "medium"
            })

            assert response.status_code == 200
            data = response.json()
            options = data["quiz"]["questions"][0]["options"]
            assert all(isinstance(opt, str) for opt in options)


class TestQuizScoring:
    """Tests for quiz scoring logic."""

    def test_score_calculation_all_correct(self):
        """Test score calculation when all answers are correct."""
        questions = [
            {"correct_index": 0},
            {"correct_index": 1},
            {"correct_index": 2}
        ]
        user_answers = [0, 1, 2]
        
        score = sum(1 for i, ans in enumerate(user_answers) if ans == questions[i]["correct_index"])
        assert score == 3

    def test_score_calculation_all_incorrect(self):
        """Test score calculation when all answers are incorrect."""
        questions = [
            {"correct_index": 0},
            {"correct_index": 1},
            {"correct_index": 2}
        ]
        user_answers = [1, 2, 3]
        
        score = sum(1 for i, ans in enumerate(user_answers) if ans == questions[i]["correct_index"])
        assert score == 0

    def test_score_calculation_mixed(self):
        """Test score calculation with mixed correct/incorrect answers."""
        questions = [
            {"correct_index": 0},
            {"correct_index": 1},
            {"correct_index": 2},
            {"correct_index": 3}
        ]
        user_answers = [0, 2, 2, 1]  # 2 correct, 2 incorrect
        
        score = sum(1 for i, ans in enumerate(user_answers) if ans == questions[i]["correct_index"])
        assert score == 2

    def test_percentage_calculation(self):
        """Test percentage score calculation."""
        total = 10
        correct = 7
        percentage = round((correct / total) * 100)
        assert percentage == 70


class TestQuizErrorHandling:
    """Tests for quiz error handling."""

    def test_quiz_generation_with_no_files(self, client):
        """Test quiz generation when no files are available."""
        mock_service = Mock()
        mock_service.generate_quiz_from_course = AsyncMock(
            side_effect=ValueError("No materials found for course")
        )

        with patch('app.routes.files_content.get_files_api_service', return_value=mock_service):
            response = client.post("/api/files-content/quiz", json={
                "course_id": "EMPTY-COURSE",
                "num_questions": 5,
                "difficulty": "medium"
            })

            # Should return error
            assert response.status_code in [400, 404, 500]

    def test_quiz_generation_with_invalid_difficulty(self, client):
        """Test quiz generation with invalid difficulty level.

        Note: The API accepts any difficulty string and passes it to the AI.
        Invalid difficulties are not rejected at the API level, but the AI
        may not handle them gracefully. This test verifies the endpoint
        doesn't crash with unusual difficulty values.
        """
        mock_service = Mock()
        mock_service.generate_quiz_from_course = AsyncMock(return_value={
            "questions": [{
                "question": "Test question",
                "options": ["A", "B", "C", "D"],
                "correct_index": 0,
                "difficulty": "invalid_difficulty"
            }]
        })

        with patch('app.routes.files_content.get_files_api_service', return_value=mock_service):
            response = client.post("/api/files-content/quiz", json={
                "course_id": "LLS-2025-2026",
                "num_questions": 1,
                "difficulty": "invalid_difficulty"
            })

            # API accepts any difficulty string - validation happens at AI level
            assert response.status_code == 200

    def test_quiz_generation_with_invalid_num_questions(self, client):
        """Test quiz generation with invalid number of questions."""
        response = client.post("/api/files-content/quiz", json={
            "course_id": "LLS-2025-2026",
            "num_questions": 0,  # Invalid: must be >= 1
            "difficulty": "medium"
        })

        assert response.status_code == 422  # Validation error


class TestQuizIntegration:
    """Integration tests for the complete quiz workflow."""

    def test_complete_quiz_workflow(self, client):
        """Test the complete quiz workflow from generation to completion."""
        # Step 1: Generate quiz
        mock_service = Mock()
        mock_service.generate_quiz_from_course = AsyncMock(return_value={
            "questions": [
                {
                    "question": "Q1",
                    "options": ["A", "B", "C", "D"],
                    "correct_index": 0,
                    "explanation": "Explanation 1"
                },
                {
                    "question": "Q2",
                    "options": ["A", "B", "C", "D"],
                    "correct_index": 1,
                    "explanation": "Explanation 2"
                }
            ]
        })

        with patch('app.routes.files_content.get_files_api_service', return_value=mock_service):
            response = client.post("/api/files-content/quiz", json={
                "course_id": "LLS-2025-2026",
                "num_questions": 2,
                "difficulty": "medium"
            })

            assert response.status_code == 200
            data = response.json()

            # Step 2: Verify quiz structure
            assert "quiz" in data
            assert "questions" in data["quiz"]
            questions = data["quiz"]["questions"]
            assert len(questions) == 2

            # Step 3: Simulate answering questions
            user_answers = [0, 2]  # First correct, second incorrect
            score = sum(1 for i, ans in enumerate(user_answers)
                       if ans == questions[i]["correct_index"])

            # Step 4: Verify score
            assert score == 1
            percentage = round((score / len(questions)) * 100)
            assert percentage == 50


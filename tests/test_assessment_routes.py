"""Unit tests for Assessment routes."""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import uuid

from app.routes.assessment import (
    get_or_create_user_id,
    extract_grade,
)


class TestUserIdGeneration:
    """Tests for user ID generation."""

    def test_get_or_create_user_id_with_header(self):
        """Test that provided user ID is returned."""
        user_id = get_or_create_user_id("user-123")
        
        assert user_id == "user-123"

    def test_get_or_create_user_id_without_header(self):
        """Test that simulated user ID is generated when none provided."""
        user_id = get_or_create_user_id(None)
        
        assert user_id.startswith("sim-")
        assert len(user_id) == 16  # "sim-" + 12 hex chars

    def test_get_or_create_user_id_empty_string(self):
        """Test that empty string is treated as no header."""
        user_id = get_or_create_user_id("")
        
        # Empty string is falsy, so should generate new ID
        assert user_id.startswith("sim-")

    def test_get_or_create_user_id_deterministic(self):
        """Test that each call generates a unique ID."""
        user_id1 = get_or_create_user_id(None)
        user_id2 = get_or_create_user_id(None)
        
        # Should be different (not deterministic)
        assert user_id1 != user_id2


class TestGradeExtraction:
    """Tests for grade extraction from AI feedback."""

    def test_extract_grade_standard_format(self):
        """Test extraction from standard GRADE: X/10 format."""
        feedback = "Great answer!\n\nGRADE: 8/10\n\nStrengths: ..."
        grade = extract_grade(feedback)
        
        assert grade == 8

    def test_extract_grade_lowercase(self):
        """Test extraction with lowercase 'grade'."""
        feedback = "Good work.\n\ngrade: 7/10\n\nFeedback: ..."
        grade = extract_grade(feedback)
        
        assert grade == 7

    def test_extract_grade_with_hash(self):
        """Test extraction with markdown header."""
        feedback = "## GRADE: 9/10\n\nExcellent analysis!"
        grade = extract_grade(feedback)
        
        assert grade == 9

    def test_extract_grade_score_format(self):
        """Test extraction from Score: X/10 format."""
        feedback = "Score: 6/10\n\nNeeds improvement."
        grade = extract_grade(feedback)
        
        assert grade == 6

    def test_extract_grade_minimum(self):
        """Test extraction of minimum grade."""
        feedback = "GRADE: 0/10"
        grade = extract_grade(feedback)
        
        assert grade == 0

    def test_extract_grade_maximum(self):
        """Test extraction of maximum grade."""
        feedback = "GRADE: 10/10"
        grade = extract_grade(feedback)
        
        assert grade == 10

    def test_extract_grade_invalid_too_high(self):
        """Test that grades > 10 are rejected."""
        feedback = "GRADE: 15/10"
        grade = extract_grade(feedback)
        
        assert grade is None

    def test_extract_grade_invalid_negative(self):
        """Test that negative grades are rejected."""
        feedback = "GRADE: -5/10"
        grade = extract_grade(feedback)
        
        assert grade is None

    def test_extract_grade_not_found(self):
        """Test when no grade pattern is found."""
        feedback = "This is feedback without a grade."
        grade = extract_grade(feedback)
        
        assert grade is None

    def test_extract_grade_multiple_patterns(self):
        """Test that first valid pattern is used."""
        feedback = "GRADE: 8/10\n\nScore: 7/10"
        grade = extract_grade(feedback)
        
        # Should extract first occurrence
        assert grade == 8

    def test_extract_grade_with_whitespace(self):
        """Test extraction with extra whitespace."""
        feedback = "GRADE:    9  /10"
        grade = extract_grade(feedback)
        
        assert grade == 9

    def test_extract_grade_case_insensitive(self):
        """Test case-insensitive matching."""
        feedback = "GrAdE: 7/10"
        grade = extract_grade(feedback)
        
        assert grade == 7


class TestAssessmentEndpoints:
    """Tests for assessment API endpoints."""

    @pytest.mark.asyncio
    @patch('app.routes.assessment.get_assessment_response')
    async def test_assess_answer_success(self, mock_get_response):
        """Test successful answer assessment."""
        from app.routes.assessment import router
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        # Mock AI response
        mock_get_response.return_value = {
            "feedback": "GRADE: 8/10\n\nGood answer!",
            "grade": 8
        }
        
        # Test request
        response = client.post(
            "/api/assessment/assess",
            json={
                "course_id": "CRIM-2025-2026",
                "question": "What is mens rea?",
                "answer": "Mens rea is the mental element of a crime.",
                "topic": "Mens Rea"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["grade"] == 8
        assert "feedback" in data

    @pytest.mark.asyncio
    @patch('app.routes.assessment.generate_essay_question')
    async def test_generate_essay_question_all_weeks(self, mock_generate):
        """Test essay question generation for all-weeks."""
        from app.routes.assessment import router
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        # Mock AI response
        mock_generate.return_value = {
            "question": "Analyze a scenario involving both mens rea and fair trial rights.",
            "topic": "Comprehensive Criminal Law",
            "key_concepts": ["mens rea", "ECHR Article 6"],
            "guidance": "Consider both substantive and procedural aspects."
        }
        
        # Test request
        response = client.post(
            "/api/assessment/essay/generate",
            json={
                "course_id": "CRIM-2025-2026",
                "topic": "all-weeks"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "question" in data
        assert "key_concepts" in data

    @pytest.mark.asyncio
    @patch('app.routes.assessment.generate_essay_question')
    async def test_generate_essay_question_part_a(self, mock_generate):
        """Test essay question generation for Part A."""
        from app.routes.assessment import router
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        # Mock AI response
        mock_generate.return_value = {
            "question": "Compare dolus eventualis with negligence.",
            "topic": "Part A: Mens Rea",
            "key_concepts": ["dolus eventualis", "negligence"],
            "guidance": "Discuss the acceptance/approval element."
        }
        
        # Test request
        response = client.post(
            "/api/assessment/essay/generate",
            json={
                "course_id": "CRIM-2025-2026",
                "topic": "part-a"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "question" in data

    @pytest.mark.asyncio
    @patch('app.routes.assessment.generate_essay_question')
    async def test_generate_essay_question_part_b(self, mock_generate):
        """Test essay question generation for Part B."""
        from app.routes.assessment import router
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        # Mock AI response
        mock_generate.return_value = {
            "question": "Analyze the Engel criteria in a specific case.",
            "topic": "Part B: ECHR",
            "key_concepts": ["Engel criteria", "autonomous interpretation"],
            "guidance": "Apply all three criteria."
        }
        
        # Test request
        response = client.post(
            "/api/assessment/essay/generate",
            json={
                "course_id": "CRIM-2025-2026",
                "topic": "part-b"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "question" in data


class TestErrorHandling:
    """Tests for error handling in assessment routes."""

    @pytest.mark.asyncio
    @patch('app.routes.assessment.get_assessment_response')
    async def test_assess_answer_api_error(self, mock_get_response):
        """Test handling of AI API errors."""
        from app.routes.assessment import router
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        # Mock API error
        mock_get_response.side_effect = Exception("API error")
        
        # Test request
        response = client.post(
            "/api/assessment/assess",
            json={
                "course_id": "CRIM-2025-2026",
                "question": "What is mens rea?",
                "answer": "Mens rea is the mental element.",
                "topic": "Mens Rea"
            }
        )
        
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_assess_answer_missing_fields(self):
        """Test validation of required fields."""
        from app.routes.assessment import router
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        # Test request with missing fields
        response = client.post(
            "/api/assessment/assess",
            json={
                "course_id": "CRIM-2025-2026"
                # Missing question, answer, topic
            }
        )
        
        assert response.status_code == 422  # Validation error


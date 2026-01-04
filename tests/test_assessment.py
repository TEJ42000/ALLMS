# tests/test_assessment.py - Tests for Assessment endpoints

import pytest
from unittest.mock import AsyncMock, patch
from app.routes.assessment import extract_grade


class TestExtractGrade:
    """Tests for the extract_grade function."""

    def test_extract_grade_standard_format(self):
        """Test extracting grade from standard format."""
        feedback = "## GRADE: 7/10\n\nGood work!"
        assert extract_grade(feedback) == 7

    def test_extract_grade_lowercase(self):
        """Test extracting grade from lowercase format."""
        feedback = "Grade: 8/10\n\nExcellent!"
        assert extract_grade(feedback) == 8

    def test_extract_grade_with_score_prefix(self):
        """Test extracting grade with Score prefix."""
        feedback = "Score: 6/10\n\nNeeds improvement."
        assert extract_grade(feedback) == 6

    def test_extract_grade_with_header(self):
        """Test extracting grade with markdown header."""
        feedback = "## GRADE: 9/10\n\nOutstanding work!"
        assert extract_grade(feedback) == 9

    def test_extract_grade_not_found(self):
        """Test when grade is not found."""
        feedback = "Good work, keep it up!"
        assert extract_grade(feedback) is None

    def test_extract_grade_invalid_range(self):
        """Test that grades outside 0-10 are rejected."""
        feedback = "GRADE: 15/10"  # Invalid
        assert extract_grade(feedback) is None

    def test_extract_grade_zero(self):
        """Test extracting grade of zero."""
        feedback = "GRADE: 0/10\n\nNeeds significant improvement."
        assert extract_grade(feedback) == 0

    def test_extract_grade_ten(self):
        """Test extracting perfect grade."""
        feedback = "GRADE: 10/10\n\nPerfect!"
        assert extract_grade(feedback) == 10


class TestAssessEndpoint:
    """Tests for the /api/assessment/assess endpoint."""

    def test_assess_success(self, client, sample_assessment_request, mock_assessment_response):
        """Test successful assessment request."""
        with patch('app.services.anthropic_client.client') as mock_client:
            mock_client.messages.create = AsyncMock(return_value=mock_assessment_response)
            
            response = client.post("/api/assessment/assess", json=sample_assessment_request)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "feedback" in data
            assert "grade" in data
            assert "timestamp" in data

    def test_assess_extracts_grade(self, client, sample_assessment_request, mock_assessment_response):
        """Test that grade is extracted from feedback."""
        with patch('app.services.anthropic_client.client') as mock_client:
            mock_client.messages.create = AsyncMock(return_value=mock_assessment_response)
            
            response = client.post("/api/assessment/assess", json=sample_assessment_request)
            
            data = response.json()
            assert data["grade"] == 7  # From mock_assessment_response

    def test_assess_minimal_request(self, client, sample_assessment_request_minimal, mock_assessment_response):
        """Test assessment with minimal fields (no question)."""
        with patch('app.services.anthropic_client.client') as mock_client:
            mock_client.messages.create = AsyncMock(return_value=mock_assessment_response)
            
            response = client.post("/api/assessment/assess", json=sample_assessment_request_minimal)
            
            assert response.status_code == 200

    def test_assess_invalid_topic_fails(self, client):
        """Test that invalid topic returns validation error."""
        response = client.post("/api/assessment/assess", json={
            "topic": "Invalid Topic",
            "answer": "A contract requires agreement between parties."
        })
        
        assert response.status_code == 422

    def test_assess_short_answer_fails(self, client):
        """Test that too short answer returns validation error."""
        response = client.post("/api/assessment/assess", json={
            "topic": "Private Law",
            "answer": "Short"  # Less than 10 characters
        })
        
        assert response.status_code == 422

    def test_assess_missing_topic_fails(self, client):
        """Test that missing topic returns validation error."""
        response = client.post("/api/assessment/assess", json={
            "answer": "A contract requires agreement between parties and must comply with the law."
        })
        
        assert response.status_code == 422

    def test_assess_api_error_handling(self, client, sample_assessment_request):
        """Test error handling when API call fails."""
        with patch('app.services.anthropic_client.client') as mock_client:
            mock_client.messages.create = AsyncMock(side_effect=Exception("API Error"))
            
            response = client.post("/api/assessment/assess", json=sample_assessment_request)
            
            assert response.status_code == 500


class TestRubricEndpoint:
    """Tests for the /api/assessment/rubric endpoint."""

    def test_get_rubric_success(self, client):
        """Test successful rubric retrieval."""
        response = client.get("/api/assessment/rubric")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "rubric" in data
        assert "topics" in data

    def test_rubric_contains_grade_levels(self, client):
        """Test that rubric contains all grade levels."""
        response = client.get("/api/assessment/rubric")
        
        data = response.json()
        rubric = data["rubric"]
        
        assert "9-10" in rubric
        assert "7-8" in rubric
        assert "5-6" in rubric
        assert "3-4" in rubric
        assert "0-2" in rubric

    def test_rubric_levels_have_criteria(self, client):
        """Test that each grade level has label and criteria."""
        response = client.get("/api/assessment/rubric")
        
        data = response.json()
        for level, details in data["rubric"].items():
            assert "label" in details
            assert "criteria" in details
            assert len(details["criteria"]) > 0


class TestSampleAnswersEndpoint:
    """Tests for the /api/assessment/sample-answers endpoint."""

    def test_get_sample_answers_success(self, client):
        """Test successful sample answers retrieval."""
        response = client.get("/api/assessment/sample-answers")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "samples" in data
        assert len(data["samples"]) > 0

    def test_sample_answers_have_required_fields(self, client):
        """Test that samples have required fields."""
        response = client.get("/api/assessment/sample-answers")
        
        data = response.json()
        for sample in data["samples"]:
            assert "topic" in sample
            assert "question" in sample
            assert "answers" in sample
            assert len(sample["answers"]) > 0


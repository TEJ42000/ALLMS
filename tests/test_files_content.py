# tests/test_files_content.py - Tests for Files API Content endpoints

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestFilesContentQuizEndpoint:
    """Tests for the /api/files-content/quiz endpoint."""

    def test_quiz_generation_success(self, client):
        """Test successful quiz generation."""
        mock_service = MagicMock()
        mock_service.get_topic_files.return_value = ["reader_private_law"]
        mock_service.generate_quiz_from_files = AsyncMock(return_value=[
            {"question": "What is Art. 6:74?", "options": ["A", "B", "C", "D"], "correct": 0}
        ])
        
        with patch('app.routes.files_content.get_files_api_service', return_value=mock_service):
            response = client.post("/api/files-content/quiz", json={
                "topic": "Private Law",
                "num_questions": 5,
                "difficulty": "medium"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "quiz" in data
            assert "files_used" in data

    def test_quiz_with_week_parameter(self, client):
        """Test quiz generation with week parameter."""
        mock_service = MagicMock()
        mock_service.get_topic_files.return_value = ["reader_admin_law"]
        mock_service.generate_quiz_from_files = AsyncMock(return_value=[])
        
        with patch('app.routes.files_content.get_files_api_service', return_value=mock_service):
            response = client.post("/api/files-content/quiz", json={
                "topic": "Administrative Law",
                "week": 3,
                "num_questions": 10,
                "difficulty": "hard"
            })
            
            assert response.status_code == 200


class TestFilesContentStudyGuideEndpoint:
    """Tests for the /api/files-content/study-guide endpoint."""

    def test_study_guide_generation_success(self, client):
        """Test successful study guide generation."""
        mock_service = MagicMock()
        mock_service.get_topic_files.return_value = ["reader_criminal_law"]
        mock_service.generate_study_guide = AsyncMock(return_value="# Study Guide\n\nContent...")
        
        with patch('app.routes.files_content.get_files_api_service', return_value=mock_service):
            response = client.post("/api/files-content/study-guide", json={
                "topic": "Criminal Law"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "guide" in data
            assert "topic" in data


class TestFilesContentArticleExplainEndpoint:
    """Tests for the /api/files-content/explain-article endpoint."""

    def test_article_explanation_success(self, client):
        """Test successful article explanation."""
        mock_service = MagicMock()
        mock_service.explain_article = AsyncMock(return_value="Art. 6:74 DCC establishes...")
        
        with patch('app.routes.files_content.get_files_api_service', return_value=mock_service):
            response = client.post("/api/files-content/explain-article", json={
                "article": "6:74",
                "code": "DCC"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "article" in data
            assert "explanation" in data
            assert "Art. 6:74 DCC" in data["article"]


class TestFilesContentCaseAnalysisEndpoint:
    """Tests for the /api/files-content/case-analysis endpoint."""

    def test_case_analysis_success(self, client):
        """Test successful case analysis."""
        mock_service = MagicMock()
        mock_service.get_topic_files.return_value = ["reader_admin_law"]
        mock_service.generate_case_analysis = AsyncMock(return_value="## Legal Analysis\n\n...")
        
        with patch('app.routes.files_content.get_files_api_service', return_value=mock_service):
            response = client.post("/api/files-content/case-analysis", json={
                "case_facts": "A municipality denied a permit without giving proper notice to the applicant. The applicant was not given an opportunity to be heard before the decision.",
                "topic": "Administrative Law"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "analysis" in data
            assert "topic" in data

    def test_case_analysis_short_facts_fails(self, client):
        """Test that too short case facts returns validation error."""
        response = client.post("/api/files-content/case-analysis", json={
            "case_facts": "Short facts",  # Less than 50 chars
            "topic": "Administrative Law"
        })
        
        assert response.status_code == 422


class TestFilesContentFlashcardsEndpoint:
    """Tests for the /api/files-content/flashcards endpoint."""

    def test_flashcards_generation_success(self, client):
        """Test successful flashcards generation."""
        mock_service = MagicMock()
        mock_service.get_topic_files.return_value = ["reader_constitutional_law"]
        mock_service.generate_flashcards = AsyncMock(return_value=[
            {"front": "Art. 120", "back": "Prohibition of constitutional review"}
        ])
        
        with patch('app.routes.files_content.get_files_api_service', return_value=mock_service):
            response = client.post("/api/files-content/flashcards", json={
                "topic": "Constitutional Law",
                "num_cards": 10
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "flashcards" in data
            assert "count" in data
            assert "topic" in data


class TestFilesContentInfoEndpoints:
    """Tests for information endpoints."""

    def test_available_files_endpoint(self, client):
        """Test listing available files."""
        mock_service = MagicMock()
        mock_service.list_available_files = AsyncMock(return_value=[
            {"id": "file1", "name": "reader.pdf", "size_mb": 1.5}
        ])
        
        with patch('app.routes.files_content.get_files_api_service', return_value=mock_service):
            response = client.get("/api/files-content/available-files")
            
            assert response.status_code == 200
            data = response.json()
            assert "files" in data
            assert "count" in data

    def test_status_endpoint(self, client):
        """Test Files API status check."""
        mock_service = MagicMock()
        mock_service.file_ids = {"reader": {"id": "123"}}
        mock_service.list_available_files = AsyncMock(return_value=[])
        
        with patch('app.routes.files_content.get_files_api_service', return_value=mock_service):
            response = client.get("/api/files-content/status")
            
            assert response.status_code == 200
            data = response.json()
            assert "status" in data

    def test_examples_endpoint(self, client):
        """Test usage examples endpoint."""
        response = client.get("/api/files-content/examples")
        
        assert response.status_code == 200
        data = response.json()
        assert "quiz" in data
        assert "study_guide" in data
        assert "explain_article" in data


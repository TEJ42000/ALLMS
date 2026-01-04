"""Pytest fixtures and configuration for the LLS Study Portal tests."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Set dummy API key before importing app
os.environ["ANTHROPIC_API_KEY"] = "test-api-key-for-testing"

# pylint: disable=wrong-import-position
from app.main import app  # noqa: E402


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_anthropic_response():
    """Create a mock Anthropic API response."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="This is a mock AI response.")]
    return mock_response


@pytest.fixture
def mock_tutor_response():
    """Create a mock tutor response with formatted content."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="""## Article 6:74 DCC - Damages

### Key Points
✅ This article establishes the basis for damages claims.
⚠️ Requires proof of attributable breach.

**Elements:**
1. Breach of obligation
2. Attributability
3. Damages
4. Causation

Art. 6:74 DCC is fundamental for contract law.""")]
    return mock_response


@pytest.fixture
def mock_assessment_response():
    """Create a mock assessment response with grade."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="""## GRADE: 7/10

### Overall Assessment
Good understanding of the topic.

### Strengths
✅ Identified key elements
✅ Used correct terminology

### Weaknesses
⚠️ Missing specific article citations
⚠️ Could provide more detail

### Key Takeaways
💡 Always cite specific articles in your answers.""")]
    return mock_response


@pytest.fixture
def mock_anthropic_client(mock_tutor_response):
    """Patch the Anthropic client for all tests."""
    with patch('app.services.anthropic_client.client') as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_tutor_response)
        yield mock_client


@pytest.fixture
def sample_chat_request():
    """Sample chat request data."""
    return {
        "message": "Explain Art. 6:74 DCC",
        "context": "Private Law"
    }


@pytest.fixture
def sample_chat_request_with_history():
    """Sample chat request with conversation history."""
    return {
        "message": "What about Art. 6:75?",
        "context": "Private Law",
        "conversation_history": [
            {"role": "user", "content": "Explain Art. 6:74 DCC"},
            {"role": "assistant", "content": "Art. 6:74 DCC establishes..."}
        ]
    }


@pytest.fixture
def sample_assessment_request():
    """Sample assessment request data."""
    return {
        "topic": "Private Law",
        "question": "What are the requirements for a valid contract?",
        "answer": (
            "A valid contract requires four elements: capacity, consensus, "
            "permissible content, and determinability."
        )
    }


@pytest.fixture
def sample_assessment_request_minimal():
    """Sample assessment request with minimal fields."""
    return {
        "topic": "Private Law",
        "answer": (
            "A contract requires agreement between parties and must be "
            "valid under the law."
        )
    }


@pytest.fixture
def mock_text_extraction():
    """Mock text extraction service for testing."""
    with patch('app.services.text_extractor.extract_text') as mock_extract:
        mock_extract.return_value = "This is extracted text from the document."
        yield mock_extract


@pytest.fixture
def sample_extraction_status():
    """Sample extraction status data for UI testing."""
    from datetime import datetime, timezone
    return {
        "path": "Course_Materials/LLS/lecture_week_1.pdf",
        "extracted": True,
        "charCount": 12000,
        "fileType": "pdf",
        "extractionDate": datetime.now(timezone.utc).isoformat(),
        "error": None
    }


@pytest.fixture
def sample_extraction_metrics():
    """Sample extraction metrics for dashboard testing."""
    return {
        "total": 42,
        "extracted": 36,
        "failed": 2,
        "pending": 4,
        "coverage": 86,
        "totalChars": 1250000,
        "byType": {
            "pdf": {"total": 35, "extracted": 30},
            "docx": {"total": 5, "extracted": 5},
            "png": {"total": 2, "extracted": 1}
        }
    }


@pytest.fixture
def mock_firestore_cache():
    """Mock Firestore cache service."""
    with patch('app.services.text_cache_service.TextCacheService') as mock_cache:
        mock_instance = MagicMock()
        mock_instance.get_cached_text.return_value = None
        mock_instance.cache_text.return_value = True
        mock_instance.get_stats.return_value = MagicMock(
            total_entries=0,
            total_characters=0,
            total_size_bytes=0,
            by_file_type={},
            cache_hit_rate=None
        )
        mock_cache.return_value = mock_instance
        yield mock_instance

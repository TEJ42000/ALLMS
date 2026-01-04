# tests/conftest.py - Pytest fixtures and configuration

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import os

# Set dummy API key before importing app
os.environ["ANTHROPIC_API_KEY"] = "test-api-key-for-testing"

from app.main import app


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
        "answer": "A valid contract requires four elements: capacity, consensus, permissible content, and determinability."
    }


@pytest.fixture
def sample_assessment_request_minimal():
    """Sample assessment request with minimal fields."""
    return {
        "topic": "Private Law",
        "answer": "A contract requires agreement between parties and must be valid under the law."
    }


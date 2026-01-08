"""Pytest fixtures and configuration for the LLS Study Portal tests."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "docker: marks tests that require Docker (deselect with '-m \"not docker\"')"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )

# Set test environment variables before importing app
os.environ["ANTHROPIC_API_KEY"] = "test-api-key-for-testing"
os.environ["AUTH_ENABLED"] = "false"  # Disable auth for tests by default
os.environ["AUTH_MOCK_USER_EMAIL"] = "dev@mgms.eu"  # Use valid domain for mock user
os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"  # Prevent GCP client initialization
os.environ["GCP_PROJECT_ID"] = "test-project"

# Mock Google Cloud clients BEFORE any imports
# This prevents the clients from trying to authenticate
import sys
_mock_secretmanager = MagicMock()
_mock_firestore = MagicMock()
_mock_storage = MagicMock()

# Mock the google.cloud modules
sys.modules['google.cloud.secretmanager'] = _mock_secretmanager
sys.modules['google.cloud.firestore'] = _mock_firestore
sys.modules['google.cloud.storage'] = _mock_storage

# Mock GCP services BEFORE importing app to prevent connection attempts
# This is critical because services are instantiated at module level

# 1. Mock Secret Manager (prevents timeout when getting API keys)
def _mock_get_secret(secret_id: str, version: str = "latest"):
    """Mock get_secret to return test values from environment."""
    env_var_name = secret_id.upper().replace("-", "_")
    return os.getenv(env_var_name)

_secret_patcher = patch('app.services.gcp_service.get_secret', side_effect=_mock_get_secret)
_secret_patcher.start()

# 2. Mock Firestore (prevents connection attempts)
_mock_firestore_client = MagicMock()
_mock_collection = MagicMock()
_mock_document = MagicMock()
_mock_subcollection = MagicMock()
_mock_doc_ref = MagicMock()
_mock_doc_snapshot = MagicMock()

# Setup chain: db.collection().document().collection()
_mock_firestore_client.collection.return_value = _mock_collection
_mock_collection.document.return_value = _mock_document
_mock_document.collection.return_value = _mock_subcollection
_mock_subcollection.document.return_value = _mock_doc_ref

# Mock document operations
_mock_doc_snapshot.exists = False
_mock_doc_ref.get.return_value = _mock_doc_snapshot
_mock_doc_ref.set.return_value = None
_mock_subcollection.stream.return_value = []

_firestore_patcher = patch('app.services.gcp_service.get_firestore_client', return_value=_mock_firestore_client)
_firestore_patcher.start()

# Clear any cached auth config before importing app
# This ensures our test environment variables are used
from app.services.auth_service import get_auth_config
get_auth_config.cache_clear()

# pylint: disable=wrong-import-position
from app.main import app  # noqa: E402
from app.models.auth_models import User  # noqa: E402


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


# =============================================================================
# Authentication Fixtures
# =============================================================================

@pytest.fixture
def mock_admin_user():
    """Create a mock admin user from @mgms.eu domain."""
    return User(
        email="admin@mgms.eu",
        user_id="admin-user-123",
        domain="mgms.eu",
        is_admin=True
    )


@pytest.fixture
def mock_regular_user():
    """Create a mock regular user from @mgms.eu domain."""
    return User(
        email="user@mgms.eu",
        user_id="regular-user-456",
        domain="mgms.eu",
        is_admin=True  # Domain users are admins
    )


@pytest.fixture
def mock_external_user():
    """Create a mock external user (not from mgms.eu domain)."""
    return User(
        email="guest@external.com",
        user_id="external-user-789",
        domain="external.com",
        is_admin=False
    )


@pytest.fixture
def mock_iap_headers():
    """Create mock IAP headers for authenticated requests."""
    return {
        "X-Goog-Authenticated-User-Email": "accounts.google.com:user@mgms.eu",
        "X-Goog-Authenticated-User-Id": "accounts.google.com:123456789"
    }


@pytest.fixture
def mock_iap_headers_external():
    """Create mock IAP headers for external user."""
    return {
        "X-Goog-Authenticated-User-Email": "accounts.google.com:guest@external.com",
        "X-Goog-Authenticated-User-Id": "accounts.google.com:987654321"
    }


# =============================================================================
# Firestore Mocking
# =============================================================================

@pytest.fixture(autouse=True)
def mock_firestore():
    """
    Mock Firestore client for all tests.

    This fixture is autouse=True, so it applies to all tests automatically.
    Tests that need specific Firestore behavior can override this.
    """
    with patch('app.services.gcp_service.get_firestore_client') as mock_get_client:
        # Create mock Firestore client
        mock_client = MagicMock()

        # Mock collection/document chain
        mock_collection = MagicMock()
        mock_document = MagicMock()
        mock_subcollection = MagicMock()

        # Setup chain: db.collection().document().collection()
        mock_client.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_document
        mock_document.collection.return_value = mock_subcollection

        # Mock document operations
        mock_doc_ref = MagicMock()
        mock_subcollection.document.return_value = mock_doc_ref

        # Mock get() to return non-existent document by default
        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.exists = False
        mock_doc_ref.get.return_value = mock_doc_snapshot

        # Mock set() to succeed
        mock_doc_ref.set.return_value = None

        # Mock stream() to return empty list by default
        mock_subcollection.stream.return_value = []

        # Return the mock client
        mock_get_client.return_value = mock_client

        yield mock_client

"""Unit tests for AI Tutor routes."""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException

from app.routes.ai_tutor import (
    _generate_cache_key,
    _get_cached_response,
    _cache_response,
)


class TestCacheKeyGeneration:
    """Tests for cache key generation."""

    def test_generate_cache_key_basic(self):
        """Test basic cache key generation."""
        key = _generate_cache_key("CRIM-2025-2026", "test", "Hello", None)
        
        # Should be a 64-character hex string (SHA-256)
        assert len(key) == 64
        assert all(c in '0123456789abcdef' for c in key)

    def test_generate_cache_key_deterministic(self):
        """Test that same inputs produce same key."""
        key1 = _generate_cache_key("CRIM-2025-2026", "test", "Hello", None)
        key2 = _generate_cache_key("CRIM-2025-2026", "test", "Hello", None)
        
        assert key1 == key2

    def test_generate_cache_key_case_insensitive(self):
        """Test that message is case-insensitive."""
        key1 = _generate_cache_key("CRIM-2025-2026", "test", "Hello", None)
        key2 = _generate_cache_key("CRIM-2025-2026", "test", "HELLO", None)
        
        assert key1 == key2

    def test_generate_cache_key_whitespace_normalized(self):
        """Test that whitespace is normalized."""
        key1 = _generate_cache_key("CRIM-2025-2026", "test", "Hello", None)
        key2 = _generate_cache_key("CRIM-2025-2026", "test", "  Hello  ", None)
        
        assert key1 == key2

    def test_generate_cache_key_different_course(self):
        """Test that different courses produce different keys."""
        key1 = _generate_cache_key("CRIM-2025-2026", "test", "Hello", None)
        key2 = _generate_cache_key("LLS-2025-2026", "test", "Hello", None)
        
        assert key1 != key2

    def test_generate_cache_key_different_context(self):
        """Test that different contexts produce different keys."""
        key1 = _generate_cache_key("CRIM-2025-2026", "context1", "Hello", None)
        key2 = _generate_cache_key("CRIM-2025-2026", "context2", "Hello", None)
        
        assert key1 != key2

    def test_generate_cache_key_with_week(self):
        """Test cache key generation with week number."""
        key1 = _generate_cache_key("CRIM-2025-2026", "test", "Hello", 1)
        key2 = _generate_cache_key("CRIM-2025-2026", "test", "Hello", 2)
        
        assert key1 != key2

    def test_generate_cache_key_week_none_vs_all(self):
        """Test that week=None is treated as 'all'."""
        key1 = _generate_cache_key("CRIM-2025-2026", "test", "Hello", None)
        key2 = _generate_cache_key("CRIM-2025-2026", "test", "Hello", None)
        
        assert key1 == key2


class TestCacheRetrieval:
    """Tests for cache retrieval."""

    @patch('app.routes.ai_tutor.get_firestore_client')
    def test_get_cached_response_hit(self, mock_get_db):
        """Test successful cache hit."""
        # Mock Firestore
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Mock document
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "response": "Cached response",
            "created_at": datetime.now(timezone.utc),
            "hit_count": 5
        }
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Test
        result = _get_cached_response("test_key")
        
        assert result == "Cached response"
        mock_doc_ref.update.assert_called_once()

    @patch('app.routes.ai_tutor.get_firestore_client')
    def test_get_cached_response_miss(self, mock_get_db):
        """Test cache miss."""
        # Mock Firestore
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Mock document doesn't exist
        mock_doc = MagicMock()
        mock_doc.exists = False
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Test
        result = _get_cached_response("test_key")
        
        assert result is None

    @patch('app.routes.ai_tutor.get_firestore_client')
    def test_get_cached_response_expired(self, mock_get_db):
        """Test expired cache entry."""
        # Mock Firestore
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Mock document with old timestamp
        old_time = datetime.now(timezone.utc) - timedelta(hours=25)
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "response": "Old response",
            "created_at": old_time,
            "hit_count": 5
        }
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Test
        result = _get_cached_response("test_key")
        
        assert result is None

    @patch('app.routes.ai_tutor.get_firestore_client')
    def test_get_cached_response_no_db(self, mock_get_db):
        """Test when Firestore is unavailable."""
        mock_get_db.return_value = None
        
        result = _get_cached_response("test_key")
        
        assert result is None

    @patch('app.routes.ai_tutor.get_firestore_client')
    def test_get_cached_response_atomic_increment(self, mock_get_db):
        """Test that hit count uses atomic increment."""
        from google.cloud.firestore import Increment
        
        # Mock Firestore
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Mock document
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "response": "Cached response",
            "created_at": datetime.now(timezone.utc),
            "hit_count": 5
        }
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Test
        result = _get_cached_response("test_key")
        
        # Verify atomic increment was used
        mock_doc_ref.update.assert_called_once()
        call_args = mock_doc_ref.update.call_args[0][0]
        assert "hit_count" in call_args
        assert isinstance(call_args["hit_count"], Increment)

    @patch('app.routes.ai_tutor.get_firestore_client')
    def test_get_cached_response_update_failure_graceful(self, mock_get_db):
        """Test that update failure doesn't break cache retrieval."""
        # Mock Firestore
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Mock document
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "response": "Cached response",
            "created_at": datetime.now(timezone.utc),
            "hit_count": 5
        }
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_doc_ref.update.side_effect = Exception("Update failed")
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Test - should still return response despite update failure
        result = _get_cached_response("test_key")
        
        assert result == "Cached response"


class TestCacheStorage:
    """Tests for cache storage."""

    @patch('app.routes.ai_tutor.get_firestore_client')
    def test_cache_response_success(self, mock_get_db):
        """Test successful cache storage."""
        # Mock Firestore
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        mock_doc_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Test
        _cache_response("test_key", "Test response", "CRIM-2025-2026", "test context")
        
        # Verify set was called
        mock_doc_ref.set.assert_called_once()
        call_args = mock_doc_ref.set.call_args[0][0]
        
        assert call_args["response"] == "Test response"
        assert call_args["course_id"] == "CRIM-2025-2026"
        assert call_args["context"] == "test context"
        assert call_args["hit_count"] == 0
        assert "created_at" in call_args

    @patch('app.routes.ai_tutor.get_firestore_client')
    def test_cache_response_no_db(self, mock_get_db):
        """Test cache storage when Firestore is unavailable."""
        mock_get_db.return_value = None
        
        # Should not raise exception
        _cache_response("test_key", "Test response", "CRIM-2025-2026", "test context")

    @patch('app.routes.ai_tutor.get_firestore_client')
    def test_cache_response_failure_graceful(self, mock_get_db):
        """Test that cache storage failure is handled gracefully."""
        # Mock Firestore
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.set.side_effect = Exception("Storage failed")
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Should not raise exception
        _cache_response("test_key", "Test response", "CRIM-2025-2026", "test context")


class TestRaceConditions:
    """Tests for race condition handling."""

    @patch('app.routes.ai_tutor.get_firestore_client')
    def test_concurrent_cache_hits_atomic(self, mock_get_db):
        """Test that concurrent cache hits use atomic increment."""
        from google.cloud.firestore import Increment
        
        # Mock Firestore
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Mock document
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "response": "Cached response",
            "created_at": datetime.now(timezone.utc),
            "hit_count": 10
        }
        
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Simulate multiple concurrent requests
        for _ in range(5):
            _get_cached_response("test_key")
        
        # Verify all updates used atomic increment
        assert mock_doc_ref.update.call_count == 5
        for call in mock_doc_ref.update.call_args_list:
            call_args = call[0][0]
            assert isinstance(call_args["hit_count"], Increment)


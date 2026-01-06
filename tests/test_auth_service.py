"""Tests for the authentication service.

Tests IAP header parsing, domain validation, and auth configuration.
"""

import os
from unittest.mock import patch, MagicMock

import pytest

from app.services.auth_service import (
    extract_user_from_iap_headers,
    validate_domain,
    get_auth_config,
)
from app.models.auth_models import AuthConfig, User


class TestIAPHeaderExtraction:
    """Tests for IAP header extraction functionality."""

    def test_extract_valid_headers(self):
        """Test extracting user from valid IAP headers."""
        mock_request = MagicMock()
        headers_dict = {
            "X-Goog-Authenticated-User-Email": "accounts.google.com:user@mgms.eu",
            "X-Goog-Authenticated-User-Id": "accounts.google.com:123456789"
        }
        mock_request.headers.get = headers_dict.get

        user = extract_user_from_iap_headers(mock_request)
        assert user is not None
        assert user.email == "user@mgms.eu"
        assert user.user_id == "123456789"

    def test_extract_missing_email_header(self):
        """Test extraction when email header is missing."""
        mock_request = MagicMock()
        mock_request.headers.get = lambda k, d=None: None

        user = extract_user_from_iap_headers(mock_request)
        assert user is None

    def test_extract_missing_id_header(self):
        """Test extraction when user ID header is missing."""
        mock_request = MagicMock()
        headers_dict = {
            "X-Goog-Authenticated-User-Email": "accounts.google.com:user@mgms.eu"
        }
        mock_request.headers.get = headers_dict.get

        user = extract_user_from_iap_headers(mock_request)
        assert user is None

    def test_extract_invalid_email_format(self):
        """Test extraction with invalid email format."""
        mock_request = MagicMock()
        headers_dict = {
            "X-Goog-Authenticated-User-Email": "invalid-format",
            "X-Goog-Authenticated-User-Id": "accounts.google.com:123456789"
        }
        mock_request.headers.get = headers_dict.get

        user = extract_user_from_iap_headers(mock_request)
        assert user is None


class TestDomainValidation:
    """Tests for domain validation functionality."""

    def test_mgms_domain_valid(self):
        """Test that @mgms.eu users pass domain validation."""
        user = User(email="user@mgms.eu", user_id="123", domain="mgms.eu")
        assert validate_domain(user) is True

    def test_mgms_domain_case_insensitive(self):
        """Test that domain check is case-insensitive."""
        user = User(email="user@MGMS.EU", user_id="123", domain="MGMS.EU")
        assert validate_domain(user) is True

    def test_other_domains_invalid(self):
        """Test that other domains fail validation."""
        user = User(email="user@gmail.com", user_id="123", domain="gmail.com")
        assert validate_domain(user) is False

        user2 = User(email="user@external.com", user_id="123", domain="external.com")
        assert validate_domain(user2) is False


class TestAuthConfig:
    """Tests for auth configuration."""

    def test_auth_config_from_env(self):
        """Test that auth config loads from environment."""
        # The test env already sets AUTH_ENABLED=false
        config = get_auth_config()
        assert isinstance(config, AuthConfig)
        assert config.auth_enabled is False  # Set in conftest.py

    def test_auth_config_defaults(self):
        """Test auth config default values."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear cache and test defaults
            get_auth_config.cache_clear()
            config = get_auth_config()
            assert config.auth_domain == "mgms.eu"
            # Restore cache for other tests
            get_auth_config.cache_clear()

    def test_mock_user_email_configurable(self):
        """Test that mock user email is configurable."""
        config = get_auth_config()
        # Should be set from conftest.py
        assert config.auth_mock_user_email == "dev@mgms.eu"


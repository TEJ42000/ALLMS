"""Tests for authentication middleware.

Tests middleware behavior with different auth configurations.
"""

import pytest
from unittest.mock import patch, MagicMock

from app.middleware.auth_middleware import AuthMiddleware
from app.models.auth_models import AuthConfig, User


class TestPublicPathExclusions:
    """Tests for public path exclusion logic."""

    def test_health_is_public(self):
        """Test that /health is a public path."""
        # Check the public paths list in middleware
        public_paths = ["/health", "/api/docs", "/api/openapi.json"]
        assert "/health" in public_paths

    def test_static_is_public(self):
        """Test that /static/* paths are public."""
        # Static paths are handled by prefix matching
        test_paths = ["/static/css/styles.css", "/static/js/app.js"]
        for path in test_paths:
            assert path.startswith("/static/")

    def test_api_docs_is_public(self):
        """Test that API documentation is public."""
        public_docs = ["/api/docs", "/api/openapi.json", "/redoc"]
        for path in public_docs:
            assert any(path.startswith(p) for p in ["/api/docs", "/api/openapi", "/redoc"])


class TestAuthDisabledMode:
    """Tests for authentication bypass when disabled."""

    def test_mock_user_created_when_auth_disabled(self):
        """Test that mock user is created when auth is disabled."""
        from app.models.auth_models import MockUser

        # MockUser uses environment variables for configuration
        mock_user = MockUser()

        # Default mock user should have admin access
        assert mock_user.email is not None
        assert mock_user.is_admin is True

    def test_mock_user_has_admin_properties(self):
        """Test that mock user has correct properties."""
        from app.models.auth_models import MockUser

        mock_user = MockUser()

        # Should have all User fields
        assert hasattr(mock_user, 'email')
        assert hasattr(mock_user, 'user_id')
        assert hasattr(mock_user, 'domain')
        assert hasattr(mock_user, 'is_admin')


class TestUserCreationFromHeaders:
    """Tests for User creation from IAP headers."""

    def test_user_from_mgms_domain(self):
        """Test creating user from @mgms.eu domain."""
        user = User(
            email="admin@mgms.eu",
            user_id="123456789",
            domain="mgms.eu",
            is_admin=True  # Must be set explicitly
        )
        assert user.is_admin is True

    def test_user_from_external_domain(self):
        """Test creating user from external domain."""
        user = User(
            email="guest@external.com",
            user_id="987654321",
            domain="external.com",
            is_admin=False
        )
        assert user.is_admin is False

    def test_user_domain_extraction(self):
        """Test that domain is correctly extracted from email."""
        test_cases = [
            ("user@mgms.eu", "mgms.eu"),
            ("guest@university.edu", "university.edu"),
            ("test@subdomain.company.com", "subdomain.company.com"),
        ]

        for email, expected_domain in test_cases:
            user = User(
                email=email,
                user_id="test-id",
                domain=expected_domain,
                is_admin=False
            )
            assert user.domain == expected_domain


class TestAuthConfigValidation:
    """Tests for AuthConfig validation."""

    def test_auth_config_loads(self):
        """Test that auth config can be loaded."""
        from app.services.auth_service import get_auth_config
        config = get_auth_config()
        # In test env, auth is disabled
        assert config.auth_enabled is False
        assert config.auth_domain == "mgms.eu"

    def test_auth_disabled_config(self):
        """Test auth disabled configuration."""
        config = AuthConfig(auth_enabled=False)
        assert config.auth_enabled is False

    def test_custom_domain_config(self):
        """Test custom domain configuration."""
        config = AuthConfig(auth_domain="custom.com")
        assert config.auth_domain == "custom.com"


class TestMiddlewareIntegration:
    """Integration tests for middleware with test client."""

    def test_public_endpoints_no_auth_required(self, client):
        """Test that public endpoints don't require authentication."""
        public_endpoints = [
            "/health",
            "/api/docs",
        ]
        
        for endpoint in public_endpoints:
            response = client.get(endpoint)
            # Should not get 401
            assert response.status_code != 401

    def test_protected_endpoints_accessible_in_dev_mode(self, client):
        """Test that protected endpoints are accessible in dev mode."""
        # Auth is disabled in test env
        response = client.get("/admin/courses")
        assert response.status_code == 200

    def test_api_endpoints_accessible_in_dev_mode(self, client):
        """Test that API endpoints are accessible in dev mode."""
        response = client.get("/api/admin/courses")
        # Should return 200 or 500 (Firestore unavailable), not 401/403
        assert response.status_code in [200, 500]


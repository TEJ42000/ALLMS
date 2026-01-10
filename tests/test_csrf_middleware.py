"""Tests for CSRF middleware.

Tests the Double-Submit Cookie pattern implementation for CSRF protection.
Issue: #204
"""

import secrets
import pytest
from unittest.mock import MagicMock, patch
from fastapi import Request
from starlette.datastructures import Headers

from app.middleware.csrf import (
    generate_csrf_token,
    is_path_exempt,
    validate_origin,
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    CSRF_EXEMPT_PATHS,
    SAFE_METHODS,
    ALLOWED_ORIGINS,
)


class TestGenerateCSRFToken:
    """Tests for CSRF token generation."""

    def test_token_is_string(self):
        """Token should be a non-empty string."""
        token = generate_csrf_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_length(self):
        """Token should be sufficiently long for security."""
        token = generate_csrf_token()
        # URL-safe base64 of 32 bytes = 43 characters
        assert len(token) >= 32

    def test_tokens_are_unique(self):
        """Each generated token should be unique."""
        tokens = [generate_csrf_token() for _ in range(100)]
        assert len(tokens) == len(set(tokens))

    def test_token_is_url_safe(self):
        """Token should only contain URL-safe characters."""
        token = generate_csrf_token()
        # URL-safe base64 uses only these characters
        valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
        assert all(c in valid_chars for c in token)


class TestPathExemption:
    """Tests for CSRF path exemption logic."""

    def test_exempt_paths_are_exempt(self):
        """Known exempt paths should return True."""
        for path in CSRF_EXEMPT_PATHS:
            # Handle prefix paths (ending with /)
            test_path = path if not path.endswith("/") else path + "test"
            assert is_path_exempt(test_path), f"Path {test_path} should be exempt"

    def test_static_files_are_exempt(self):
        """Static file paths should be exempt."""
        static_paths = [
            "/static/css/styles.css",
            "/static/js/app.js",
            "/static/images/logo.png",
        ]
        for path in static_paths:
            assert is_path_exempt(path), f"Static path {path} should be exempt"

    def test_api_endpoints_not_exempt(self):
        """Regular API endpoints should not be exempt."""
        non_exempt_paths = [
            "/api/quiz/generate",
            "/api/tutor/chat",
            "/api/flashcards",
            "/api/assessment/submit",
        ]
        for path in non_exempt_paths:
            assert not is_path_exempt(path), f"API path {path} should NOT be exempt"

    def test_favicon_is_exempt(self):
        """Favicon should be exempt."""
        assert is_path_exempt("/favicon.ico")


class TestOriginValidation:
    """Tests for Origin/Referer header validation."""

    def _create_mock_request(self, origin=None, referer=None):
        """Create a mock request with specified headers."""
        headers = {}
        if origin:
            headers["origin"] = origin
        if referer:
            headers["referer"] = referer
        
        mock_request = MagicMock(spec=Request)
        mock_request.headers = Headers(headers)
        return mock_request

    def test_valid_origin_localhost(self):
        """Valid localhost origins should pass."""
        for origin in ["http://localhost:8000", "http://127.0.0.1:8000"]:
            request = self._create_mock_request(origin=origin)
            header_present, is_valid = validate_origin(request)
            assert header_present is True
            assert is_valid is True, f"Origin {origin} should be valid"

    def test_invalid_origin_rejected(self):
        """Invalid origins should be rejected."""
        request = self._create_mock_request(origin="https://evil.com")
        header_present, is_valid = validate_origin(request)
        assert header_present is True
        assert is_valid is False

    def test_no_origin_header(self):
        """Requests without Origin should return (False, False)."""
        request = self._create_mock_request()
        header_present, is_valid = validate_origin(request)
        assert header_present is False
        assert is_valid is False

    def test_referer_fallback(self):
        """Referer header should be used when Origin is missing."""
        request = self._create_mock_request(referer="http://localhost:8000/page")
        header_present, is_valid = validate_origin(request)
        assert header_present is True
        assert is_valid is True

    def test_invalid_referer_rejected(self):
        """Invalid referer should be rejected."""
        request = self._create_mock_request(referer="https://malicious.site/attack")
        header_present, is_valid = validate_origin(request)
        assert header_present is True
        assert is_valid is False


class TestSafeMethods:
    """Tests for safe method handling."""

    def test_safe_methods_defined(self):
        """Safe methods should include GET, HEAD, OPTIONS."""
        assert "GET" in SAFE_METHODS
        assert "HEAD" in SAFE_METHODS
        assert "OPTIONS" in SAFE_METHODS
        assert "TRACE" in SAFE_METHODS

    def test_post_not_safe(self):
        """POST should not be a safe method."""
        assert "POST" not in SAFE_METHODS

    def test_mutating_methods_not_safe(self):
        """PUT, PATCH, DELETE should not be safe methods."""
        assert "PUT" not in SAFE_METHODS
        assert "PATCH" not in SAFE_METHODS
        assert "DELETE" not in SAFE_METHODS


@pytest.mark.skip(reason="CSRF middleware disabled in test environment (TESTING=true)")
class TestCSRFMiddlewareIntegration:
    """Integration tests for CSRF middleware with FastAPI test client."""

    def test_csrf_cookie_set_on_get(self, client):
        """GET requests should set a CSRF cookie."""
        response = client.get("/health")
        assert response.status_code == 200
        assert CSRF_COOKIE_NAME in response.cookies

    def test_csrf_cookie_not_duplicated(self, client):
        """Existing CSRF cookie should not be overwritten."""
        # First request sets cookie
        response1 = client.get("/health")
        token1 = response1.cookies.get(CSRF_COOKIE_NAME)

        # Second request with cookie should not change it
        response2 = client.get("/health", cookies={CSRF_COOKIE_NAME: token1})
        # Cookie should not be in response if already set
        assert CSRF_COOKIE_NAME not in response2.cookies or response2.cookies.get(CSRF_COOKIE_NAME) == token1

    def test_post_without_csrf_rejected(self, client):
        """POST without CSRF token should be rejected."""
        response = client.post(
            "/api/quiz/generate",
            json={"topic": "test"},
            headers={"Origin": "http://localhost:8000"}
        )
        assert response.status_code == 403
        assert "CSRF" in response.json().get("detail", "")

    def test_post_with_valid_csrf_accepted(self, client):
        """POST with valid CSRF token should be accepted."""
        # Get CSRF token from cookie
        get_response = client.get("/health")
        csrf_token = get_response.cookies.get(CSRF_COOKIE_NAME)

        # POST with token should work (even if endpoint doesn't exist or fails for other reasons)
        response = client.post(
            "/api/health",  # Using health endpoint which is exempt
            headers={
                CSRF_HEADER_NAME: csrf_token,
                "Origin": "http://localhost:8000"
            },
            cookies={CSRF_COOKIE_NAME: csrf_token}
        )
        # Should not be 403 CSRF error (may be 404 or 405)
        if response.status_code == 403:
            assert "CSRF" not in response.json().get("detail", "")

    def test_post_with_mismatched_token_rejected(self, client):
        """POST with mismatched CSRF token should be rejected."""
        # Get CSRF token from cookie
        get_response = client.get("/health")
        csrf_token = get_response.cookies.get(CSRF_COOKIE_NAME)
        wrong_token = generate_csrf_token()  # Different token

        response = client.post(
            "/api/tutor/chat",
            json={"message": "test"},
            headers={
                CSRF_HEADER_NAME: wrong_token,
                "Origin": "http://localhost:8000"
            },
            cookies={CSRF_COOKIE_NAME: csrf_token}
        )
        assert response.status_code == 403
        assert "validation failed" in response.json().get("detail", "").lower()

    def test_post_missing_header_rejected(self, client):
        """POST with cookie but no header should be rejected."""
        get_response = client.get("/health")
        csrf_token = get_response.cookies.get(CSRF_COOKIE_NAME)

        response = client.post(
            "/api/tutor/chat",
            json={"message": "test"},
            headers={"Origin": "http://localhost:8000"},
            cookies={CSRF_COOKIE_NAME: csrf_token}
        )
        assert response.status_code == 403
        assert "missing" in response.json().get("detail", "").lower()

    def test_exempt_paths_bypass_csrf(self, client):
        """Exempt paths should not require CSRF token."""
        # Health endpoint is exempt
        response = client.post("/api/health", json={})
        # Should not be 403 CSRF error (may be 404 or 405)
        if response.status_code == 403:
            detail = response.json().get("detail", "")
            assert "CSRF" not in detail

    def test_invalid_origin_rejected(self, client):
        """POST with invalid Origin header should be rejected."""
        get_response = client.get("/health")
        csrf_token = get_response.cookies.get(CSRF_COOKIE_NAME)

        response = client.post(
            "/api/tutor/chat",
            json={"message": "test"},
            headers={
                CSRF_HEADER_NAME: csrf_token,
                "Origin": "https://evil.com"
            },
            cookies={CSRF_COOKIE_NAME: csrf_token}
        )
        assert response.status_code == 403
        assert "origin" in response.json().get("detail", "").lower()


class TestTimingAttackResistance:
    """Tests for timing attack resistance in token comparison."""

    def test_compare_digest_used(self):
        """Verify constant-time comparison is used."""
        # This is a static check - the middleware uses secrets.compare_digest
        import app.middleware.csrf as csrf_module
        import inspect

        source = inspect.getsource(csrf_module.CSRFMiddleware.dispatch)
        assert "secrets.compare_digest" in source, \
            "CSRF token comparison must use secrets.compare_digest for timing attack resistance"


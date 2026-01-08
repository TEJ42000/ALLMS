"""Unit tests for Streak System API endpoints.

Tests cover:
- GET /api/gamification/streak/calendar
- GET /api/gamification/streak/consistency
- POST /api/gamification/streak/maintenance (admin only)
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from app.main import app
from app.models.gamification_models import UserStats, StreakInfo


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {
        "user_id": "test_user_123",
        "email": "test@example.com",
        "is_admin": False
    }


@pytest.fixture
def mock_admin_user():
    """Mock admin user."""
    return {
        "user_id": "admin_user",
        "email": "admin@example.com",
        "is_admin": True
    }


class TestStreakCalendarAPI:
    """Test streak calendar API endpoint."""

    def test_get_calendar_success(self, client, mock_user):
        """Test successful calendar retrieval."""
        with patch('app.routes.gamification.get_current_user', return_value=mock_user):
            with patch('app.routes.gamification.get_gamification_service') as mock_service:
                # Mock service response
                mock_service_instance = Mock()
                mock_service.return_value = mock_service_instance
                
                # Mock user stats
                stats = UserStats(
                    user_id="test_user_123",
                    user_email="test@example.com",
                    streak=StreakInfo(
                        current_count=5,
                        longest_count=10,
                        freezes_available=2
                    )
                )
                mock_service_instance.get_or_create_user_stats.return_value = stats
                
                # Mock activity history
                mock_service_instance.get_user_activities.return_value = ([], None)
                
                # Make request
                response = client.get("/api/gamification/streak/calendar?days=30")
                
                # Should succeed
                assert response.status_code == 200
                data = response.json()
                assert "calendar" in data
                assert "current_streak" in data
                assert "longest_streak" in data
                assert "freezes_available" in data

    def test_get_calendar_invalid_days(self, client, mock_user):
        """Test calendar with invalid days parameter."""
        with patch('app.routes.gamification.get_current_user', return_value=mock_user):
            # Request too many days
            response = client.get("/api/gamification/streak/calendar?days=100")
            
            # Should fail validation
            assert response.status_code == 400

    def test_get_calendar_unauthorized(self, client):
        """Test calendar without authentication."""
        # No auth header
        response = client.get("/api/gamification/streak/calendar")
        
        # Should require authentication
        assert response.status_code in [401, 403]


class TestWeeklyConsistencyAPI:
    """Test weekly consistency API endpoint."""

    def test_get_consistency_success(self, client, mock_user):
        """Test successful consistency retrieval."""
        with patch('app.routes.gamification.get_current_user', return_value=mock_user):
            with patch('app.routes.gamification.get_gamification_service') as mock_service:
                # Mock service response
                mock_service_instance = Mock()
                mock_service.return_value = mock_service_instance
                
                # Mock user stats with partial consistency
                stats = UserStats(
                    user_id="test_user_123",
                    user_email="test@example.com",
                    streak=StreakInfo(
                        weekly_consistency={
                            "flashcards": True,
                            "quiz": True,
                            "evaluation": False,
                            "guide": False
                        },
                        bonus_active=False,
                        bonus_multiplier=1.0
                    )
                )
                mock_service_instance.get_or_create_user_stats.return_value = stats
                
                # Make request
                response = client.get("/api/gamification/streak/consistency")
                
                # Should succeed
                assert response.status_code == 200
                data = response.json()
                assert "week_start" in data
                assert "week_end" in data
                assert "categories" in data
                assert "bonus_active" in data
                assert "completion_percentage" in data
                
                # Check completion percentage (2 out of 4 = 50%)
                assert data["completion_percentage"] == 50

    def test_get_consistency_bonus_active(self, client, mock_user):
        """Test consistency with active bonus."""
        with patch('app.routes.gamification.get_current_user', return_value=mock_user):
            with patch('app.routes.gamification.get_gamification_service') as mock_service:
                # Mock service response
                mock_service_instance = Mock()
                mock_service.return_value = mock_service_instance
                
                # Mock user stats with active bonus
                stats = UserStats(
                    user_id="test_user_123",
                    user_email="test@example.com",
                    streak=StreakInfo(
                        weekly_consistency={
                            "flashcards": True,
                            "quiz": True,
                            "evaluation": True,
                            "guide": True
                        },
                        bonus_active=True,
                        bonus_multiplier=1.5
                    )
                )
                mock_service_instance.get_or_create_user_stats.return_value = stats
                
                # Make request
                response = client.get("/api/gamification/streak/consistency")
                
                # Should succeed
                assert response.status_code == 200
                data = response.json()
                assert data["bonus_active"] is True
                assert data["bonus_multiplier"] == 1.5
                assert data["completion_percentage"] == 100

    def test_get_consistency_unauthorized(self, client):
        """Test consistency without authentication."""
        # No auth header
        response = client.get("/api/gamification/streak/consistency")
        
        # Should require authentication
        assert response.status_code in [401, 403]


class TestStreakMaintenanceAPI:
    """Test streak maintenance admin endpoint."""

    def test_maintenance_success_admin(self, client, mock_admin_user):
        """Test successful maintenance run by admin."""
        with patch('app.routes.gamification.get_current_user', return_value=mock_admin_user):
            with patch('app.routes.gamification.get_streak_maintenance_service') as mock_service:
                # Mock service response
                mock_service_instance = Mock()
                mock_service.return_value = mock_service_instance
                
                mock_service_instance.run_daily_maintenance.return_value = {
                    "success": True,
                    "users_processed": 100,
                    "freezes_applied": 5,
                    "streaks_broken": 2
                }
                
                # Make request
                response = client.post("/api/gamification/streak/maintenance")
                
                # Should succeed
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["users_processed"] == 100

    def test_maintenance_forbidden_non_admin(self, client, mock_user):
        """Test maintenance blocked for non-admin users."""
        with patch('app.routes.gamification.get_current_user', return_value=mock_user):
            # Make request as non-admin
            response = client.post("/api/gamification/streak/maintenance")
            
            # Should be forbidden
            assert response.status_code == 403

    def test_maintenance_unauthorized(self, client):
        """Test maintenance without authentication."""
        # No auth header
        response = client.post("/api/gamification/streak/maintenance")
        
        # Should require authentication
        assert response.status_code in [401, 403]


class TestStreakAPIIntegration:
    """Integration tests for streak API endpoints."""

    def test_calendar_and_consistency_consistency(self, client, mock_user):
        """Test that calendar and consistency endpoints return consistent data."""
        with patch('app.routes.gamification.get_current_user', return_value=mock_user):
            with patch('app.routes.gamification.get_gamification_service') as mock_service:
                # Mock service response
                mock_service_instance = Mock()
                mock_service.return_value = mock_service_instance
                
                # Mock user stats
                stats = UserStats(
                    user_id="test_user_123",
                    user_email="test@example.com",
                    streak=StreakInfo(
                        current_count=5,
                        longest_count=10,
                        freezes_available=2,
                        weekly_consistency={
                            "flashcards": True,
                            "quiz": False,
                            "evaluation": False,
                            "guide": False
                        },
                        bonus_active=False,
                        bonus_multiplier=1.0
                    )
                )
                mock_service_instance.get_or_create_user_stats.return_value = stats
                mock_service_instance.get_user_activities.return_value = ([], None)
                
                # Get calendar
                calendar_response = client.get("/api/gamification/streak/calendar")
                assert calendar_response.status_code == 200
                calendar_data = calendar_response.json()
                
                # Get consistency
                consistency_response = client.get("/api/gamification/streak/consistency")
                assert consistency_response.status_code == 200
                consistency_data = consistency_response.json()
                
                # Both should show same streak count
                assert calendar_data["current_streak"] == 5
                
                # Both should show same bonus status
                assert consistency_data["bonus_active"] is False


class TestStreakAPIErrorHandling:
    """Test error handling in streak API endpoints."""

    def test_calendar_service_error(self, client, mock_user):
        """Test calendar endpoint handles service errors gracefully."""
        with patch('app.routes.gamification.get_current_user', return_value=mock_user):
            with patch('app.routes.gamification.get_gamification_service') as mock_service:
                # Mock service to raise exception
                mock_service_instance = Mock()
                mock_service.return_value = mock_service_instance
                mock_service_instance.get_or_create_user_stats.side_effect = Exception("Database error")
                
                # Make request
                response = client.get("/api/gamification/streak/calendar")
                
                # Should return 500 error
                assert response.status_code == 500

    def test_consistency_service_error(self, client, mock_user):
        """Test consistency endpoint handles service errors gracefully."""
        with patch('app.routes.gamification.get_current_user', return_value=mock_user):
            with patch('app.routes.gamification.get_gamification_service') as mock_service:
                # Mock service to raise exception
                mock_service_instance = Mock()
                mock_service.return_value = mock_service_instance
                mock_service_instance.get_or_create_user_stats.side_effect = Exception("Database error")
                
                # Make request
                response = client.get("/api/gamification/streak/consistency")
                
                # Should return 500 error
                assert response.status_code == 500

    def test_maintenance_service_error(self, client, mock_admin_user):
        """Test maintenance endpoint handles service errors gracefully."""
        with patch('app.routes.gamification.get_current_user', return_value=mock_admin_user):
            with patch('app.routes.gamification.get_streak_maintenance_service') as mock_service:
                # Mock service to raise exception
                mock_service_instance = Mock()
                mock_service.return_value = mock_service_instance
                mock_service_instance.run_daily_maintenance.side_effect = Exception("Maintenance error")
                
                # Make request
                response = client.post("/api/gamification/streak/maintenance")
                
                # Should return 500 error
                assert response.status_code == 500


"""Tests for Gamification API endpoints."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.models.gamification_models import (
    UserStats,
    UserActivity,
    ActivityLogResponse,
    StreakInfo,
    ActivityCounters,
    Week7Quest,
)


class TestGamificationStatsEndpoint:
    """Tests for GET /api/gamification/stats endpoint."""

    @patch('app.routes.gamification.get_gamification_service')
    def test_get_stats_success(self, mock_get_service, client):
        """Test getting user stats successfully."""
        # Mock service
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        # Mock stats
        mock_stats = UserStats(
            user_id="test-user",
            user_email="test@example.com",
            total_xp=1500,
            current_level=15,
            level_title="Summer Associate",
            xp_to_next_level=100
        )
        mock_service.get_or_create_user_stats.return_value = mock_stats
        
        # Make request
        response = client.get("/api/gamification/stats")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total_xp"] == 1500
        assert data["current_level"] == 15
        assert data["level_title"] == "Summer Associate"
        assert data["xp_to_next_level"] == 100

    @patch('app.routes.gamification.get_gamification_service')
    def test_get_stats_service_failure(self, mock_get_service, client):
        """Test handling service failure."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.get_or_create_user_stats.return_value = None
        
        response = client.get("/api/gamification/stats")
        assert response.status_code == 500


class TestActivityLogEndpoint:
    """Tests for POST /api/gamification/activity endpoint."""

    @patch('app.routes.gamification.get_gamification_service')
    def test_log_activity_success(self, mock_get_service, client):
        """Test logging activity successfully."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        # Mock response
        mock_response = ActivityLogResponse(
            activity_id="activity-123",
            xp_awarded=10,
            new_total_xp=110,
            level_up=False,
            new_level=None,
            new_level_title=None,
            streak_maintained=True,
            badges_earned=[]
        )
        mock_service.log_activity.return_value = mock_response
        
        # Make request
        response = client.post("/api/gamification/activity", json={
            "activity_type": "quiz_completed",
            "activity_data": {
                "score": 8,
                "total_questions": 10,
                "difficulty": "easy"
            }
        })
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["xp_awarded"] == 10
        assert data["new_total_xp"] == 110
        assert data["level_up"] == False

    @patch('app.routes.gamification.get_gamification_service')
    def test_log_activity_level_up(self, mock_get_service, client):
        """Test logging activity that causes level up."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        mock_response = ActivityLogResponse(
            activity_id="activity-123",
            xp_awarded=50,
            new_total_xp=1000,
            level_up=True,
            new_level=11,
            new_level_title="Summer Associate",
            streak_maintained=True,
            badges_earned=[]
        )
        mock_service.log_activity.return_value = mock_response
        
        response = client.post("/api/gamification/activity", json={
            "activity_type": "evaluation_completed",
            "activity_data": {"grade": 8}
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["level_up"] == True
        assert data["new_level"] == 11
        assert data["new_level_title"] == "Summer Associate"

    @patch('app.routes.gamification.get_gamification_service')
    def test_log_activity_service_failure(self, mock_get_service, client):
        """Test handling service failure."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.log_activity.return_value = None
        
        response = client.post("/api/gamification/activity", json={
            "activity_type": "quiz_completed",
            "activity_data": {"score": 8, "total_questions": 10}
        })
        
        assert response.status_code == 500


class TestXPConfigEndpoints:
    """Tests for XP configuration endpoints."""

    @patch('app.routes.gamification.get_gamification_service')
    def test_get_xp_config(self, mock_get_service, client):
        """Test getting XP configuration."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        # Mock config
        mock_config = {
            "flashcard_set_completed": 5,
            "study_guide_completed": 15,
            "quiz_easy_passed": 10,
            "quiz_hard_passed": 25,
            "evaluation_low": 20,
            "evaluation_high": 50
        }
        mock_service.get_xp_config.return_value = mock_config
        
        # Mock Firestore doc
        mock_db = MagicMock()
        mock_service.db = mock_db
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            **mock_config,
            "updated_at": datetime.now(timezone.utc),
            "updated_by": "admin@example.com"
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        response = client.get("/api/gamification/config/xp")

        assert response.status_code == 200
        data = response.json()
        assert data["flashcard_set_completed"] == 5
        assert data["quiz_hard_passed"] == 25

    @patch('app.routes.gamification.get_gamification_service')
    def test_update_xp_config(self, mock_get_service, client):
        """Test updating XP configuration."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.update_xp_config.return_value = True

        response = client.patch("/api/gamification/config/xp", json={
            "quiz_easy_passed": 15,
            "quiz_hard_passed": 30
        })

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

        # Verify service was called with correct params
        mock_service.update_xp_config.assert_called_once()
        call_args = mock_service.update_xp_config.call_args
        updates = call_args[0][0]
        assert updates["quiz_easy_passed"] == 15
        assert updates["quiz_hard_passed"] == 30

    @patch('app.routes.gamification.get_gamification_service')
    def test_update_xp_config_empty(self, mock_get_service, client):
        """Test updating XP config with no updates."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        response = client.patch("/api/gamification/config/xp", json={})

        assert response.status_code == 400

    @patch('app.routes.gamification.get_gamification_service')
    def test_update_xp_config_service_failure(self, mock_get_service, client):
        """Test handling service failure on update."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.update_xp_config.return_value = False

        response = client.patch("/api/gamification/config/xp", json={
            "quiz_easy_passed": 15
        })

        assert response.status_code == 500


class TestSessionEndpoints:
    """Tests for session management endpoints."""

    @patch('app.routes.gamification.get_gamification_service')
    def test_start_session(self, mock_get_service, client):
        """Test starting a session."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        from app.models.gamification_models import SessionStartResponse
        mock_response = SessionStartResponse(
            session_id="session-123",
            start_time=datetime.now(timezone.utc)
        )
        mock_service.start_session.return_value = mock_response

        response = client.post("/api/gamification/session/start")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "session-123"

    @patch('app.routes.gamification.get_gamification_service')
    def test_session_heartbeat(self, mock_get_service, client):
        """Test sending session heartbeat."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.update_session_heartbeat.return_value = True

        response = client.post("/api/gamification/session/heartbeat", json={
            "session_id": "session-123",
            "active_seconds": 30,
            "current_page": "dashboard"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    @patch('app.routes.gamification.get_gamification_service')
    def test_end_session(self, mock_get_service, client):
        """Test ending a session."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.end_session.return_value = True

        response = client.post("/api/gamification/session/end?session_id=session-123")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestGetActivitiesEndpoint:
    """Tests for GET /api/gamification/activities endpoint."""

    @patch('app.routes.gamification.get_gamification_service')
    def test_get_activities(self, mock_get_service, client):
        """Test getting user activities."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # Mock activities
        mock_activities = [
            UserActivity(
                id="activity-1",
                user_id="test-user",
                user_email="test@example.com",
                activity_type="quiz_completed",
                activity_data={"score": 8, "total_questions": 10},
                xp_awarded=10
            ),
            UserActivity(
                id="activity-2",
                user_id="test-user",
                user_email="test@example.com",
                activity_type="flashcard_set_completed",
                activity_data={"correct_count": 20},
                xp_awarded=10
            )
        ]
        mock_service.get_user_activities.return_value = (mock_activities, None)

        response = client.get("/api/gamification/activities")

        assert response.status_code == 200
        data = response.json()
        assert len(data["activities"]) == 2
        assert data["next_cursor"] is None

    @patch('app.routes.gamification.get_gamification_service')
    def test_get_activities_with_pagination(self, mock_get_service, client):
        """Test getting activities with pagination."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        mock_activities = [UserActivity(
            id=f"activity-{i}",
            user_id="test-user",
            user_email="test@example.com",
            activity_type="quiz_completed",
            activity_data={},
            xp_awarded=10
        ) for i in range(50)]

        mock_service.get_user_activities.return_value = (mock_activities, "cursor-123")

        response = client.get("/api/gamification/activities?limit=50")

        assert response.status_code == 200
        data = response.json()
        assert len(data["activities"]) == 50
        assert data["next_cursor"] == "cursor-123"


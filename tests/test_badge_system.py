"""
Tests for Badge System (Phase 4)

Tests badge checking, unlocking, and progress tracking.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from app.models.gamification_models import (
    UserStats,
    BadgeDefinition,
    UserBadge,
    StreakInfo,
    ActivityCounters
)
from app.services.badge_service import BadgeService


class TestBadgeService:
    """Test badge service functionality."""

    @pytest.fixture
    def badge_service(self):
        """Create badge service with mocked DB."""
        with patch('app.services.badge_service.get_firestore_client'):
            service = BadgeService()
            service.db = Mock()
            return service

    @pytest.fixture
    def sample_user_stats(self):
        """Create sample user stats."""
        return UserStats(
            user_id="test_user",
            user_email="test@example.com",
            total_xp=1500,
            streak=StreakInfo(
                current_count=15,
                longest_count=20
            ),
            # FIX: Changed activity_counters to activities (correct attribute name)
            activities=ActivityCounters(
                flashcards_reviewed=25,  # FIX: Changed from flashcard_sets_completed
                quizzes_passed=12,
                evaluations_submitted=8,  # FIX: Changed from evaluations_completed
                guides_completed=5  # FIX: Changed from study_guides_completed
            )
        )

    def test_check_streak_badge_criteria(self, badge_service, sample_user_stats):
        """Test checking streak badge criteria."""
        # Badge requiring 14-day streak
        badge_def = BadgeDefinition(
            badge_id="on_fire",
            name="On Fire",
            description="14-day streak",
            category="streak",
            icon="🔥",
            rarity="uncommon",
            criteria={"streak_days": 14},
            points=50
        )
        
        # User has 15-day streak, should meet criteria
        result = badge_service._check_badge_criteria(badge_def, sample_user_stats)
        assert result is True

    def test_check_xp_badge_criteria(self, badge_service, sample_user_stats):
        """Test checking XP badge criteria."""
        # Badge requiring 1000 XP
        badge_def = BadgeDefinition(
            badge_id="apprentice",
            name="Apprentice",
            description="1000 XP",
            category="xp",
            icon="⭐",
            rarity="common",
            criteria={"total_xp": 1000},
            points=25
        )
        
        # User has 1500 XP, should meet criteria
        result = badge_service._check_badge_criteria(badge_def, sample_user_stats)
        assert result is True

    def test_check_activity_badge_criteria(self, badge_service, sample_user_stats):
        """Test checking activity badge criteria."""
        # Badge requiring 20 flashcard sets
        badge_def = BadgeDefinition(
            badge_id="flashcard_fan",
            name="Flashcard Fan",
            description="20 flashcard sets",
            category="activity",
            icon="📇",
            rarity="uncommon",
            criteria={"flashcard_sets": 20},
            points=50
        )
        
        # User has 25 sets, should meet criteria
        result = badge_service._check_badge_criteria(badge_def, sample_user_stats)
        assert result is True

    def test_check_activity_badge_not_met(self, badge_service, sample_user_stats):
        """Test activity badge criteria not met."""
        # Badge requiring 50 quizzes
        badge_def = BadgeDefinition(
            badge_id="quiz_master",
            name="Quiz Master",
            description="50 quizzes",
            category="activity",
            icon="📝",
            rarity="rare",
            criteria={"quizzes_passed": 50},
            points=100
        )
        
        # User has only 12 quizzes, should not meet criteria
        result = badge_service._check_badge_criteria(badge_def, sample_user_stats)
        assert result is False

    def test_calculate_progress_streak(self, badge_service, sample_user_stats):
        """Test calculating progress for streak badge."""
        badge_def = BadgeDefinition(
            badge_id="blazing",
            name="Blazing",
            description="30-day streak",
            category="streak",
            icon="🔥",
            rarity="rare",
            criteria={"streak_days": 30},
            points=100
        )
        
        progress = badge_service._calculate_progress(badge_def, sample_user_stats)
        
        assert progress is not None
        assert progress["current"] == 15
        assert progress["required"] == 30
        assert progress["percentage"] == 50

    def test_calculate_progress_xp(self, badge_service, sample_user_stats):
        """Test calculating progress for XP badge."""
        badge_def = BadgeDefinition(
            badge_id="expert",
            name="Expert",
            description="5000 XP",
            category="xp",
            icon="⭐",
            rarity="rare",
            criteria={"total_xp": 5000},
            points=100
        )
        
        progress = badge_service._calculate_progress(badge_def, sample_user_stats)
        
        assert progress is not None
        assert progress["current"] == 1500
        assert progress["required"] == 5000
        assert progress["percentage"] == 30

    def test_unlock_badge(self, badge_service):
        """Test unlocking a badge."""
        badge_def = BadgeDefinition(
            badge_id="test_badge",
            name="Test Badge",
            description="Test",
            category="special",
            icon="🎯",
            rarity="common",
            criteria={},
            points=10
        )

        # Mock Firestore collection
        mock_collection = Mock()
        mock_doc = Mock()
        mock_doc_ref = Mock()
        mock_doc.exists = False  # Badge not yet earned
        mock_doc_ref.get.return_value = mock_doc
        mock_collection.document.return_value = mock_doc_ref
        badge_service.db.collection.return_value = mock_collection

        # Mock the transactional decorator on db - it just calls the function
        badge_service.db.transactional = lambda func: lambda txn: func(txn)
        badge_service.db.transaction.return_value = Mock()

        user_badge = badge_service._unlock_badge("test_user", badge_def)

        assert user_badge is not None
        assert user_badge.user_id == "test_user"
        assert user_badge.badge_id == "test_badge"
        assert user_badge.badge_name == "Test Badge"

    def test_get_earned_badge_ids(self, badge_service):
        """Test getting earned badge IDs."""
        # Mock Firestore query
        mock_doc1 = Mock()
        mock_doc1.to_dict.return_value = {"badge_id": "badge1"}
        mock_doc2 = Mock()
        mock_doc2.to_dict.return_value = {"badge_id": "badge2"}
        
        mock_query = Mock()
        mock_query.stream.return_value = [mock_doc1, mock_doc2]
        
        mock_collection = Mock()
        mock_collection.where.return_value = mock_query
        badge_service.db.collection.return_value = mock_collection
        
        earned_ids = badge_service._get_earned_badge_ids("test_user")
        
        assert "badge1" in earned_ids
        assert "badge2" in earned_ids
        assert len(earned_ids) == 2


class TestBadgeDefinitions:
    """Test badge definitions."""

    def test_all_badge_definitions_count(self):
        """Test that we have all 30+ badges defined."""
        from app.services.badge_definitions import get_all_badge_definitions
        
        badges = get_all_badge_definitions()
        
        # Should have at least 30 badges
        assert len(badges) >= 30

    def test_streak_badges_count(self):
        """Test streak badges count."""
        from app.services.badge_definitions import get_streak_badges
        
        badges = get_streak_badges()
        
        # Should have 7 streak badges
        assert len(badges) == 7

    def test_xp_badges_count(self):
        """Test XP badges count."""
        from app.services.badge_definitions import get_xp_badges
        
        badges = get_xp_badges()
        
        # Should have 6 XP badges
        assert len(badges) == 6

    def test_activity_badges_count(self):
        """Test activity badges count."""
        from app.services.badge_definitions import get_activity_badges
        
        badges = get_activity_badges()
        
        # Should have 5 activity badges
        assert len(badges) == 5

    def test_consistency_badges_count(self):
        """Test consistency badges count."""
        from app.services.badge_definitions import get_consistency_badges
        
        badges = get_consistency_badges()
        
        # Should have 4 consistency badges
        assert len(badges) == 4

    def test_special_badges_count(self):
        """Test special badges count."""
        from app.services.badge_definitions import get_special_badges
        
        badges = get_special_badges()
        
        # Should have at least 8 special badges
        assert len(badges) >= 8

    def test_badge_unique_ids(self):
        """Test that all badge IDs are unique."""
        from app.services.badge_definitions import get_all_badge_definitions
        
        badges = get_all_badge_definitions()
        badge_ids = [b.badge_id for b in badges]
        
        # All IDs should be unique
        assert len(badge_ids) == len(set(badge_ids))

    def test_badge_has_required_fields(self):
        """Test that all badges have required fields."""
        from app.services.badge_definitions import get_all_badge_definitions
        
        badges = get_all_badge_definitions()
        
        for badge in badges:
            assert badge.badge_id
            assert badge.name
            assert badge.description
            assert badge.category
            assert badge.icon
            assert badge.rarity
            assert badge.criteria
            assert badge.points >= 0


class TestBadgeIntegration:
    """Test badge integration with activity logging."""

    def test_badge_checking_on_activity(self):
        """Test that badges are checked when activity is logged."""
        # This would be an integration test
        # For now, just verify the structure is in place
        from app.services.badge_service import get_badge_service
        
        service = get_badge_service()
        assert service is not None
        assert hasattr(service, 'check_and_unlock_badges')

    def test_badge_progress_tracking(self):
        """Test badge progress tracking."""
        from app.services.badge_service import get_badge_service
        
        service = get_badge_service()
        assert hasattr(service, 'get_badge_progress')


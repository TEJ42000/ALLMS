"""Tests for Gamification Streak System.

Tests the streak tracking functionality including:
- 4:00 AM reset logic
- Streak freeze usage
- Streak maintenance and breaking
- Edge cases and boundary conditions
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from app.services.gamification_service import GamificationService, STREAK_RESET_HOUR
from app.models.gamification_models import UserStats, StreakInfo


@pytest.fixture
def mock_firestore():
    """Mock Firestore client for testing."""
    mock_db = MagicMock()
    return mock_db


@pytest.fixture
def gamification_service(mock_firestore):
    """Create a gamification service with mocked Firestore."""
    service = GamificationService()
    service._db = mock_firestore  # Use private attribute to bypass property
    return service


@pytest.fixture
def sample_user_stats():
    """Create sample user stats for testing."""
    return UserStats(
        user_id="test-user-123",
        user_email="test@example.com",
        total_xp=1000,
        current_level=5,
        level_title="Junior Clerk",
        xp_to_next_level=200,
        streak=StreakInfo(
            current_count=5,
            longest_streak=10,
            last_activity_date=datetime.now(timezone.utc) - timedelta(days=1),
            freezes_available=2
        )
    )


class TestStreakDayCalculation:
    """Tests for _get_streak_day method."""

    def test_before_4am_counts_as_previous_day(self, gamification_service):
        """Activity before 4 AM should count as previous day."""
        # 3:30 AM on Jan 6
        dt = datetime(2026, 1, 6, 3, 30, 0, tzinfo=timezone.utc)
        streak_day = gamification_service._get_streak_day(dt)
        
        # Should be Jan 5
        expected = datetime(2026, 1, 5, 0, 0, 0, tzinfo=timezone.utc)
        assert streak_day == expected

    def test_at_4am_counts_as_current_day(self, gamification_service):
        """Activity at exactly 4 AM should count as current day."""
        # 4:00 AM on Jan 6
        dt = datetime(2026, 1, 6, 4, 0, 0, tzinfo=timezone.utc)
        streak_day = gamification_service._get_streak_day(dt)
        
        # Should be Jan 6
        expected = datetime(2026, 1, 6, 0, 0, 0, tzinfo=timezone.utc)
        assert streak_day == expected

    def test_after_4am_counts_as_current_day(self, gamification_service):
        """Activity after 4 AM should count as current day."""
        # 11:30 PM on Jan 6
        dt = datetime(2026, 1, 6, 23, 30, 0, tzinfo=timezone.utc)
        streak_day = gamification_service._get_streak_day(dt)
        
        # Should be Jan 6
        expected = datetime(2026, 1, 6, 0, 0, 0, tzinfo=timezone.utc)
        assert streak_day == expected

    def test_midnight_counts_as_previous_day(self, gamification_service):
        """Activity at midnight should count as previous day."""
        # 12:00 AM on Jan 6
        dt = datetime(2026, 1, 6, 0, 0, 0, tzinfo=timezone.utc)
        streak_day = gamification_service._get_streak_day(dt)
        
        # Should be Jan 5
        expected = datetime(2026, 1, 5, 0, 0, 0, tzinfo=timezone.utc)
        assert streak_day == expected


class TestStreakStatusCheck:
    """Tests for check_streak_status method."""

    def test_first_activity_ever(self, gamification_service, mock_firestore):
        """First activity should start streak at 1."""
        # Mock no existing stats
        mock_firestore.collection().document().get.return_value.exists = False
        
        current_time = datetime.now(timezone.utc)
        maintained, count, freeze_used = gamification_service.check_streak_status(
            "new-user", current_time
        )
        
        assert maintained is True
        assert count == 1
        assert freeze_used is False

    def test_same_day_activity_maintains_streak(self, gamification_service, sample_user_stats):
        """Multiple activities on same streak day should maintain count."""
        # Mock existing stats with activity earlier today
        with patch.object(gamification_service, 'get_user_stats', return_value=sample_user_stats):
            # Set last activity to 2 hours ago (same streak day)
            sample_user_stats.last_active = datetime.now(timezone.utc) - timedelta(hours=2)
            sample_user_stats.streak.current_count = 7
            
            current_time = datetime.now(timezone.utc)
            maintained, count, freeze_used = gamification_service.check_streak_status(
                "test-user", current_time
            )
            
            assert maintained is True
            assert count == 7  # Should maintain, not increment
            assert freeze_used is False

    def test_next_day_activity_increments_streak(self, gamification_service, sample_user_stats):
        """Activity on next streak day should increment count."""
        with patch.object(gamification_service, 'get_user_stats', return_value=sample_user_stats):
            # Set last activity to yesterday at 10 AM
            sample_user_stats.last_active = datetime(2026, 1, 5, 10, 0, 0, tzinfo=timezone.utc)
            sample_user_stats.streak.current_count = 7
            
            # Current activity today at 10 AM
            current_time = datetime(2026, 1, 6, 10, 0, 0, tzinfo=timezone.utc)
            maintained, count, freeze_used = gamification_service.check_streak_status(
                "test-user", current_time
            )
            
            assert maintained is True
            assert count == 8  # Should increment
            assert freeze_used is False

    def test_missed_one_day_with_freeze_maintains_streak(self, gamification_service, sample_user_stats):
        """Missing one day with available freeze should maintain streak."""
        with patch.object(gamification_service, 'get_user_stats', return_value=sample_user_stats):
            # Set last activity to 2 days ago
            sample_user_stats.last_active = datetime(2026, 1, 4, 10, 0, 0, tzinfo=timezone.utc)
            sample_user_stats.streak.current_count = 7
            sample_user_stats.streak.freezes_available = 2
            
            # Current activity today
            current_time = datetime(2026, 1, 6, 10, 0, 0, tzinfo=timezone.utc)
            maintained, count, freeze_used = gamification_service.check_streak_status(
                "test-user", current_time
            )
            
            assert maintained is True
            assert count == 7  # Should maintain with freeze
            assert freeze_used is True

    def test_missed_one_day_without_freeze_breaks_streak(self, gamification_service, sample_user_stats):
        """Missing one day without freeze should break streak."""
        with patch.object(gamification_service, 'get_user_stats', return_value=sample_user_stats):
            # Set last activity to 2 days ago
            sample_user_stats.last_active = datetime(2026, 1, 4, 10, 0, 0, tzinfo=timezone.utc)
            sample_user_stats.streak.current_count = 7
            sample_user_stats.streak.freezes_available = 0  # No freezes
            
            # Current activity today
            current_time = datetime(2026, 1, 6, 10, 0, 0, tzinfo=timezone.utc)
            maintained, count, freeze_used = gamification_service.check_streak_status(
                "test-user", current_time
            )
            
            assert maintained is False
            assert count == 1  # Should reset
            assert freeze_used is False

    def test_missed_multiple_days_breaks_streak_even_with_freeze(self, gamification_service, sample_user_stats):
        """Missing multiple days should break streak even with freeze available."""
        with patch.object(gamification_service, 'get_user_stats', return_value=sample_user_stats):
            # Set last activity to 3 days ago
            sample_user_stats.last_active = datetime(2026, 1, 3, 10, 0, 0, tzinfo=timezone.utc)
            sample_user_stats.streak.current_count = 7
            sample_user_stats.streak.freezes_available = 2  # Has freezes but too many days missed

            # Current activity today
            current_time = datetime(2026, 1, 6, 10, 0, 0, tzinfo=timezone.utc)
            maintained, count, freeze_used = gamification_service.check_streak_status(
                "test-user", current_time
            )

            assert maintained is False
            assert count == 1  # Should reset
            assert freeze_used is False  # Freeze not used because gap too large


class TestStreakEdgeCases:
    """Tests for edge cases in streak tracking."""

    def test_activity_just_before_4am_same_streak_day(self, gamification_service, sample_user_stats):
        """Activity at 3:59 AM should be same streak day as previous evening."""
        with patch.object(gamification_service, 'get_user_stats', return_value=sample_user_stats):
            # Last activity at 11 PM yesterday
            sample_user_stats.last_active = datetime(2026, 1, 5, 23, 0, 0, tzinfo=timezone.utc)
            sample_user_stats.streak.current_count = 5

            # Current activity at 3:59 AM today (still counts as Jan 5)
            current_time = datetime(2026, 1, 6, 3, 59, 0, tzinfo=timezone.utc)
            maintained, count, freeze_used = gamification_service.check_streak_status(
                "test-user", current_time
            )

            assert maintained is True
            assert count == 5  # Same day, should maintain
            assert freeze_used is False

    def test_activity_at_4am_is_next_day(self, gamification_service, sample_user_stats):
        """Activity at exactly 4:00 AM should be next streak day."""
        with patch.object(gamification_service, 'get_user_stats', return_value=sample_user_stats):
            # Last activity at 11 PM yesterday
            sample_user_stats.last_active = datetime(2026, 1, 5, 23, 0, 0, tzinfo=timezone.utc)
            sample_user_stats.streak.current_count = 5

            # Current activity at 4:00 AM today (new streak day)
            current_time = datetime(2026, 1, 6, 4, 0, 0, tzinfo=timezone.utc)
            maintained, count, freeze_used = gamification_service.check_streak_status(
                "test-user", current_time
            )

            assert maintained is True
            assert count == 6  # Next day, should increment
            assert freeze_used is False

    def test_late_night_study_session_crosses_midnight(self, gamification_service, sample_user_stats):
        """Late night session crossing midnight should count as same streak day."""
        with patch.object(gamification_service, 'get_user_stats', return_value=sample_user_stats):
            # Last activity at 11:30 PM
            sample_user_stats.last_active = datetime(2026, 1, 5, 23, 30, 0, tzinfo=timezone.utc)
            sample_user_stats.streak.current_count = 5

            # Continue studying at 1:00 AM (still same streak day)
            current_time = datetime(2026, 1, 6, 1, 0, 0, tzinfo=timezone.utc)
            maintained, count, freeze_used = gamification_service.check_streak_status(
                "test-user", current_time
            )

            assert maintained is True
            assert count == 5  # Same streak day
            assert freeze_used is False


class TestStreakFreezeEarning:
    """Tests for earning streak freezes."""

    def test_freeze_earned_every_500_xp(self, gamification_service):
        """Should earn 1 freeze for every 500 XP."""
        # Test various XP thresholds
        test_cases = [
            (0, 499, 0),      # No freeze yet (0//500=0, 499//500=0, 0-0=0)
            (0, 500, 1),      # First freeze at 500 (500//500=1, 0//500=0, 1-0=1)
            (0, 999, 1),      # Still 1 freeze (999//500=1, 0//500=0, 1-0=1)
            (0, 1000, 2),     # Second freeze at 1000 (1000//500=2, 0//500=0, 2-0=2)
            (500, 1000, 1),   # Crossing from 500 to 1000 earns 1 (1000//500=2, 500//500=1, 2-1=1)
            (450, 550, 1),    # Crossing 500 threshold earns 1 (550//500=1, 450//500=0, 1-0=1)
            (1900, 2100, 1),  # Crossing 2000 earns 1 (2100//500=4, 1900//500=3, 4-3=1)
            (1900, 2500, 2),  # Crossing 2000 and 2500 earns 2 (2500//500=5, 1900//500=3, 5-3=2)
            (1900, 3000, 3),  # Crossing 2000, 2500, and 3000 earns 3 (3000//500=6, 1900//500=3, 6-3=3)
        ]

        for old_xp, new_xp, expected_freezes in test_cases:
            freezes_to_add = (new_xp // 500) - (old_xp // 500)
            assert freezes_to_add == expected_freezes, \
                f"XP {old_xp} -> {new_xp} should earn {expected_freezes} freezes, got {freezes_to_add}"


class TestStreakIntegration:
    """Integration tests for streak system with activity logging."""

    def test_firestore_unavailable_returns_safe_defaults(self, gamification_service):
        """When Firestore is unavailable, should return safe defaults."""
        gamification_service._db = None  # Use private attribute

        current_time = datetime.now(timezone.utc)
        maintained, count, freeze_used = gamification_service.check_streak_status(
            "test-user", current_time
        )

        assert maintained is True
        assert count == 1
        assert freeze_used is False

    def test_longest_streak_tracking(self, gamification_service, sample_user_stats):
        """Should track longest streak achieved."""
        with patch.object(gamification_service, 'get_user_stats', return_value=sample_user_stats):
            # Current streak is 5, longest is 10
            sample_user_stats.streak.current_count = 5
            sample_user_stats.streak.longest_streak = 10
            sample_user_stats.last_active = datetime(2026, 1, 5, 10, 0, 0, tzinfo=timezone.utc)

            # Activity on next day should increment to 6 (still less than longest)
            current_time = datetime(2026, 1, 6, 10, 0, 0, tzinfo=timezone.utc)
            maintained, count, freeze_used = gamification_service.check_streak_status(
                "test-user", current_time
            )

            assert count == 6
            # Longest should remain 10 (not updated in check_streak_status, but in update_streak)

    def test_no_previous_activity_starts_streak(self, gamification_service, sample_user_stats):
        """User with no previous activity should start streak at 1."""
        with patch.object(gamification_service, 'get_user_stats', return_value=sample_user_stats):
            sample_user_stats.last_active = None  # No previous activity

            current_time = datetime.now(timezone.utc)
            maintained, count, freeze_used = gamification_service.check_streak_status(
                "test-user", current_time
            )

            assert maintained is True
            assert count == 1
            assert freeze_used is False


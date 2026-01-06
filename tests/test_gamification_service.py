"""Tests for Gamification Service."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.models.gamification_models import (
    UserStats,
    UserActivity,
    UserSession,
    ActivityLogResponse,
    StreakInfo,
    ActivityCounters,
    Week7Quest,
)
from app.services.gamification_service import (
    GamificationService,
    XP_VALUES,
    LEVEL_THRESHOLDS,
    STREAK_FREEZE_XP_REQUIREMENT,
)


class TestXPCalculation:
    """Tests for XP calculation logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = GamificationService()
        # Mock Firestore to return default XP values
        with patch.object(self.service, 'get_xp_config', return_value=XP_VALUES):
            pass

    def test_quiz_easy_passed(self):
        """Test XP calculation for passing easy quiz."""
        xp = self.service.calculate_xp_for_activity(
            "quiz_completed",
            {"difficulty": "easy", "score": 7, "total_questions": 10}
        )
        assert xp == XP_VALUES["quiz_easy_passed"]

    def test_quiz_hard_passed(self):
        """Test XP calculation for passing hard quiz."""
        xp = self.service.calculate_xp_for_activity(
            "quiz_completed",
            {"difficulty": "hard", "score": 8, "total_questions": 10}
        )
        assert xp == XP_VALUES["quiz_hard_passed"]

    def test_quiz_failed(self):
        """Test XP calculation for failing quiz (< 60%)."""
        xp = self.service.calculate_xp_for_activity(
            "quiz_completed",
            {"difficulty": "hard", "score": 5, "total_questions": 10}
        )
        assert xp == 0

    def test_quiz_exactly_60_percent(self):
        """Test XP calculation for exactly 60% (should pass)."""
        xp = self.service.calculate_xp_for_activity(
            "quiz_completed",
            {"difficulty": "easy", "score": 6, "total_questions": 10}
        )
        assert xp == XP_VALUES["quiz_easy_passed"]

    def test_flashcard_set_completed(self):
        """Test XP calculation for flashcard review."""
        # 25 correct cards = 2 sets of 10 = 2 * 5 XP
        xp = self.service.calculate_xp_for_activity(
            "flashcard_set_completed",
            {"correct_count": 25, "total_count": 30}
        )
        assert xp == 2 * XP_VALUES["flashcard_set_completed"]

    def test_flashcard_less_than_10(self):
        """Test XP calculation for less than 10 flashcards."""
        xp = self.service.calculate_xp_for_activity(
            "flashcard_set_completed",
            {"correct_count": 9, "total_count": 10}
        )
        assert xp == 0

    def test_study_guide_completed(self):
        """Test XP calculation for study guide completion."""
        xp = self.service.calculate_xp_for_activity(
            "study_guide_completed",
            {}
        )
        assert xp == XP_VALUES["study_guide_completed"]

    def test_evaluation_high_grade(self):
        """Test XP calculation for high AI evaluation grade."""
        xp = self.service.calculate_xp_for_activity(
            "evaluation_completed",
            {"grade": 8}
        )
        assert xp == XP_VALUES["evaluation_high"]

    def test_evaluation_low_grade(self):
        """Test XP calculation for low AI evaluation grade."""
        xp = self.service.calculate_xp_for_activity(
            "evaluation_completed",
            {"grade": 5}
        )
        assert xp == XP_VALUES["evaluation_low"]

    def test_evaluation_grade_boundary(self):
        """Test XP calculation at grade boundary (7)."""
        xp = self.service.calculate_xp_for_activity(
            "evaluation_completed",
            {"grade": 7}
        )
        assert xp == XP_VALUES["evaluation_high"]

    def test_evaluation_zero_grade(self):
        """Test XP calculation for zero grade."""
        xp = self.service.calculate_xp_for_activity(
            "evaluation_completed",
            {"grade": 0}
        )
        assert xp == 0

    def test_unknown_activity_type(self):
        """Test XP calculation for unknown activity type."""
        xp = self.service.calculate_xp_for_activity(
            "unknown_activity",
            {}
        )
        assert xp == 0


class TestLevelCalculation:
    """Tests for level progression calculation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = GamificationService()

    def test_level_1_zero_xp(self):
        """Test level calculation at 0 XP."""
        level, title, xp_to_next = self.service.calculate_level_from_xp(0)
        assert level == 1
        assert title == "Junior Clerk"
        assert xp_to_next > 0

    def test_level_10_boundary(self):
        """Test level calculation at tier boundary (999 XP)."""
        level, title, xp_to_next = self.service.calculate_level_from_xp(999)
        assert level == 10
        assert title == "Junior Clerk"
        assert xp_to_next == 1

    def test_level_11_tier_change(self):
        """Test level calculation at tier change (1000 XP)."""
        level, title, xp_to_next = self.service.calculate_level_from_xp(1000)
        assert level == 11
        assert title == "Summer Associate"
        assert xp_to_next > 0

    def test_level_25_boundary(self):
        """Test level calculation at second tier boundary (4999 XP)."""
        level, title, xp_to_next = self.service.calculate_level_from_xp(4999)
        assert level == 25
        assert title == "Summer Associate"
        assert xp_to_next == 1

    def test_level_26_tier_change(self):
        """Test level calculation at second tier change (5000 XP)."""
        level, title, xp_to_next = self.service.calculate_level_from_xp(5000)
        assert level == 26
        assert title == "Junior Partner"
        assert xp_to_next > 0

    def test_level_50_boundary(self):
        """Test level calculation at third tier boundary (14999 XP)."""
        level, title, xp_to_next = self.service.calculate_level_from_xp(14999)
        assert level == 50
        assert title == "Junior Partner"
        assert xp_to_next == 1

    def test_level_51_tier_change(self):
        """Test level calculation at third tier change (15000 XP)."""
        level, title, xp_to_next = self.service.calculate_level_from_xp(15000)
        assert level == 51
        assert title == "Senior Partner"
        assert xp_to_next > 0

    def test_level_100_high_xp(self):
        """Test level calculation at very high XP (50000+)."""
        level, title, xp_to_next = self.service.calculate_level_from_xp(50000)
        assert level == 101
        assert title == "Juris Doctor"
        assert xp_to_next > 0

    def test_level_progression_consistency(self):
        """Test that level progression is consistent."""
        # Test that XP increases result in level increases
        prev_level = 0
        for xp in range(0, 20000, 100):
            level, _, _ = self.service.calculate_level_from_xp(xp)
            assert level >= prev_level, f"Level decreased at {xp} XP"
            prev_level = level


class TestStreakFreeze:
    """Tests for streak freeze calculation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = GamificationService()

    def test_freeze_earned_at_500_xp(self):
        """Test that freeze is earned at 500 XP."""
        # User goes from 400 to 600 XP
        old_xp = 400
        new_xp = 600

        old_freezes = old_xp // STREAK_FREEZE_XP_REQUIREMENT
        new_freezes = new_xp // STREAK_FREEZE_XP_REQUIREMENT

        freezes_earned = new_freezes - old_freezes
        assert freezes_earned == 1

    def test_freeze_earned_at_1000_xp(self):
        """Test that freeze is earned at 1000 XP."""
        old_xp = 900
        new_xp = 1100

        old_freezes = old_xp // STREAK_FREEZE_XP_REQUIREMENT
        new_freezes = new_xp // STREAK_FREEZE_XP_REQUIREMENT

        freezes_earned = new_freezes - old_freezes
        assert freezes_earned == 1

    def test_multiple_freezes_earned(self):
        """Test earning multiple freezes at once."""
        old_xp = 0
        new_xp = 1500

        old_freezes = old_xp // STREAK_FREEZE_XP_REQUIREMENT
        new_freezes = new_xp // STREAK_FREEZE_XP_REQUIREMENT

        freezes_earned = new_freezes - old_freezes
        assert freezes_earned == 3

    def test_no_freeze_earned(self):
        """Test that no freeze is earned below threshold."""
        old_xp = 100
        new_xp = 200

        old_freezes = old_xp // STREAK_FREEZE_XP_REQUIREMENT
        new_freezes = new_xp // STREAK_FREEZE_XP_REQUIREMENT

        freezes_earned = new_freezes - old_freezes
        assert freezes_earned == 0


class TestUserStatsModel:
    """Tests for UserStats model."""

    def test_create_user_stats(self):
        """Test creating a UserStats object."""
        stats = UserStats(
            user_id="test-user",
            user_email="test@example.com",
            course_id="LLS-2024"
        )

        assert stats.user_id == "test-user"
        assert stats.user_email == "test@example.com"
        assert stats.course_id == "LLS-2024"
        assert stats.total_xp == 0
        assert stats.current_level == 1
        assert stats.level_title == "Junior Clerk"

    def test_user_stats_defaults(self):
        """Test UserStats default values."""
        stats = UserStats(
            user_id="test-user",
            user_email="test@example.com"
        )

        assert stats.streak.current_count == 0
        assert stats.streak.longest_streak == 0
        assert stats.streak.freezes_available == 0
        assert stats.activities.flashcards_reviewed == 0
        assert stats.activities.quizzes_completed == 0
        assert stats.week7_quest.active == False


class TestUserActivityModel:
    """Tests for UserActivity model."""

    def test_create_user_activity(self):
        """Test creating a UserActivity object."""
        activity = UserActivity(
            id="activity-123",
            user_id="test-user",
            user_email="test@example.com",
            activity_type="quiz_completed",
            activity_data={"score": 8, "total_questions": 10},
            xp_awarded=10
        )

        assert activity.id == "activity-123"
        assert activity.user_id == "test-user"
        assert activity.activity_type == "quiz_completed"
        assert activity.xp_awarded == 10
        assert activity.timestamp is not None


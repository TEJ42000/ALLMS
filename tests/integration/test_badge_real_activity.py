"""
Integration tests for badge unlocking with real activity data.

Tests the complete flow from activity logging to badge unlocking.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock

from app.services.badge_service import BadgeService
from app.models.gamification_models import (
    UserStats,
    ActivityCounters,
    StreakInfo,
    BadgeDefinition,
    UserBadge
)


class TestBadgeUnlockingWithRealActivity:
    """Test badge unlocking with realistic activity data."""

    @pytest.fixture
    def badge_service_with_db(self):
        """Create badge service with mocked Firestore."""
        from unittest.mock import patch
        # Patch before creating the service, then set up the mock db
        patcher = patch('app.services.badge_service.get_firestore_client')
        mock_client = patcher.start()
        mock_db = MagicMock()
        mock_client.return_value = mock_db
        service = BadgeService()

        # Mock transactional decorator for _unlock_badge - it just executes the function
        service.db.transactional = lambda func: lambda txn: func(txn)
        service.db.transaction.return_value = MagicMock()

        # Mock the document get to return that badge doesn't exist yet
        mock_snapshot = MagicMock()
        mock_snapshot.exists = False  # Badge not yet earned
        service.db.collection.return_value.document.return_value.get.return_value = mock_snapshot

        yield service
        patcher.stop()

    @pytest.fixture
    def user_stats_new_user(self):
        """Create stats for a brand new user."""
        return UserStats(
            user_id="test_user_new",
            user_email="test_new@example.com",
            total_xp=0,
            level=1,
            level_title="Beginner",
            activities=ActivityCounters(
                flashcards_reviewed=0,
                quizzes_passed=0,
                evaluations_submitted=0,
                guides_completed=0
            ),
            streak=StreakInfo(
                current_count=0,
                longest_streak=0
                # last_activity_date has a default, don't set to None
            ),
            created_at=datetime.now(timezone.utc)
        )

    @pytest.fixture
    def user_stats_active_user(self):
        """Create stats for an active user with some progress."""
        return UserStats(
            user_id="test_user_active",
            user_email="test_active@example.com",
            total_xp=750,
            level=3,
            level_title="Learner",
            activities=ActivityCounters(
                flashcards_reviewed=15,
                quizzes_passed=8,
                evaluations_submitted=5,
                guides_completed=3
            ),
            streak=StreakInfo(
                current_count=5,
                longest_streak=10,
                last_activity_date=datetime.now(timezone.utc)
            ),
            created_at=datetime.now(timezone.utc) - timedelta(days=30)
        )

    def test_first_activity_unlocks_ignition_badge(self, badge_service_with_db, user_stats_new_user):
        """Test that first activity unlocks the Ignition badge (1-day streak)."""
        # Setup: User completes first activity
        user_stats_new_user.streak.current_count = 1
        user_stats_new_user.streak.last_activity_date = datetime.now(timezone.utc).date()
        user_stats_new_user.total_xp = 50

        # Mock badge definitions
        ignition_badge = BadgeDefinition(
            badge_id="ignition",
            name="Ignition",
            description="Start your first streak",
            category="streak",
            icon="🔥",
            rarity="common",
            criteria={"streak_days": 1},
            points=10,
            active=True
        )

        # Mock Firestore responses
        badge_service_with_db.db.collection.return_value.stream.return_value = [
            Mock(to_dict=lambda: ignition_badge.model_dump(mode='json'))
        ]

        # Mock user badges collection (no badges yet)
        badge_service_with_db.db.collection.return_value.where.return_value.stream.return_value = []

        # Check if badge should be unlocked
        badges_to_unlock = badge_service_with_db.check_and_unlock_badges(
            user_stats_new_user.user_id,
            user_stats_new_user
        )

        # Verify Ignition badge is unlocked
        assert len(badges_to_unlock) > 0
        assert any(b.badge_id == "ignition" for b in badges_to_unlock)

    def test_flashcard_activity_unlocks_badge(self, badge_service_with_db, user_stats_active_user):
        """Test that completing flashcards unlocks Flashcard Fanatic badge."""
        # Setup: User completes 100 flashcard sets
        user_stats_active_user.activities.flashcards_reviewed = 100

        # Mock badge definition
        flashcard_badge = BadgeDefinition(
            badge_id="flashcard_fanatic",
            name="Flashcard Fanatic",
            description="Review 100 flashcard sets",
            category="activity",
            icon="📇",
            rarity="rare",
            criteria={"flashcard_sets": 100},
            points=100,
            active=True
        )

        # Mock Firestore responses
        badge_service_with_db.db.collection.return_value.stream.return_value = [
            Mock(to_dict=lambda: flashcard_badge.model_dump(mode='json'))
        ]

        # Mock user badges collection (no badges yet)
        badge_service_with_db.db.collection.return_value.where.return_value.stream.return_value = []

        # Check if badge should be unlocked
        badges_to_unlock = badge_service_with_db.check_and_unlock_badges(
            user_stats_active_user.user_id,
            user_stats_active_user
        )

        # Verify badge is unlocked
        assert len(badges_to_unlock) > 0
        assert any(b.badge_id == "flashcard_fanatic" for b in badges_to_unlock)

    def test_xp_milestone_unlocks_badge(self, badge_service_with_db, user_stats_active_user):
        """Test that reaching XP milestone unlocks badge."""
        # Setup: User reaches 1000 XP
        user_stats_active_user.total_xp = 1000

        # Mock badge definition
        xp_badge = BadgeDefinition(
            badge_id="apprentice",
            name="Apprentice",
            description="Reach 1,000 XP",
            category="xp",
            icon="⭐",
            rarity="uncommon",
            criteria={"total_xp": 1000},
            points=25,
            active=True
        )

        # Mock Firestore responses
        badge_service_with_db.db.collection.return_value.stream.return_value = [
            Mock(to_dict=lambda: xp_badge.model_dump(mode='json'))
        ]

        # Mock user badges collection (no badges yet)
        badge_service_with_db.db.collection.return_value.where.return_value.stream.return_value = []

        # Check if badge should be unlocked
        badges_to_unlock = badge_service_with_db.check_and_unlock_badges(
            user_stats_active_user.user_id,
            user_stats_active_user
        )

        # Verify badge is unlocked
        assert len(badges_to_unlock) > 0
        assert any(b.badge_id == "apprentice" for b in badges_to_unlock)

    def test_multiple_criteria_badge_requires_all(self, badge_service_with_db, user_stats_active_user):
        """Test that multi-criteria badges require ALL criteria to be met."""
        # Setup: User has some progress but not all criteria met
        user_stats_active_user.activities.flashcards_reviewed = 10
        user_stats_active_user.activities.quizzes_passed = 10
        user_stats_active_user.activities.evaluations_submitted = 5  # Not enough!
        user_stats_active_user.activities.guides_completed = 10

        # Mock badge definition
        well_rounded_badge = BadgeDefinition(
            badge_id="well_rounded",
            name="Well-Rounded",
            description="Complete 10 of each activity type",
            category="activity",
            icon="🎯",
            rarity="epic",
            criteria={
                "flashcard_sets": 10,
                "quizzes_passed": 10,
                "evaluations": 10,  # User only has 5
                "study_guides": 10
            },
            points=200,
            active=True
        )

        # Mock Firestore responses
        badge_service_with_db.db.collection.return_value.stream.return_value = [
            Mock(to_dict=lambda: well_rounded_badge.model_dump(mode='json'))
        ]

        # Mock user badges collection (no badges yet)
        badge_service_with_db.db.collection.return_value.where.return_value.stream.return_value = []

        # Check if badge should be unlocked
        badges_to_unlock = badge_service_with_db.check_and_unlock_badges(
            user_stats_active_user.user_id,
            user_stats_active_user
        )

        # Verify badge is NOT unlocked (missing evaluations)
        assert not any(b.badge_id == "well_rounded" for b in badges_to_unlock)

        # Now complete the missing criteria
        user_stats_active_user.activities.evaluations_submitted = 10

        # Check again
        badges_to_unlock = badge_service_with_db.check_and_unlock_badges(
            user_stats_active_user.user_id,
            user_stats_active_user
        )

        # Verify badge IS now unlocked
        assert any(b.badge_id == "well_rounded" for b in badges_to_unlock)

    def test_already_earned_badge_not_unlocked_again(self, badge_service_with_db, user_stats_active_user):
        """Test that already earned badges are not unlocked again."""
        # Setup: User has criteria for badge
        user_stats_active_user.total_xp = 500

        # Mock badge definition
        novice_badge = BadgeDefinition(
            badge_id="novice",
            name="Novice",
            description="Reach 500 XP",
            category="xp",
            icon="🌟",
            rarity="common",
            criteria={"total_xp": 500},
            points=10,
            active=True
        )

        # Mock Firestore responses
        badge_service_with_db.db.collection.return_value.stream.return_value = [
            Mock(to_dict=lambda: novice_badge.model_dump(mode='json'))
        ]

        # Mock user badges collection (badge already earned)
        existing_badge = UserBadge(
            user_id=user_stats_active_user.user_id,
            badge_id="novice",
            badge_name="Novice",
            badge_description="Earn 500 XP",
            badge_icon="🌟",
            earned_at=datetime.now(timezone.utc) - timedelta(days=10)
        )
        badge_service_with_db.db.collection.return_value.where.return_value.stream.return_value = [
            Mock(to_dict=lambda: existing_badge.model_dump(mode='json'))
        ]

        # Check if badge should be unlocked
        badges_to_unlock = badge_service_with_db.check_and_unlock_badges(
            user_stats_active_user.user_id,
            user_stats_active_user
        )

        # Verify badge is NOT unlocked again
        assert not any(b.badge_id == "novice" for b in badges_to_unlock)

    def test_zero_division_protection_in_progress(self, badge_service_with_db, user_stats_new_user):
        """Test that zero-division is prevented in progress calculation."""
        # Mock badge with zero criteria (invalid)
        invalid_badge = BadgeDefinition(
            badge_id="invalid_badge",
            name="Invalid Badge",
            description="Badge with zero criteria",
            category="xp",
            icon="❌",
            rarity="common",
            criteria={"total_xp": 0},  # Invalid!
            points=10,
            active=True
        )

        # Calculate progress should handle this gracefully
        progress = badge_service_with_db._calculate_progress(invalid_badge, user_stats_new_user)

        # Should return None for invalid criteria
        assert progress is None


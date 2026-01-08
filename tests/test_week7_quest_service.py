"""
Unit tests for Week 7 Quest Service.

Tests quest activation, exam readiness calculation, double XP tracking,
and boss battle completion.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch

from app.services.week7_quest_service import Week7QuestService
from app.models.gamification_models import (
    UserStats,
    ActivityCounters,
    StreakInfo,
    Week7Quest
)


class TestWeek7QuestService:
    """Test Week 7 Quest Service functionality."""

    @pytest.fixture
    def quest_service(self):
        """Create quest service with mocked Firestore."""
        service = Week7QuestService()
        service.db = MagicMock()
        return service

    @pytest.fixture
    def base_stats(self):
        """Create base user stats for testing."""
        return UserStats(
            user_id="test_user",
            user_email="test@example.com",
            course_id="test_course",
            total_xp=1000,
            level=5,
            level_title="Scholar",
            activities=ActivityCounters(
                flashcards_reviewed=0,
                quizzes_passed=0,
                evaluations_submitted=0,
                guides_completed=0
            ),
            streak=StreakInfo(
                current_count=5,
                longest_count=10,
                last_activity_date=datetime.now(timezone.utc).date()
            ),
            week7_quest=Week7Quest(
                active=False,
                course_id=None,
                exam_readiness_percent=0,
                boss_battle_completed=False,
                double_xp_earned=0
            ),
            created_at=datetime.now(timezone.utc)
        )

    # =============================================================================
    # Quest Activation Tests
    # =============================================================================

    def test_activate_quest_success(self, quest_service, base_stats):
        """Test successful quest activation."""
        # Mock Firestore document
        doc_mock = Mock()
        doc_mock.exists = True
        doc_mock.to_dict.return_value = base_stats.model_dump(mode='json')
        
        quest_service.db.collection.return_value.document.return_value.get.return_value = doc_mock
        
        # Activate quest
        activated, message = quest_service.check_and_activate_quest(
            user_id="test_user",
            course_id="test_course",
            current_week=7
        )
        
        assert activated is True
        assert "activated" in message.lower()

    def test_activate_quest_wrong_week(self, quest_service, base_stats):
        """Test quest activation fails for wrong week."""
        doc_mock = Mock()
        doc_mock.exists = True
        doc_mock.to_dict.return_value = base_stats.model_dump(mode='json')

        quest_service.db.collection.return_value.document.return_value.get.return_value = doc_mock

        # Try to activate in week 5
        activated, message = quest_service.check_and_activate_quest(
            user_id="test_user",
            course_id="test_course",
            current_week=5
        )

        assert activated is False
        assert message is not None
        assert "week 7" in message.lower()
        assert "current week: 5" in message.lower()

    def test_activate_quest_wrong_course(self, quest_service, base_stats):
        """Test quest activation fails for wrong course."""
        # Set different course_id in stats
        base_stats.course_id = "different_course"
        
        doc_mock = Mock()
        doc_mock.exists = True
        doc_mock.to_dict.return_value = base_stats.model_dump(mode='json')
        
        quest_service.db.collection.return_value.document.return_value.get.return_value = doc_mock
        
        # Try to activate for different course
        activated, message = quest_service.check_and_activate_quest(
            user_id="test_user",
            course_id="test_course",
            current_week=7
        )
        
        assert activated is False
        assert "current course" in message.lower()

    def test_activate_quest_already_active(self, quest_service, base_stats):
        """Test quest activation fails if already active."""
        base_stats.week7_quest.active = True
        
        doc_mock = Mock()
        doc_mock.exists = True
        doc_mock.to_dict.return_value = base_stats.model_dump(mode='json')
        
        quest_service.db.collection.return_value.document.return_value.get.return_value = doc_mock
        
        activated, message = quest_service.check_and_activate_quest(
            user_id="test_user",
            course_id="test_course",
            current_week=7
        )
        
        assert activated is False
        assert "already active" in message.lower()

    def test_activate_quest_already_completed(self, quest_service, base_stats):
        """Test quest activation fails if already completed."""
        base_stats.week7_quest.boss_battle_completed = True
        
        doc_mock = Mock()
        doc_mock.exists = True
        doc_mock.to_dict.return_value = base_stats.model_dump(mode='json')
        
        quest_service.db.collection.return_value.document.return_value.get.return_value = doc_mock
        
        activated, message = quest_service.check_and_activate_quest(
            user_id="test_user",
            course_id="test_course",
            current_week=7
        )
        
        assert activated is False
        assert "already completed" in message.lower()

    # =============================================================================
    # Exam Readiness Calculation Tests
    # =============================================================================

    def test_exam_readiness_zero_activities(self, quest_service, base_stats):
        """Test exam readiness with no activities."""
        readiness = quest_service.calculate_exam_readiness(base_stats)
        assert readiness == 0

    def test_exam_readiness_partial_progress(self, quest_service, base_stats):
        """Test exam readiness with partial progress."""
        # Set some activities (50% of requirements)
        # Requirements: 50 flashcards, 5 quizzes, 3 evaluations, 2 guides
        base_stats.activities.flashcards_reviewed = 25  # 50% of 50
        base_stats.activities.quizzes_passed = 2  # 40% of 5 (but average will be ~47%)
        base_stats.activities.evaluations_submitted = 1  # 33% of 3
        base_stats.activities.guides_completed = 1  # 50% of 2

        readiness = quest_service.calculate_exam_readiness(base_stats)
        assert 40 <= readiness <= 50  # Should be around 43%

    def test_exam_readiness_full_progress(self, quest_service, base_stats):
        """Test exam readiness with all requirements met."""
        # Set all activities to meet requirements
        # Requirements: 50 flashcards, 5 quizzes, 3 evaluations, 2 guides
        base_stats.activities.flashcards_reviewed = 50
        base_stats.activities.quizzes_passed = 5
        base_stats.activities.evaluations_submitted = 3
        base_stats.activities.guides_completed = 2

        readiness = quest_service.calculate_exam_readiness(base_stats)
        assert readiness == 100

    def test_exam_readiness_over_requirements(self, quest_service, base_stats):
        """Test exam readiness caps at 100%."""
        # Set activities above requirements
        base_stats.activities.flashcards_reviewed = 100
        base_stats.activities.quizzes_passed = 10
        base_stats.activities.evaluations_submitted = 5
        base_stats.activities.guides_completed = 5
        
        readiness = quest_service.calculate_exam_readiness(base_stats)
        assert readiness == 100

    # =============================================================================
    # Quest Update Calculation Tests
    # =============================================================================

    def test_calculate_quest_updates_inactive_quest(self, quest_service, base_stats):
        """Test quest updates return empty dict when quest inactive."""
        updates = quest_service.calculate_quest_updates(
            user_id="test_user",
            xp_bonus=50,
            stats=base_stats,
            activity_type="quiz_completed"
        )
        
        assert updates == {}

    def test_calculate_quest_updates_with_activity(self, quest_service, base_stats):
        """Test quest updates calculate correctly with activity."""
        base_stats.week7_quest.active = True
        base_stats.week7_quest.course_id = "test_course"
        
        updates = quest_service.calculate_quest_updates(
            user_id="test_user",
            xp_bonus=50,
            stats=base_stats,
            activity_type="quiz_completed"
        )
        
        assert "week7_quest.exam_readiness_percent" in updates
        assert "week7_quest.double_xp_earned" in updates
        assert updates["week7_quest.double_xp_earned"] == 50

    def test_calculate_quest_updates_boss_completion(self, quest_service, base_stats):
        """Test boss battle completion when reaching 100% readiness."""
        base_stats.week7_quest.active = True
        base_stats.week7_quest.course_id = "test_course"

        # Set activities to almost complete
        # Requirements: 50 flashcards, 5 quizzes, 3 evaluations, 2 guides
        base_stats.activities.flashcards_reviewed = 49
        base_stats.activities.quizzes_passed = 5
        base_stats.activities.evaluations_submitted = 3
        base_stats.activities.guides_completed = 2

        # This flashcard should complete the quest
        updates = quest_service.calculate_quest_updates(
            user_id="test_user",
            xp_bonus=10,
            stats=base_stats,
            activity_type="flashcard_set_completed"
        )

        assert updates.get("week7_quest.boss_battle_completed") is True

    # =============================================================================
    # Edge Case Tests
    # =============================================================================

    def test_exam_readiness_with_negative_values(self, quest_service, base_stats):
        """Test exam readiness handles negative activity counts gracefully."""
        # This shouldn't happen, but test defensive programming
        base_stats.activities.flashcards_reviewed = -10
        base_stats.activities.quizzes_passed = -5
        
        readiness = quest_service.calculate_exam_readiness(base_stats)
        assert readiness >= 0  # Should not be negative

    def test_predict_stats_after_quiz(self, quest_service, base_stats):
        """Test stats prediction after quiz activity."""
        # Test quiz_completed - should increment completed but NOT passed (conservative)
        predicted = quest_service._predict_stats_after_activity(base_stats, "quiz_completed")

        assert predicted.activities.quizzes_completed == base_stats.activities.quizzes_completed + 1
        assert predicted.activities.quizzes_passed == base_stats.activities.quizzes_passed  # No increment

        # Test quiz_passed - should increment both
        predicted_passed = quest_service._predict_stats_after_activity(base_stats, "quiz_passed")

        assert predicted_passed.activities.quizzes_completed == base_stats.activities.quizzes_completed + 1
        assert predicted_passed.activities.quizzes_passed == base_stats.activities.quizzes_passed + 1

    def test_predict_stats_after_flashcard(self, quest_service, base_stats):
        """Test stats prediction after flashcard activity."""
        predicted = quest_service._predict_stats_after_activity(base_stats, "flashcard_set_completed")
        
        assert predicted.activities.flashcards_reviewed == base_stats.activities.flashcards_reviewed + 1

    def test_get_quest_requirements(self, quest_service):
        """Test getting quest requirements."""
        requirements = quest_service.get_quest_requirements()

        # Check structure
        assert "requirements" in requirements
        assert "double_xp_multiplier" in requirements
        assert "boss_battle" in requirements

        # Check individual requirements
        reqs = requirements["requirements"]
        assert "flashcards" in reqs
        assert "quizzes" in reqs
        assert "evaluations" in reqs
        assert "guides" in reqs

        # Check values
        assert reqs["flashcards"]["required"] == 50
        assert reqs["quizzes"]["required"] == 5
        assert reqs["evaluations"]["required"] == 3
        assert reqs["guides"]["required"] == 2


"""
API Endpoint Tests for Badge System (Phase 4)

Tests to verify API endpoints work correctly after field name fixes.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from app.models.gamification_models import (
    UserStats,
    BadgeDefinition,
    UserBadge,
    StreakInfo,
    ActivityCounters,
    User
)


class TestBadgeAPIEndpoints:
    """Test badge API endpoints work correctly."""

    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        return User(
            user_id="test_user_123",
            email="test@example.com",
            name="Test User"
        )

    def test_user_stats_with_activities_attribute(self, mock_user):
        """Test that UserStats uses 'activities' attribute correctly.
        
        FIX: Verify activities (not activity_counters) is used
        """
        # Create UserStats with activities attribute
        user_stats = UserStats(
            user_id=mock_user.user_id,
            user_email=mock_user.email,
            total_xp=1000,
            streak=StreakInfo(current_count=5),
            activities=ActivityCounters(
                flashcards_reviewed=50,
                quizzes_passed=10,
                evaluations_submitted=5,
                guides_completed=3
            )
        )
        
        # Verify attribute exists and is correct type
        assert hasattr(user_stats, 'activities')
        assert isinstance(user_stats.activities, ActivityCounters)
        
        # Verify we can access activity counters
        assert user_stats.activities.flashcards_reviewed == 50
        assert user_stats.activities.quizzes_passed == 10
        assert user_stats.activities.evaluations_submitted == 5
        assert user_stats.activities.guides_completed == 3

    def test_activity_counters_field_names(self):
        """Test that ActivityCounters has correct field names.
        
        FIX: Verify field names match model definition
        """
        counters = ActivityCounters(
            flashcards_reviewed=100,
            quizzes_completed=50,
            quizzes_passed=40,
            evaluations_submitted=25,
            guides_completed=15,
            total_study_time_minutes=300
        )
        
        # Verify all fields exist
        assert hasattr(counters, 'flashcards_reviewed')
        assert hasattr(counters, 'quizzes_completed')
        assert hasattr(counters, 'quizzes_passed')
        assert hasattr(counters, 'evaluations_submitted')
        assert hasattr(counters, 'guides_completed')
        assert hasattr(counters, 'total_study_time_minutes')
        
        # Verify values
        assert counters.flashcards_reviewed == 100
        assert counters.quizzes_completed == 50
        assert counters.quizzes_passed == 40
        assert counters.evaluations_submitted == 25
        assert counters.guides_completed == 15
        assert counters.total_study_time_minutes == 300

    def test_badge_service_uses_correct_attributes(self, mock_user):
        """Test that badge service uses correct attribute names.
        
        FIX: Verify badge service accesses user_stats.activities
        """
        from app.services.badge_service import BadgeService
        
        user_stats = UserStats(
            user_id=mock_user.user_id,
            user_email=mock_user.email,
            total_xp=1000,
            streak=StreakInfo(current_count=5),
            activities=ActivityCounters(
                flashcards_reviewed=100,
                quizzes_passed=50,
                evaluations_submitted=25,
                guides_completed=15
            )
        )
        
        # Create badge definition for flashcard activity
        badge_def = BadgeDefinition(
            badge_id="flashcard_fanatic",
            name="Flashcard Fanatic",
            description="Complete 100 flashcard sets",
            category="activity",
            icon="📇",
            rarity="rare",
            criteria={"flashcard_sets": 100},
            points=100,
            active=True
        )
        
        with patch.object(BadgeService, '_get_badge_definitions') as mock_get_defs:
            mock_get_defs.return_value = [badge_def]
            
            service = BadgeService()
            service.db = Mock()
            
            # This should work without AttributeError
            try:
                result = service._check_badge_criteria(badge_def, user_stats)
                # Should return True because flashcards_reviewed (100) >= criteria (100)
                assert result == True
            except AttributeError as e:
                pytest.fail(f"AttributeError accessing activities: {e}")

    def test_badge_progress_calculation_with_correct_fields(self, mock_user):
        """Test badge progress calculation uses correct field names.
        
        FIX: Verify progress calculation accesses user_stats.activities.flashcards_reviewed
        """
        from app.services.badge_service import BadgeService
        
        user_stats = UserStats(
            user_id=mock_user.user_id,
            user_email=mock_user.email,
            total_xp=500,
            streak=StreakInfo(current_count=5),
            activities=ActivityCounters(
                flashcards_reviewed=50,  # 50% toward 100
                quizzes_passed=25,
                evaluations_submitted=10,
                guides_completed=5
            )
        )
        
        badge_def = BadgeDefinition(
            badge_id="flashcard_fanatic",
            name="Flashcard Fanatic",
            description="Complete 100 flashcard sets",
            category="activity",
            icon="📇",
            rarity="rare",
            criteria={"flashcard_sets": 100},
            points=100,
            active=True
        )
        
        service = BadgeService()
        service.db = Mock()
        
        # Calculate progress
        try:
            progress = service._calculate_progress(badge_def, user_stats)
            
            # Verify progress is calculated correctly
            assert progress is not None
            assert progress["current"] == 50
            assert progress["required"] == 100
            assert progress["percentage"] == 50
        except AttributeError as e:
            pytest.fail(f"AttributeError calculating progress: {e}")

    def test_field_mapping_in_activity_criteria(self):
        """Test that field mapping works correctly.
        
        FIX: Verify field mapping from badge criteria to ActivityCounters
        """
        from app.services.badge_service import BadgeService
        
        service = BadgeService()
        service.db = Mock()
        
        # Test the field mapping
        counters = ActivityCounters(
            flashcards_reviewed=100,
            quizzes_passed=50,
            evaluations_submitted=25,
            guides_completed=15
        )
        
        # Test flashcard_sets -> flashcards_reviewed
        criteria1 = {"flashcard_sets": 100}
        result1 = service._check_activity_criteria(criteria1, counters)
        assert result1 == True  # 100 >= 100
        
        # Test quizzes_passed -> quizzes_passed (direct match)
        criteria2 = {"quizzes_passed": 50}
        result2 = service._check_activity_criteria(criteria2, counters)
        assert result2 == True  # 50 >= 50
        
        # Test evaluations -> evaluations_submitted
        criteria3 = {"evaluations": 25}
        result3 = service._check_activity_criteria(criteria3, counters)
        assert result3 == True  # 25 >= 25
        
        # Test study_guides -> guides_completed
        criteria4 = {"study_guides": 15}
        result4 = service._check_activity_criteria(criteria4, counters)
        assert result4 == True  # 15 >= 15
        
        # Test criteria not met
        criteria5 = {"flashcard_sets": 200}
        result5 = service._check_activity_criteria(criteria5, counters)
        assert result5 == False  # 100 < 200

    def test_multiple_activity_criteria(self):
        """Test badge with multiple activity criteria.
        
        FIX: Verify all criteria are checked correctly
        """
        from app.services.badge_service import BadgeService
        
        service = BadgeService()
        service.db = Mock()
        
        counters = ActivityCounters(
            flashcards_reviewed=10,
            quizzes_passed=10,
            evaluations_submitted=10,
            guides_completed=10
        )
        
        # Well-rounded badge requires 10 of each
        criteria = {
            "flashcard_sets": 10,
            "quizzes_passed": 10,
            "evaluations": 10,
            "study_guides": 10
        }
        
        result = service._check_activity_criteria(criteria, counters)
        assert result == True  # All criteria met
        
        # Test with one criterion not met
        counters_partial = ActivityCounters(
            flashcards_reviewed=10,
            quizzes_passed=10,
            evaluations_submitted=10,
            guides_completed=5  # Only 5, needs 10
        )
        
        result_partial = service._check_activity_criteria(criteria, counters_partial)
        assert result_partial == False  # Not all criteria met

    def test_api_endpoint_structure_verification(self):
        """Test that API endpoint response structure is correct.
        
        This verifies the endpoint would work correctly with fixed field names.
        """
        # This is a structural test - actual endpoint testing would require TestClient
        
        # Verify UserStats can be serialized with activities
        user_stats = UserStats(
            user_id="test_user",
            user_email="test@example.com",
            total_xp=1000,
            activities=ActivityCounters(
                flashcards_reviewed=50,
                quizzes_passed=25
            )
        )
        
        # Serialize to dict (as API would do)
        stats_dict = user_stats.model_dump(mode='json')
        
        # Verify structure
        assert 'activities' in stats_dict
        assert 'flashcards_reviewed' in stats_dict['activities']
        assert stats_dict['activities']['flashcards_reviewed'] == 50

    def test_badge_definition_serialization(self):
        """Test that badge definitions serialize correctly.
        
        Verifies API can return badge definitions properly.
        """
        badge = BadgeDefinition(
            badge_id="test_badge",
            name="Test Badge",
            description="Test",
            category="activity",
            icon="🎯",
            rarity="common",
            criteria={"flashcard_sets": 100},
            points=10,
            active=True
        )
        
        # Serialize to dict (as API would do)
        badge_dict = badge.model_dump(mode='json')
        
        # Verify structure
        assert badge_dict['badge_id'] == "test_badge"
        assert badge_dict['category'] == "activity"
        assert badge_dict['criteria'] == {"flashcard_sets": 100}
        assert badge_dict['active'] == True

    def test_user_badge_serialization(self):
        """Test that user badges serialize correctly.

        Verifies API can return earned badges properly.
        """
        user_badge = UserBadge(
            user_id="test_user",
            badge_id="test_badge",
            badge_name="Test Badge",
            badge_description="A test badge",
            badge_icon="🏆",
            earned_at=datetime.now(timezone.utc)
        )
        
        # Serialize to dict (as API would do)
        badge_dict = user_badge.model_dump(mode='json')
        
        # Verify structure
        assert badge_dict['user_id'] == "test_user"
        assert badge_dict['badge_id'] == "test_badge"
        assert 'earned_at' in badge_dict


class TestFieldNameConsistency:
    """Test field name consistency across the system."""

    def test_no_activity_counters_attribute(self):
        """Verify UserStats does NOT have activity_counters attribute."""
        user_stats = UserStats(
            user_id="test",
            user_email="test@example.com"
        )

        # Should have 'activities'
        assert hasattr(user_stats, 'activities')

        # Should NOT have 'activity_counters'
        assert not hasattr(user_stats, 'activity_counters')

    def test_no_flashcard_sets_completed_field(self):
        """Verify ActivityCounters does NOT have flashcard_sets_completed field."""
        counters = ActivityCounters()

        # Should have 'flashcards_reviewed'
        assert hasattr(counters, 'flashcards_reviewed')

        # Should NOT have 'flashcard_sets_completed'
        assert not hasattr(counters, 'flashcard_sets_completed')

    def test_complete_field_name_mapping(self):
        """Test complete field name mapping from badge criteria to ActivityCounters.

        CRITICAL: Verifies all badge criteria map to correct ActivityCounters fields
        """
        from app.services.badge_service import BadgeService

        service = BadgeService()
        service.db = Mock()

        # Create ActivityCounters with all fields
        counters = ActivityCounters(
            flashcards_reviewed=100,
            quizzes_completed=75,
            quizzes_passed=50,
            evaluations_submitted=25,
            guides_completed=15,
            total_study_time_minutes=300
        )

        # Test all mappings
        test_cases = [
            # (badge_criteria_key, expected_field_name, counter_value, criteria_value, should_pass)
            ("flashcard_sets", "flashcards_reviewed", 100, 100, True),
            ("flashcard_sets", "flashcards_reviewed", 100, 150, False),
            ("quizzes_passed", "quizzes_passed", 50, 50, True),
            ("quizzes_passed", "quizzes_passed", 50, 75, False),
            ("evaluations", "evaluations_submitted", 25, 25, True),
            ("evaluations", "evaluations_submitted", 25, 30, False),
            ("study_guides", "guides_completed", 15, 15, True),
            ("study_guides", "guides_completed", 15, 20, False),
        ]

        for criteria_key, field_name, counter_value, criteria_value, should_pass in test_cases:
            # Verify field exists in ActivityCounters
            assert hasattr(counters, field_name), f"ActivityCounters missing field: {field_name}"

            # Verify field value matches expected
            actual_value = getattr(counters, field_name)
            assert actual_value == counter_value, f"Field {field_name} has wrong value: {actual_value} != {counter_value}"

            # Test badge criteria checking
            criteria = {criteria_key: criteria_value}
            result = service._check_activity_criteria(criteria, counters)

            if should_pass:
                assert result == True, f"Criteria {criteria_key}={criteria_value} should pass with {field_name}={counter_value}"
            else:
                assert result == False, f"Criteria {criteria_key}={criteria_value} should fail with {field_name}={counter_value}"

    def test_field_mapping_with_zero_values(self):
        """Test field mapping works correctly with zero values.

        Ensures zero values don't cause false positives.
        """
        from app.services.badge_service import BadgeService

        service = BadgeService()
        service.db = Mock()

        # Create ActivityCounters with all zeros
        counters = ActivityCounters(
            flashcards_reviewed=0,
            quizzes_passed=0,
            evaluations_submitted=0,
            guides_completed=0
        )

        # All criteria should fail with zero values
        test_cases = [
            {"flashcard_sets": 1},
            {"quizzes_passed": 1},
            {"evaluations": 1},
            {"study_guides": 1},
        ]

        for criteria in test_cases:
            result = service._check_activity_criteria(criteria, counters)
            assert result == False, f"Criteria {criteria} should fail with zero values"

    def test_field_mapping_with_exact_match(self):
        """Test field mapping with exact criteria match.

        Verifies >= comparison works correctly.
        """
        from app.services.badge_service import BadgeService

        service = BadgeService()
        service.db = Mock()

        # Create ActivityCounters with specific values
        counters = ActivityCounters(
            flashcards_reviewed=100,
            quizzes_passed=50,
            evaluations_submitted=25,
            guides_completed=10
        )

        # Test exact matches (should all pass)
        test_cases = [
            {"flashcard_sets": 100},  # Exact match
            {"quizzes_passed": 50},   # Exact match
            {"evaluations": 25},      # Exact match
            {"study_guides": 10},     # Exact match
        ]

        for criteria in test_cases:
            result = service._check_activity_criteria(criteria, counters)
            assert result == True, f"Criteria {criteria} should pass with exact match"

    def test_field_mapping_with_multiple_criteria(self):
        """Test field mapping with multiple criteria (AND logic).

        Verifies all criteria must be met.
        """
        from app.services.badge_service import BadgeService

        service = BadgeService()
        service.db = Mock()

        # Create ActivityCounters
        counters = ActivityCounters(
            flashcards_reviewed=100,
            quizzes_passed=50,
            evaluations_submitted=25,
            guides_completed=10
        )

        # Test multiple criteria - all met
        criteria_all_met = {
            "flashcard_sets": 100,
            "quizzes_passed": 50,
            "evaluations": 25,
            "study_guides": 10
        }
        result = service._check_activity_criteria(criteria_all_met, counters)
        assert result == True, "All criteria met should pass"

        # Test multiple criteria - one not met
        criteria_one_not_met = {
            "flashcard_sets": 100,
            "quizzes_passed": 50,
            "evaluations": 25,
            "study_guides": 20  # Not met (only have 10)
        }
        result = service._check_activity_criteria(criteria_one_not_met, counters)
        assert result == False, "One criterion not met should fail"


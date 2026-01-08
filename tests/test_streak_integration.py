"""Integration tests for Streak System with Firestore Emulator.

These tests require the Firestore emulator to be running:
    firebase emulators:start --only firestore

Set environment variable:
    export FIRESTORE_EMULATOR_HOST="localhost:8080"
"""

import pytest
import os
from datetime import datetime, timezone, timedelta
from google.cloud import firestore
from app.services.gamification_service import GamificationService
from app.services.streak_maintenance import StreakMaintenanceService
from app.models.gamification_models import UserStats, StreakInfo


# Skip if emulator not available
pytestmark = pytest.mark.skipif(
    not os.environ.get('FIRESTORE_EMULATOR_HOST'),
    reason="Firestore emulator not running. Set FIRESTORE_EMULATOR_HOST=localhost:8080"
)


@pytest.fixture(scope="function")
def firestore_client():
    """Create Firestore client connected to emulator."""
    # Ensure we're using the emulator
    assert os.environ.get('FIRESTORE_EMULATOR_HOST'), "Emulator must be running"
    
    client = firestore.Client(project="test-project")
    yield client
    
    # Cleanup: Delete all test data
    collections = client.collections()
    for collection in collections:
        for doc in collection.stream():
            doc.reference.delete()


@pytest.fixture
def gamification_service(firestore_client):
    """Create gamification service with emulator."""
    service = GamificationService()
    service.db = firestore_client
    return service


@pytest.fixture
def maintenance_service(firestore_client, gamification_service):
    """Create maintenance service with emulator."""
    service = StreakMaintenanceService()
    service.db = firestore_client
    service.gamification_service = gamification_service
    return service


class TestWeeklyConsistencyIntegration:
    """Integration tests for weekly consistency bonus."""

    def test_complete_weekly_consistency_flow(self, gamification_service):
        """Test complete flow from activity logging to bonus activation."""
        user_id = "integration_test_user_1"
        user_email = "test1@example.com"
        course_id = "test_course"
        
        # Step 1: Log flashcard activity
        result1 = gamification_service.log_activity(
            user_id=user_id,
            user_email=user_email,
            course_id=course_id,
            activity_type="flashcard_set_completed",
            activity_data={"cards_completed": 10, "correct": 8}
        )
        assert result1 is not None
        assert result1.xp_awarded > 0
        
        # Step 2: Log quiz activity
        result2 = gamification_service.log_activity(
            user_id=user_id,
            user_email=user_email,
            course_id=course_id,
            activity_type="quiz_completed",
            activity_data={"score": 8, "total_questions": 10, "difficulty": "easy"}
        )
        assert result2 is not None
        
        # Step 3: Log evaluation activity
        result3 = gamification_service.log_activity(
            user_id=user_id,
            user_email=user_email,
            course_id=course_id,
            activity_type="evaluation_completed",
            activity_data={"grade": 8, "complexity": "low"}
        )
        assert result3 is not None
        
        # Step 4: Log study guide activity (completes all 4 categories)
        result4 = gamification_service.log_activity(
            user_id=user_id,
            user_email=user_email,
            course_id=course_id,
            activity_type="study_guide_completed",
            activity_data={"sections": 5}
        )
        assert result4 is not None
        
        # Step 5: Verify bonus is now active
        stats = gamification_service.get_or_create_user_stats(user_id, user_email, course_id)
        assert stats is not None
        assert stats.streak.bonus_active is True, "Bonus should be active after completing all 4 categories"
        assert stats.streak.bonus_multiplier == 1.5, "Bonus multiplier should be 1.5 (50% boost)"
        
        # Step 6: Log another activity and verify bonus is applied
        base_xp = result1.xp_awarded
        result5 = gamification_service.log_activity(
            user_id=user_id,
            user_email=user_email,
            course_id=course_id,
            activity_type="flashcard_set_completed",
            activity_data={"cards_completed": 10, "correct": 8}
        )
        
        # XP should be multiplied by 1.5
        expected_xp = int(base_xp * 1.5)
        assert result5.xp_awarded == expected_xp, f"XP should be {expected_xp} (base {base_xp} * 1.5)"

    def test_weekly_consistency_race_condition(self, gamification_service):
        """Test that concurrent consistency updates don't cause duplicate bonuses."""
        user_id = "race_test_user"
        user_email = "race@example.com"
        course_id = "test_course"
        
        # Complete 3 categories
        for activity_type in ["flashcard_set_completed", "quiz_completed", "evaluation_completed"]:
            gamification_service.log_activity(
                user_id=user_id,
                user_email=user_email,
                course_id=course_id,
                activity_type=activity_type,
                activity_data={"test": True}
            )
        
        # Simulate concurrent completion of 4th category
        # Both should try to complete "guide" category
        import concurrent.futures
        
        def complete_guide():
            return gamification_service.log_activity(
                user_id=user_id,
                user_email=user_email,
                course_id=course_id,
                activity_type="study_guide_completed",
                activity_data={"sections": 5}
            )
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(complete_guide) for _ in range(2)]
            results = [f.result() for f in futures]
        
        # Both should succeed, but bonus should only be activated once
        assert all(r is not None for r in results), "Both activities should be logged"
        
        # Verify bonus is active exactly once
        stats = gamification_service.get_or_create_user_stats(user_id, user_email, course_id)
        assert stats.streak.bonus_active is True
        assert stats.streak.bonus_multiplier == 1.5


class TestStreakFreezeIntegration:
    """Integration tests for streak freeze application."""

    def test_freeze_application_flow(self, gamification_service, maintenance_service):
        """Test complete freeze application flow."""
        user_id = "freeze_test_user"
        user_email = "freeze@example.com"
        course_id = "test_course"
        
        # Step 1: Create user with activity yesterday
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        gamification_service.log_activity(
            user_id=user_id,
            user_email=user_email,
            course_id=course_id,
            activity_type="flashcard_set_completed",
            activity_data={"cards_completed": 10}
        )
        
        # Manually set last_active to yesterday
        stats = gamification_service.get_or_create_user_stats(user_id, user_email, course_id)
        doc_ref = gamification_service.db.collection("user_stats").document(user_id)
        doc_ref.update({"last_active": yesterday})
        
        # Give user some freezes
        doc_ref.update({"streak.freezes_available": 2, "streak.current_count": 5})
        
        # Step 2: Run maintenance (should apply freeze for missed day)
        stats_before = gamification_service.get_or_create_user_stats(user_id, user_email, course_id)
        freezes_before = stats_before.streak.freezes_available
        
        result = maintenance_service.run_daily_maintenance()
        
        # Step 3: Verify freeze was applied
        assert result["status"] == "success"
        
        stats_after = gamification_service.get_or_create_user_stats(user_id, user_email, course_id)
        assert stats_after.streak.freezes_available == freezes_before - 1, "One freeze should be used"
        assert stats_after.streak.current_count == 5, "Streak should be maintained"

    def test_freeze_race_condition_prevention(self, maintenance_service):
        """Test that concurrent freeze applications don't cause negative counts."""
        user_id = "concurrent_freeze_user"
        
        # Create user with 1 freeze
        doc_ref = maintenance_service.db.collection("user_stats").document(user_id)
        doc_ref.set({
            "user_id": user_id,
            "user_email": "concurrent@example.com",
            "streak": {
                "freezes_available": 1,
                "current_count": 5
            }
        })
        
        # Try to apply freeze concurrently
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(maintenance_service._apply_freeze, user_id) for _ in range(3)]
            results = [f.result() for f in futures]
        
        # Only one should succeed
        success_count = sum(1 for r in results if r is True)
        assert success_count == 1, "Only one freeze application should succeed"
        
        # Verify freeze count is 0 (not negative)
        doc = doc_ref.get()
        freezes = doc.to_dict()["streak"]["freezes_available"]
        assert freezes == 0, "Freeze count should be 0, not negative"


class TestMaintenanceJobIntegration:
    """Integration tests for daily maintenance job."""

    def test_maintenance_job_with_multiple_users(self, gamification_service, maintenance_service):
        """Test maintenance job processes multiple users correctly."""
        # Create 10 test users with different streak states
        users = []
        for i in range(10):
            user_id = f"maintenance_user_{i}"
            user_email = f"user{i}@example.com"
            
            # Log activity
            gamification_service.log_activity(
                user_id=user_id,
                user_email=user_email,
                course_id="test_course",
                activity_type="flashcard_set_completed",
                activity_data={"cards_completed": 10}
            )
            
            # Set different last_active times
            doc_ref = gamification_service.db.collection("user_stats").document(user_id)
            
            if i < 3:
                # Users 0-2: Active today (no action needed)
                doc_ref.update({"last_active": datetime.now(timezone.utc)})
            elif i < 6:
                # Users 3-5: Missed 1 day, have freezes
                yesterday = datetime.now(timezone.utc) - timedelta(days=1)
                doc_ref.update({
                    "last_active": yesterday,
                    "streak.freezes_available": 2,
                    "streak.current_count": 5
                })
            else:
                # Users 6-9: Missed 2+ days, streak broken
                two_days_ago = datetime.now(timezone.utc) - timedelta(days=2)
                doc_ref.update({
                    "last_active": two_days_ago,
                    "streak.freezes_available": 0,
                    "streak.current_count": 5
                })
            
            users.append(user_id)
        
        # Run maintenance
        result = maintenance_service.run_daily_maintenance()
        
        # Verify results
        assert result["status"] == "success"
        assert result["users_processed"] == 10
        assert result["freezes_applied"] == 3  # Users 3-5
        assert result["streaks_broken"] == 4   # Users 6-9


class TestLoadTest:
    """Load tests for maintenance job with production-scale data."""

    @pytest.mark.slow
    def test_maintenance_job_performance(self, gamification_service, maintenance_service):
        """Test maintenance job with 1000 users (production scale)."""
        import time
        
        # Create 1000 users
        print("\nCreating 1000 test users...")
        for i in range(1000):
            user_id = f"load_test_user_{i}"
            gamification_service.log_activity(
                user_id=user_id,
                user_email=f"user{i}@example.com",
                course_id="test_course",
                activity_type="flashcard_set_completed",
                activity_data={"cards_completed": 10}
            )
            
            if i % 100 == 0:
                print(f"Created {i} users...")
        
        print("Running maintenance job...")
        start_time = time.time()
        result = maintenance_service.run_daily_maintenance()
        duration = time.time() - start_time
        
        print(f"\nMaintenance completed in {duration:.2f} seconds")
        print(f"Users processed: {result['users_processed']}")
        print(f"Processing rate: {result['users_processed'] / duration:.2f} users/second")
        
        # Performance assertions
        assert result["status"] == "success"
        assert result["users_processed"] == 1000
        assert duration < 60, "Should process 1000 users in under 60 seconds"
        assert result["errors"] == 0, "Should have no errors"


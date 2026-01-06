"""Tests for Gamification Badge System.

Tests the badge earning functionality including:
- Badge seeding and definitions
- Badge earning for all 6 badge types
- Tier progression (Bronze → Silver → Gold)
- Time-based badges (Night Owl, Early Riser)
- Sequence-based badges (Hat Trick, Legal Scholar)
- Combo-based badges (Combo King, Deep Diver)
- Edge cases and boundary conditions
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, call

from app.services.gamification_service import GamificationService
from app.models.gamification_models import (
    BadgeDefinition,
    UserBadge,
    UserActivity
)


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


def setup_firestore_mocks(mock_firestore, badge_def_doc, user_badge_doc):
    """Helper to setup Firestore mocks for badge tests.

    Args:
        mock_firestore: The mock Firestore client
        badge_def_doc: Mock document for badge definition
        user_badge_doc: Mock document for user badge

    Returns:
        mock_user_badge_ref: The mock reference for user badge operations
    """
    # Path 1: badge_definitions/{badge_id}
    mock_badge_def_ref = MagicMock()
    mock_badge_def_ref.get.return_value = badge_def_doc

    # Path 2: user_achievements/{user_id}/badges/{badge_id}
    mock_user_badge_ref = MagicMock()
    mock_user_badge_ref.get.return_value = user_badge_doc

    # Mock the collection chain
    def collection_side_effect(collection_name):
        mock_collection = MagicMock()
        if collection_name == "badge_definitions":
            mock_collection.document.return_value = mock_badge_def_ref
        elif collection_name == "user_achievements":
            mock_user_doc = MagicMock()
            mock_badges_collection = MagicMock()
            mock_badges_collection.document.return_value = mock_user_badge_ref
            mock_user_doc.collection.return_value = mock_badges_collection
            mock_collection.document.return_value = mock_user_doc
        return mock_collection

    mock_firestore.collection.side_effect = collection_side_effect
    return mock_user_badge_ref


@pytest.fixture
def sample_badge_definitions():
    """Create sample badge definitions for testing."""
    return [
        BadgeDefinition(
            badge_id="night_owl",
            name="Night Owl",
            description="Complete a Hard Quiz or AI Evaluation between 11:00 PM and 3:00 AM",
            icon="🦉",
            category="behavioral",
            tiers=["bronze", "silver", "gold"],
            tier_requirements={"bronze": 1, "silver": 5, "gold": 10}
        ),
        BadgeDefinition(
            badge_id="early_riser",
            name="Early Riser",
            description="Complete a Study Guide before 8:00 AM",
            icon="☀️",
            category="behavioral",
            tiers=["bronze", "silver", "gold"],
            tier_requirements={"bronze": 1, "silver": 5, "gold": 10}
        ),
        BadgeDefinition(
            badge_id="hat_trick",
            name="Hat Trick",
            description="Pass 3 separate Hard Quizzes in a row with 100% accuracy",
            icon="🎩",
            category="achievement",
            tiers=["bronze", "silver", "gold"],
            tier_requirements={"bronze": 1, "silver": 3, "gold": 5}
        ),
        BadgeDefinition(
            badge_id="combo_king",
            name="Combo King",
            description="Flip 20 Flashcards in a row without marking one as incorrect",
            icon="🔥",
            category="achievement",
            tiers=["bronze", "silver", "gold"],
            tier_requirements={"bronze": 1, "silver": 5, "gold": 10}
        ),
        BadgeDefinition(
            badge_id="legal_scholar",
            name="Legal Scholar",
            description="Achieve an AI Grade of 9 or 10 on three consecutive Evaluations",
            icon="⚖️",
            category="achievement",
            tiers=["bronze", "silver", "gold"],
            tier_requirements={"bronze": 1, "silver": 3, "gold": 5}
        ),
        BadgeDefinition(
            badge_id="deep_diver",
            name="Deep Diver",
            description="Spend 45+ minutes interacting with a single Study Guide without navigating away",
            icon="📖",
            category="behavioral",
            tiers=["bronze", "silver", "gold"],
            tier_requirements={"bronze": 1, "silver": 5, "gold": 10}
        )
    ]


# =============================================================================
# Badge Seeding Tests
# =============================================================================

def test_seed_badge_definitions_success(gamification_service, mock_firestore):
    """Test successful badge definition seeding."""
    # Setup mock
    mock_doc_ref = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = False
    mock_doc_ref.get.return_value = mock_doc
    mock_firestore.collection.return_value.document.return_value = mock_doc_ref
    
    # Execute
    result = gamification_service.seed_badge_definitions()
    
    # Verify
    assert result is True
    assert mock_doc_ref.set.call_count == 6  # 6 badges seeded


def test_seed_badge_definitions_skip_existing(gamification_service, mock_firestore):
    """Test that seeding skips existing badges."""
    # Setup mock - badge already exists
    mock_doc_ref = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc_ref.get.return_value = mock_doc
    mock_firestore.collection.return_value.document.return_value = mock_doc_ref
    
    # Execute
    result = gamification_service.seed_badge_definitions()
    
    # Verify
    assert result is True
    assert mock_doc_ref.set.call_count == 0  # No badges created


def test_seed_badge_definitions_no_firestore():
    """Test seeding fails gracefully without Firestore."""
    # Mock get_firestore_client to return None
    with patch('app.services.gamification_service.get_firestore_client', return_value=None):
        service = GamificationService()
        result = service.seed_badge_definitions()
        assert result is False


# =============================================================================
# Badge Retrieval Tests
# =============================================================================

def test_get_badge_definitions_success(gamification_service, mock_firestore, sample_badge_definitions):
    """Test retrieving all badge definitions."""
    # Setup mock
    mock_docs = []
    for badge_def in sample_badge_definitions:
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = badge_def.model_dump(mode='json')
        mock_docs.append(mock_doc)

    mock_firestore.collection.return_value.where.return_value.stream.return_value = mock_docs

    # Execute
    result = gamification_service.get_badge_definitions()

    # Verify
    assert len(result) == 6
    assert all(isinstance(badge, BadgeDefinition) for badge in result)


def test_get_user_badges_success(gamification_service, mock_firestore):
    """Test retrieving user's earned badges."""
    # Setup mock
    mock_badge_data = {
        "badge_id": "night_owl",
        "badge_name": "Night Owl",
        "badge_description": "Complete a Hard Quiz or AI Evaluation between 11:00 PM and 3:00 AM",
        "badge_icon": "🦉",
        "tier": "bronze",
        "earned_at": datetime.now(timezone.utc),
        "times_earned": 1
    }

    mock_doc = MagicMock()
    mock_doc.to_dict.return_value = mock_badge_data

    mock_firestore.collection.return_value.document.return_value.collection.return_value.stream.return_value = [mock_doc]

    # Execute
    result = gamification_service.get_user_badges("test-user-123")

    # Verify
    assert len(result) == 1
    assert isinstance(result[0], UserBadge)
    assert result[0].badge_id == "night_owl"


# =============================================================================
# Time-Based Badge Tests
# =============================================================================

@patch('app.services.gamification_service.datetime')
def test_night_owl_badge_earned_hard_quiz(mock_datetime, gamification_service, mock_firestore):
    """Test Night Owl badge earned for hard quiz at night."""
    # Setup - 11:30 PM
    mock_now = datetime(2024, 1, 15, 23, 30, 0, tzinfo=timezone.utc)
    mock_datetime.now.return_value = mock_now

    # Mock badge definition exists
    mock_badge_def_doc = MagicMock()
    mock_badge_def_doc.exists = True
    mock_badge_def_doc.to_dict.return_value = {
        "badge_id": "night_owl",
        "name": "Night Owl",
        "description": "Complete a Hard Quiz or AI Evaluation between 11:00 PM and 3:00 AM",
        "icon": "🦉",
        "category": "behavioral",
        "tiers": ["bronze", "silver", "gold"],
        "tier_requirements": {"bronze": 1, "silver": 5, "gold": 10}
    }

    # Mock user doesn't have badge yet
    mock_user_badge_doc = MagicMock()
    mock_user_badge_doc.exists = False

    # Setup Firestore mocks
    mock_user_badge_ref = setup_firestore_mocks(mock_firestore, mock_badge_def_doc, mock_user_badge_doc)

    # Execute
    activity_data = {"difficulty": "hard", "score": 10, "total_questions": 10}
    earned_badges = gamification_service.check_and_award_badges(
        "test-user-123",
        "test@example.com",
        "quiz_completed",
        activity_data
    )

    # Verify
    assert "night_owl" in earned_badges
    assert mock_user_badge_ref.set.called


@patch('app.services.gamification_service.datetime')
def test_night_owl_badge_not_earned_daytime(mock_datetime, gamification_service, mock_firestore):
    """Test Night Owl badge NOT earned during daytime."""
    # Setup - 2:00 PM
    mock_now = datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)
    mock_datetime.now.return_value = mock_now

    # Execute
    activity_data = {"difficulty": "hard", "score": 10, "total_questions": 10}
    earned_badges = gamification_service.check_and_award_badges(
        "test-user-123",
        "test@example.com",
        "quiz_completed",
        activity_data
    )

    # Verify
    assert "night_owl" not in earned_badges


@patch('app.services.gamification_service.datetime')
def test_early_riser_badge_earned(mock_datetime, gamification_service, mock_firestore):
    """Test Early Riser badge earned for study guide before 8 AM."""
    # Setup - 7:00 AM
    mock_now = datetime(2024, 1, 15, 7, 0, 0, tzinfo=timezone.utc)
    mock_datetime.now.return_value = mock_now

    # Mock badge definition and user badge
    mock_badge_def_doc = MagicMock()
    mock_badge_def_doc.exists = True
    mock_badge_def_doc.to_dict.return_value = {
        "badge_id": "early_riser",
        "name": "Early Riser",
        "description": "Complete a Study Guide before 8:00 AM",
        "icon": "☀️",
        "category": "behavioral",
        "tiers": ["bronze", "silver", "gold"],
        "tier_requirements": {"bronze": 1, "silver": 5, "gold": 10}
    }

    mock_user_badge_doc = MagicMock()
    mock_user_badge_doc.exists = False

    # Setup Firestore mocks
    mock_user_badge_ref = setup_firestore_mocks(mock_firestore, mock_badge_def_doc, mock_user_badge_doc)

    # Execute
    activity_data = {"time_spent_minutes": 30}
    earned_badges = gamification_service.check_and_award_badges(
        "test-user-123",
        "test@example.com",
        "study_guide_completed",
        activity_data
    )

    # Verify
    assert "early_riser" in earned_badges


def test_deep_diver_badge_earned(gamification_service, mock_firestore):
    """Test Deep Diver badge earned for 45+ minutes on study guide."""
    # Mock badge definition and user badge
    mock_badge_def_doc = MagicMock()
    mock_badge_def_doc.exists = True
    mock_badge_def_doc.to_dict.return_value = {
        "badge_id": "deep_diver",
        "name": "Deep Diver",
        "description": "Spend 45+ minutes interacting with a single Study Guide",
        "icon": "📖",
        "category": "behavioral",
        "tiers": ["bronze", "silver", "gold"],
        "tier_requirements": {"bronze": 1, "silver": 5, "gold": 10}
    }

    mock_user_badge_doc = MagicMock()
    mock_user_badge_doc.exists = False

    # Setup Firestore mocks
    mock_user_badge_ref = setup_firestore_mocks(mock_firestore, mock_badge_def_doc, mock_user_badge_doc)

    # Execute
    activity_data = {"time_spent_minutes": 50}
    earned_badges = gamification_service.check_and_award_badges(
        "test-user-123",
        "test@example.com",
        "study_guide_completed",
        activity_data
    )

    # Verify
    assert "deep_diver" in earned_badges


def test_deep_diver_badge_not_earned_short_time(gamification_service, mock_firestore):
    """Test Deep Diver badge NOT earned for less than 45 minutes."""
    # Execute
    activity_data = {"time_spent_minutes": 30}
    earned_badges = gamification_service.check_and_award_badges(
        "test-user-123",
        "test@example.com",
        "study_guide_completed",
        activity_data
    )

    # Verify
    assert "deep_diver" not in earned_badges


# =============================================================================
# Combo Badge Tests
# =============================================================================

def test_combo_king_badge_earned(gamification_service, mock_firestore):
    """Test Combo King badge earned for 20 flashcards in a row."""
    # Mock badge definition and user badge
    mock_badge_def_doc = MagicMock()
    mock_badge_def_doc.exists = True
    mock_badge_def_doc.to_dict.return_value = {
        "badge_id": "combo_king",
        "name": "Combo King",
        "description": "Flip 20 Flashcards in a row without marking one as incorrect",
        "icon": "🔥",
        "category": "achievement",
        "tiers": ["bronze", "silver", "gold"],
        "tier_requirements": {"bronze": 1, "silver": 5, "gold": 10}
    }

    mock_user_badge_doc = MagicMock()
    mock_user_badge_doc.exists = False

    # Setup Firestore mocks
    mock_user_badge_ref = setup_firestore_mocks(mock_firestore, mock_badge_def_doc, mock_user_badge_doc)

    # Execute
    activity_data = {"consecutive_correct": 25}
    earned_badges = gamification_service.check_and_award_badges(
        "test-user-123",
        "test@example.com",
        "flashcard_set_completed",
        activity_data
    )

    # Verify
    assert "combo_king" in earned_badges


# =============================================================================
# Tier Progression Tests
# =============================================================================

def test_badge_tier_upgrade_bronze_to_silver(gamification_service, mock_firestore):
    """Test badge tier upgrades from bronze to silver."""
    # Mock badge definition
    mock_badge_def_doc = MagicMock()
    mock_badge_def_doc.exists = True
    mock_badge_def_doc.to_dict.return_value = {
        "badge_id": "combo_king",
        "name": "Combo King",
        "description": "Flip 20 Flashcards in a row without marking one as incorrect",
        "icon": "🔥",
        "category": "achievement",
        "tiers": ["bronze", "silver", "gold"],
        "tier_requirements": {"bronze": 1, "silver": 5, "gold": 10}
    }

    # Mock user already has bronze badge with 4 times_earned
    mock_user_badge_doc = MagicMock()
    mock_user_badge_doc.exists = True
    mock_user_badge_doc.to_dict.return_value = {
        "badge_id": "combo_king",
        "tier": "bronze",
        "times_earned": 4
    }

    # Setup Firestore mocks
    mock_user_badge_ref = setup_firestore_mocks(mock_firestore, mock_badge_def_doc, mock_user_badge_doc)

    # Execute - 5th time earning should upgrade to silver
    activity_data = {"consecutive_correct": 25}
    earned_badges = gamification_service.check_and_award_badges(
        "test-user-123",
        "test@example.com",
        "flashcard_set_completed",
        activity_data
    )

    # Verify
    assert "combo_king" in earned_badges  # Badge returned because tier upgraded
    mock_user_badge_ref.update.assert_called_once()
    update_call = mock_user_badge_ref.update.call_args[0][0]
    assert update_call["times_earned"] == 5
    assert update_call["tier"] == "silver"


def test_badge_no_tier_upgrade(gamification_service, mock_firestore):
    """Test badge times_earned increments without tier upgrade."""
    # Mock badge definition
    mock_badge_def_doc = MagicMock()
    mock_badge_def_doc.exists = True
    mock_badge_def_doc.to_dict.return_value = {
        "badge_id": "combo_king",
        "name": "Combo King",
        "description": "Flip 20 Flashcards in a row without marking one as incorrect",
        "icon": "🔥",
        "category": "achievement",
        "tiers": ["bronze", "silver", "gold"],
        "tier_requirements": {"bronze": 1, "silver": 5, "gold": 10}
    }

    # Mock user already has bronze badge with 2 times_earned
    mock_user_badge_doc = MagicMock()
    mock_user_badge_doc.exists = True
    mock_user_badge_doc.to_dict.return_value = {
        "badge_id": "combo_king",
        "tier": "bronze",
        "times_earned": 2
    }

    # Setup Firestore mocks
    mock_user_badge_ref = setup_firestore_mocks(mock_firestore, mock_badge_def_doc, mock_user_badge_doc)

    # Execute - 3rd time earning, still bronze
    activity_data = {"consecutive_correct": 25}
    earned_badges = gamification_service.check_and_award_badges(
        "test-user-123",
        "test@example.com",
        "flashcard_set_completed",
        activity_data
    )

    # Verify
    assert "combo_king" not in earned_badges  # Not returned because no tier upgrade
    mock_user_badge_ref.update.assert_called_once()
    update_call = mock_user_badge_ref.update.call_args[0][0]
    assert update_call["times_earned"] == 3
    assert update_call["tier"] == "bronze"


# =============================================================================
# Sequence Badge Tests
# =============================================================================

def test_hat_trick_badge_earned(gamification_service, mock_firestore):
    """Test Hat Trick badge earned for 3 perfect hard quizzes in a row."""
    # Mock badge definition
    mock_badge_def_doc = MagicMock()
    mock_badge_def_doc.exists = True
    mock_badge_def_doc.to_dict.return_value = {
        "badge_id": "hat_trick",
        "name": "Hat Trick",
        "description": "Pass 3 Hard Quizzes in a row with 100% score",
        "icon": "🎩",
        "category": "achievement",
        "tiers": ["bronze", "silver", "gold"],
        "tier_requirements": {"bronze": 1, "silver": 3, "gold": 5}
    }

    mock_user_badge_doc = MagicMock()
    mock_user_badge_doc.exists = False

    # Mock previous activities - 2 perfect hard quizzes
    mock_activities = [
        UserActivity(
            id="act1",
            user_id="test-user-123",
            user_email="test@example.com",
            activity_type="quiz_completed",
            activity_data={"difficulty": "hard", "score": 10, "total_questions": 10},
            timestamp=datetime.now(timezone.utc) - timedelta(hours=2)
        ),
        UserActivity(
            id="act2",
            user_id="test-user-123",
            user_email="test@example.com",
            activity_type="quiz_completed",
            activity_data={"difficulty": "hard", "score": 5, "total_questions": 5},
            timestamp=datetime.now(timezone.utc) - timedelta(hours=1)
        )
    ]

    # Mock get_user_activities to return previous perfect quizzes
    with patch.object(gamification_service, 'get_user_activities', return_value=(mock_activities, None)):
        # Setup Firestore mocks
        mock_user_badge_ref = setup_firestore_mocks(mock_firestore, mock_badge_def_doc, mock_user_badge_doc)

        # Execute - current quiz is also perfect hard quiz
        activity_data = {"difficulty": "hard", "score": 8, "total_questions": 8}
        earned_badges = gamification_service.check_and_award_badges(
            "test-user-123",
            "test@example.com",
            "quiz_completed",
            activity_data
        )

        # Verify
        assert "hat_trick" in earned_badges


def test_hat_trick_badge_not_earned_not_perfect(gamification_service, mock_firestore):
    """Test Hat Trick badge NOT earned if current quiz not perfect."""
    # Mock previous activities - 2 perfect hard quizzes
    mock_activities = [
        UserActivity(
            id="act1",
            user_id="test-user-123",
            user_email="test@example.com",
            activity_type="quiz_completed",
            activity_data={"difficulty": "hard", "score": 10, "total_questions": 10},
            timestamp=datetime.now(timezone.utc) - timedelta(hours=2)
        ),
        UserActivity(
            id="act2",
            user_id="test-user-123",
            user_email="test@example.com",
            activity_type="quiz_completed",
            activity_data={"difficulty": "hard", "score": 5, "total_questions": 5},
            timestamp=datetime.now(timezone.utc) - timedelta(hours=1)
        )
    ]

    # Mock get_user_activities
    with patch.object(gamification_service, 'get_user_activities', return_value=(mock_activities, None)):
        # Execute - current quiz is NOT perfect
        activity_data = {"difficulty": "hard", "score": 7, "total_questions": 10}
        earned_badges = gamification_service.check_and_award_badges(
            "test-user-123",
            "test@example.com",
            "quiz_completed",
            activity_data
        )

        # Verify
        assert "hat_trick" not in earned_badges


def test_legal_scholar_badge_earned(gamification_service, mock_firestore):
    """Test Legal Scholar badge earned for 3 consecutive high-grade evaluations."""
    # Mock badge definition
    mock_badge_def_doc = MagicMock()
    mock_badge_def_doc.exists = True
    mock_badge_def_doc.to_dict.return_value = {
        "badge_id": "legal_scholar",
        "name": "Legal Scholar",
        "description": "Achieve AI Grade of 9-10 on 3 consecutive Evaluations",
        "icon": "⚖️",
        "category": "achievement",
        "tiers": ["bronze", "silver", "gold"],
        "tier_requirements": {"bronze": 1, "silver": 3, "gold": 5}
    }

    mock_user_badge_doc = MagicMock()
    mock_user_badge_doc.exists = False

    # Mock previous activities - 2 high-grade evaluations
    mock_activities = [
        UserActivity(
            id="act1",
            user_id="test-user-123",
            user_email="test@example.com",
            activity_type="evaluation_completed",
            activity_data={"grade": 10},
            timestamp=datetime.now(timezone.utc) - timedelta(hours=2)
        ),
        UserActivity(
            id="act2",
            user_id="test-user-123",
            user_email="test@example.com",
            activity_type="evaluation_completed",
            activity_data={"grade": 9},
            timestamp=datetime.now(timezone.utc) - timedelta(hours=1)
        )
    ]

    # Mock get_user_activities
    with patch.object(gamification_service, 'get_user_activities', return_value=(mock_activities, None)):
        # Setup Firestore mocks
        mock_user_badge_ref = setup_firestore_mocks(mock_firestore, mock_badge_def_doc, mock_user_badge_doc)

        # Execute - current evaluation is also high grade
        activity_data = {"grade": 10}
        earned_badges = gamification_service.check_and_award_badges(
            "test-user-123",
            "test@example.com",
            "evaluation_completed",
            activity_data
        )

        # Verify
        assert "legal_scholar" in earned_badges


def test_legal_scholar_badge_not_earned_sequence_broken(gamification_service, mock_firestore):
    """Test Legal Scholar badge NOT earned if sequence is broken."""
    # Mock previous activities - 1 high grade, then low grade (sequence broken)
    mock_activities = [
        UserActivity(
            id="act1",
            user_id="test-user-123",
            user_email="test@example.com",
            activity_type="evaluation_completed",
            activity_data={"grade": 10},
            timestamp=datetime.now(timezone.utc) - timedelta(hours=3)
        ),
        UserActivity(
            id="act2",
            user_id="test-user-123",
            user_email="test@example.com",
            activity_type="evaluation_completed",
            activity_data={"grade": 6},  # Low grade breaks sequence
            timestamp=datetime.now(timezone.utc) - timedelta(hours=2)
        ),
        UserActivity(
            id="act3",
            user_id="test-user-123",
            user_email="test@example.com",
            activity_type="evaluation_completed",
            activity_data={"grade": 9},
            timestamp=datetime.now(timezone.utc) - timedelta(hours=1)
        )
    ]

    # Mock get_user_activities
    with patch.object(gamification_service, 'get_user_activities', return_value=(mock_activities, None)):
        # Execute
        activity_data = {"grade": 10}
        earned_badges = gamification_service.check_and_award_badges(
            "test-user-123",
            "test@example.com",
            "evaluation_completed",
            activity_data
        )

        # Verify
        assert "legal_scholar" not in earned_badges


# =============================================================================
# Edge Case Tests
# =============================================================================

def test_check_and_award_badges_no_firestore(gamification_service):
    """Test badge checking fails gracefully without Firestore."""
    gamification_service._db = None

    activity_data = {"difficulty": "hard"}
    earned_badges = gamification_service.check_and_award_badges(
        "test-user-123",
        "test@example.com",
        "quiz_completed",
        activity_data
    )

    assert earned_badges == []


def test_award_badge_definition_not_found(gamification_service, mock_firestore):
    """Test awarding badge fails gracefully if definition not found."""
    # Mock badge definition doesn't exist
    mock_badge_def_doc = MagicMock()
    mock_badge_def_doc.exists = False
    mock_firestore.collection.return_value.document.return_value.get.return_value = mock_badge_def_doc

    # Execute
    result = gamification_service._award_badge(
        "test-user-123",
        "test@example.com",
        "nonexistent_badge"
    )

    # Verify
    assert result is None


"""
Badge Definitions - All badge configurations

This module contains all badge definitions for the gamification system.
Badges are organized into 5 categories:
1. Streak Badges (7)
2. XP Badges (6)
3. Activity Badges (5)
4. Consistency Badges (4)
5. Special Badges (8+)
"""

from datetime import datetime, timezone
from typing import List, Dict, Any

from app.models.gamification_models import BadgeDefinition


def get_all_badge_definitions() -> List[BadgeDefinition]:
    """Get all badge definitions.

    Returns:
        List of all BadgeDefinition objects
    """
    return (
        get_streak_badges() +
        get_xp_badges() +
        get_activity_badges() +
        get_consistency_badges() +
        get_special_badges()
    )


def get_streak_badges() -> List[BadgeDefinition]:
    """Get streak badge definitions (7 badges)."""
    return [
        BadgeDefinition(
            badge_id="ignition",
            name="Ignition",
            description="Start your first streak - complete an activity today!",
            category="streak",
            icon="🔥",
            rarity="common",
            criteria={"streak_days": 1},
            points=10
        ),
        BadgeDefinition(
            badge_id="warming_up",
            name="Warming Up",
            description="Maintain a 7-day streak - you're building momentum!",
            category="streak",
            icon="🔥",
            rarity="common",
            criteria={"streak_days": 7},
            points=25
        ),
        BadgeDefinition(
            badge_id="on_fire",
            name="On Fire",
            description="Maintain a 14-day streak - you're on a roll!",
            category="streak",
            icon="🔥",
            rarity="uncommon",
            criteria={"streak_days": 14},
            points=50
        ),
        BadgeDefinition(
            badge_id="blazing",
            name="Blazing",
            description="Maintain a 30-day streak - incredible dedication!",
            category="streak",
            icon="🔥",
            rarity="rare",
            criteria={"streak_days": 30},
            points=100
        ),
        BadgeDefinition(
            badge_id="inferno",
            name="Inferno",
            description="Maintain a 60-day streak - you're unstoppable!",
            category="streak",
            icon="🔥",
            rarity="epic",
            criteria={"streak_days": 60},
            points=200
        ),
        BadgeDefinition(
            badge_id="eternal_flame",
            name="Eternal Flame",
            description="Maintain a 90-day streak - legendary commitment!",
            category="streak",
            icon="🔥",
            rarity="legendary",
            criteria={"streak_days": 90},
            points=500
        ),
        BadgeDefinition(
            badge_id="phoenix",
            name="Phoenix",
            description="Rise from the ashes - rebuild a streak after breaking a 30+ day streak",
            category="streak",
            icon="🔥",
            rarity="epic",
            criteria={"rebuild_after": 30},
            points=150
        ),
    ]


def get_xp_badges() -> List[BadgeDefinition]:
    """Get XP badge definitions (6 badges)."""
    return [
        BadgeDefinition(
            badge_id="novice",
            name="Novice",
            description="Reach 500 XP - you're just getting started!",
            category="xp",
            icon="⭐",
            rarity="common",
            criteria={"total_xp": 500},
            points=10
        ),
        BadgeDefinition(
            badge_id="apprentice",
            name="Apprentice",
            description="Reach 1,000 XP - you're learning fast!",
            category="xp",
            icon="⭐",
            rarity="common",
            criteria={"total_xp": 1000},
            points=25
        ),
        BadgeDefinition(
            badge_id="practitioner",
            name="Practitioner",
            description="Reach 2,500 XP - you're becoming skilled!",
            category="xp",
            icon="⭐",
            rarity="uncommon",
            criteria={"total_xp": 2500},
            points=50
        ),
        BadgeDefinition(
            badge_id="expert",
            name="Expert",
            description="Reach 5,000 XP - you're highly proficient!",
            category="xp",
            icon="⭐",
            rarity="rare",
            criteria={"total_xp": 5000},
            points=100
        ),
        BadgeDefinition(
            badge_id="master",
            name="Master",
            description="Reach 10,000 XP - you've mastered the material!",
            category="xp",
            icon="⭐",
            rarity="epic",
            criteria={"total_xp": 10000},
            points=200
        ),
        BadgeDefinition(
            badge_id="grandmaster",
            name="Grandmaster",
            description="Reach 25,000 XP - you're a true expert!",
            category="xp",
            icon="⭐",
            rarity="legendary",
            criteria={"total_xp": 25000},
            points=500
        ),
    ]


def get_activity_badges() -> List[BadgeDefinition]:
    """Get activity badge definitions (5 badges)."""
    return [
        BadgeDefinition(
            badge_id="flashcard_fanatic",
            name="Flashcard Fanatic",
            description="Complete 100 flashcard sets - you love those cards!",
            category="activity",
            icon="📇",
            rarity="rare",
            criteria={"flashcard_sets": 100},
            points=100
        ),
        BadgeDefinition(
            badge_id="quiz_master",
            name="Quiz Master",
            description="Pass 50 quizzes - you're a testing champion!",
            category="activity",
            icon="📝",
            rarity="rare",
            criteria={"quizzes_passed": 50},
            points=100
        ),
        BadgeDefinition(
            badge_id="evaluation_expert",
            name="Evaluation Expert",
            description="Complete 25 evaluations - you're analytical!",
            category="activity",
            icon="⚖️",
            rarity="uncommon",
            criteria={"evaluations": 25},
            points=75
        ),
        BadgeDefinition(
            badge_id="study_guide_scholar",
            name="Study Guide Scholar",
            description="Complete 25 study guides - you're thorough!",
            category="activity",
            icon="📖",
            rarity="uncommon",
            criteria={"study_guides": 25},
            points=75
        ),
        BadgeDefinition(
            badge_id="well_rounded",
            name="Well-Rounded",
            description="Complete at least 10 of each activity type - balanced learning!",
            category="activity",
            icon="🎯",
            rarity="epic",
            criteria={
                "flashcard_sets": 10,
                "quizzes_passed": 10,
                "evaluations": 10,
                "study_guides": 10
            },
            points=150
        ),
    ]


def get_consistency_badges() -> List[BadgeDefinition]:
    """Get consistency badge definitions (4 badges)."""
    return [
        BadgeDefinition(
            badge_id="consistent_learner",
            name="Consistent Learner",
            description="Earn weekly bonus 4 weeks in a row - you're building habits!",
            category="consistency",
            icon="🏆",
            rarity="uncommon",
            criteria={"consecutive_weeks_bonus": 4},
            points=50
        ),
        BadgeDefinition(
            badge_id="dedication",
            name="Dedication",
            description="Earn weekly bonus 8 weeks in a row - impressive commitment!",
            category="consistency",
            icon="🏆",
            rarity="rare",
            criteria={"consecutive_weeks_bonus": 8},
            points=100
        ),
        BadgeDefinition(
            badge_id="commitment",
            name="Commitment",
            description="Earn weekly bonus 12 weeks in a row - you're dedicated!",
            category="consistency",
            icon="🏆",
            rarity="epic",
            criteria={"consecutive_weeks_bonus": 12},
            points=200
        ),
        BadgeDefinition(
            badge_id="unstoppable",
            name="Unstoppable",
            description="Earn weekly bonus 26 weeks in a row - half a year of consistency!",
            category="consistency",
            icon="🏆",
            rarity="legendary",
            criteria={"consecutive_weeks_bonus": 26},
            points=500
        ),
    ]


def get_special_badges() -> List[BadgeDefinition]:
    """Get special badge definitions (8+ badges)."""
    return [
        BadgeDefinition(
            badge_id="early_adopter",
            name="Early Adopter",
            description="Join during the beta period - you're a pioneer!",
            category="special",
            icon="🌟",
            rarity="rare",
            criteria={"joined_before": "2026-03-01T00:00:00+00:00"},
            points=100
        ),
        BadgeDefinition(
            badge_id="perfect_week",
            name="Perfect Week",
            description="Complete all 4 categories every day for a week - flawless!",
            category="special",
            icon="🌟",
            rarity="epic",
            criteria={"perfect_week": True},
            points=200
        ),
        BadgeDefinition(
            badge_id="night_owl",
            name="Night Owl",
            description="Complete activities after midnight 10 times - burning the midnight oil!",
            category="special",
            icon="🦉",
            rarity="uncommon",
            criteria={"night_activities": 10},
            points=50
        ),
        BadgeDefinition(
            badge_id="early_bird",
            name="Early Bird",
            description="Complete activities before 6 AM 10 times - rise and shine!",
            category="special",
            icon="☀️",
            rarity="uncommon",
            criteria={"early_activities": 10},
            points=50
        ),
        BadgeDefinition(
            badge_id="weekend_warrior",
            name="Weekend Warrior",
            description="Maintain streak through 10 weekends - no days off!",
            category="special",
            icon="🌟",
            rarity="rare",
            criteria={"weekend_streaks": 10},
            points=100
        ),
        BadgeDefinition(
            badge_id="combo_king",
            name="Combo King",
            description="Get 20 flashcards correct in a row - perfect streak!",
            category="special",
            icon="👑",
            rarity="rare",
            criteria={"flashcard_combo": 20},
            points=100
        ),
        BadgeDefinition(
            badge_id="deep_diver",
            name="Deep Diver",
            description="Complete 50+ flashcards in one session - intense focus!",
            category="special",
            icon="🤿",
            rarity="uncommon",
            criteria={"flashcards_one_session": 50},
            points=75
        ),
        BadgeDefinition(
            badge_id="hat_trick",
            name="Hat Trick",
            description="Pass 3 hard quizzes in a row with 90%+ - exceptional!",
            category="special",
            icon="🎩",
            rarity="epic",
            criteria={"hard_quiz_streak": 3, "min_score": 90},
            points=150
        ),
        BadgeDefinition(
            badge_id="legal_scholar",
            name="Legal Scholar",
            description="Complete 5 high-complexity evaluations in a row - mastery!",
            category="special",
            icon="⚖️",
            rarity="epic",
            criteria={"high_complexity_evaluations": 5},
            points=150
        ),
    ]


def seed_badge_definitions(db) -> int:
    """Seed all badge definitions to Firestore.

    Args:
        db: Firestore client

    Returns:
        Number of badges seeded
    """
    badges = get_all_badge_definitions()
    count = 0

    for badge in badges:
        try:
            db.collection("badge_definitions").document(badge.badge_id).set(
                badge.model_dump(mode='json')
            )
            count += 1
        except Exception as e:
            print(f"Error seeding badge {badge.badge_id}: {e}")

    return count


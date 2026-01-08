"""Gamification Models.

Provides data models for the gamification system including user stats,
activities, sessions, and badges.

Firestore structure:
- user_stats/{user_id}
- user_activities/{activity_id}
- user_sessions/{session_id}
- badge_definitions/{badge_id}
- user_achievements/{user_id}/badges/{badge_id}
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


# =============================================================================
# User Stats Models
# =============================================================================

class StreakInfo(BaseModel):
    """Streak tracking information."""

    current_count: int = Field(default=0, description="Current streak count in days")
    longest_streak: int = Field(default=0, description="Longest streak ever achieved")
    last_activity_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last activity timestamp"
    )
    last_activity_day: str = Field(
        default="",
        description="Last activity day (YYYY-MM-DD) for 4AM reset logic"
    )
    freezes_available: int = Field(default=0, description="Number of streak freezes available")
    next_reset: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Next 4AM reset time"
    )
    weekly_consistency: Dict[str, bool] = Field(
        default_factory=lambda: {
            "flashcards": False,
            "quiz": False,
            "evaluation": False,
            "guide": False
        },
        description="Weekly consistency tracking for bonus"
    )
    week_start: Optional[str] = Field(
        default=None,
        description="Start of current week (ISO format) for consistency tracking"
    )
    bonus_active: bool = Field(
        default=False,
        description="Whether weekly consistency bonus is active"
    )
    bonus_multiplier: float = Field(
        default=1.0,
        ge=1.0,  # Must be >= 1.0
        le=2.0,  # Must be <= 2.0 (max 100% bonus)
        description="XP multiplier when bonus is active (1.0-2.0)"
    )


class ActivityCounters(BaseModel):
    """Activity counters for user stats."""
    
    flashcards_reviewed: int = Field(default=0, description="Total flashcards reviewed")
    quizzes_completed: int = Field(default=0, description="Total quizzes completed")
    quizzes_passed: int = Field(default=0, description="Total quizzes passed")
    evaluations_submitted: int = Field(default=0, description="Total evaluations submitted")
    guides_completed: int = Field(default=0, description="Total study guides completed")
    total_study_time_minutes: int = Field(default=0, description="Total study time in minutes")


class Week7Quest(BaseModel):
    """Week 7 Boss Prep Quest tracking."""
    
    active: bool = Field(default=False, description="Whether Week 7 mode is active")
    exam_readiness_percent: int = Field(default=0, ge=0, le=100, description="Exam readiness percentage")
    boss_battle_completed: bool = Field(default=False, description="Whether boss battle was completed")
    double_xp_earned: int = Field(default=0, description="Total double XP earned during Week 7")


class UserStats(BaseModel):
    """Core gamification statistics per user.
    
    Stored in Firestore: user_stats/{user_id}
    """
    
    user_id: str = Field(..., description="User's IAP user ID")
    user_email: str = Field(..., description="User's email address")
    course_id: Optional[str] = Field(None, description="Current active course ID")
    
    # XP & Levels
    total_xp: int = Field(default=0, ge=0, description="Total XP earned")
    current_level: int = Field(default=1, ge=1, description="Current level")
    level_title: str = Field(default="Junior Clerk", description="Current level title")
    xp_to_next_level: int = Field(default=100, ge=0, description="XP needed for next level")
    
    # Streaks
    streak: StreakInfo = Field(default_factory=StreakInfo, description="Streak information")
    
    # Activity Counters
    activities: ActivityCounters = Field(
        default_factory=ActivityCounters,
        description="Activity counters"
    )
    
    # Week 7 Quest
    week7_quest: Week7Quest = Field(
        default_factory=Week7Quest,
        description="Week 7 quest tracking"
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When stats were created"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When stats were last updated"
    )
    last_active: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last activity timestamp"
    )


# =============================================================================
# Activity Models
# =============================================================================

class UserActivity(BaseModel):
    """Detailed activity log for user interactions.
    
    Stored in Firestore: user_activities/{activity_id}
    """
    
    id: str = Field(..., description="Unique activity ID")
    user_id: str = Field(..., description="User's IAP user ID")
    user_email: str = Field(..., description="User's email address")
    course_id: Optional[str] = Field(None, description="Course ID if applicable")
    
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When activity occurred"
    )
    
    activity_type: str = Field(
        ...,
        description="Type of activity: quiz_completed, flashcard_reviewed, guide_viewed, etc."
    )
    activity_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Type-specific activity data"
    )
    
    session_id: Optional[str] = Field(None, description="Session ID this activity belongs to")
    xp_awarded: int = Field(default=0, ge=0, description="XP awarded for this activity")
    streak_maintained: bool = Field(default=False, description="Whether streak was maintained")
    badges_earned: List[str] = Field(default_factory=list, description="Badge IDs earned from this activity")
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (browser, device, time_of_day, etc.)"
    )


# =============================================================================
# Session Models
# =============================================================================

class PageView(BaseModel):
    """Page view within a session."""

    page: str = Field(..., description="Page name (dashboard, quiz, etc.)")
    active_seconds: int = Field(default=0, ge=0, description="Active time on this page")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When page was viewed"
    )


class UserSession(BaseModel):
    """Time-on-site tracking per session.

    Stored in Firestore: user_sessions/{session_id}
    """

    session_id: str = Field(..., description="Unique session ID")
    user_id: str = Field(..., description="User's IAP user ID")
    course_id: Optional[str] = Field(None, description="Course ID if applicable")

    start_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Session start time"
    )
    end_time: Optional[datetime] = Field(None, description="Session end time")

    active_time_seconds: int = Field(default=0, ge=0, description="Total active time in seconds")
    idle_time_seconds: int = Field(default=0, ge=0, description="Total idle time in seconds")
    total_time_seconds: int = Field(default=0, ge=0, description="Total session time in seconds")

    page_views: List[PageView] = Field(default_factory=list, description="Page views in this session")
    activities_count: int = Field(default=0, ge=0, description="Number of activities in session")
    xp_earned: int = Field(default=0, ge=0, description="Total XP earned in session")


# =============================================================================
# Badge Models
# =============================================================================

class BadgeDefinition(BaseModel):
    """Master list of all available badges.

    Stored in Firestore: badge_definitions/{badge_id}
    """

    badge_id: str = Field(..., description="Unique badge ID")
    name: str = Field(..., description="Badge name")
    description: str = Field(..., description="Badge description")
    icon: str = Field(..., description="Badge icon (emoji or URL)")

    category: str = Field(
        ...,
        description="Badge category: behavioral, achievement, milestone"
    )

    tiers: List[str] = Field(
        default_factory=lambda: ["bronze", "silver", "gold"],
        description="Available tiers"
    )
    tier_requirements: Dict[str, int] = Field(
        default_factory=lambda: {"bronze": 1, "silver": 5, "gold": 10},
        description="Times earned required for each tier"
    )

    active: bool = Field(default=True, description="Whether badge is active")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When badge was created"
    )


class UserBadge(BaseModel):
    """User-earned badge.

    Stored in Firestore: user_achievements/{user_id}/badges/{badge_id}
    """

    badge_id: str = Field(..., description="Badge ID")
    badge_name: str = Field(..., description="Badge name")
    badge_description: str = Field(..., description="Badge description")
    badge_icon: str = Field(..., description="Badge icon")

    tier: str = Field(default="bronze", description="Current tier: bronze, silver, gold")
    earned_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When badge was first earned"
    )
    times_earned: int = Field(default=1, ge=1, description="Number of times earned")
    course_id: Optional[str] = Field(None, description="Course ID if applicable")


# =============================================================================
# Request/Response Models
# =============================================================================

class ActivityLogRequest(BaseModel):
    """Request to log a user activity."""

    activity_type: str = Field(..., description="Type of activity")
    activity_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Activity-specific data"
    )
    course_id: Optional[str] = Field(None, description="Course ID if applicable")


class ActivityLogResponse(BaseModel):
    """Response from logging an activity."""

    activity_id: str = Field(..., description="Created activity ID")
    xp_awarded: int = Field(..., description="XP awarded")
    new_total_xp: int = Field(..., description="New total XP")
    level_up: bool = Field(..., description="Whether user leveled up")
    new_level: Optional[int] = Field(None, description="New level if leveled up")
    new_level_title: Optional[str] = Field(None, description="New level title if leveled up")
    streak_maintained: bool = Field(..., description="Whether streak was maintained")
    new_streak_count: Optional[int] = Field(None, description="New streak count")
    freeze_used: Optional[bool] = Field(None, description="Whether a streak freeze was used")
    badges_earned: List[str] = Field(default_factory=list, description="Badge IDs earned")


class SessionStartResponse(BaseModel):
    """Response from starting a session."""

    session_id: str = Field(..., description="Created session ID")
    start_time: datetime = Field(..., description="Session start time")


class SessionHeartbeatRequest(BaseModel):
    """Request to update session heartbeat."""

    session_id: str = Field(..., description="Session ID")
    active_seconds: int = Field(..., ge=0, description="Active seconds since last heartbeat")
    current_page: str = Field(..., description="Current page name")


class UserStatsResponse(BaseModel):
    """Response with user gamification stats."""

    total_xp: int = Field(..., description="Total XP")
    current_level: int = Field(..., description="Current level")
    level_title: str = Field(..., description="Level title")
    xp_to_next_level: int = Field(..., description="XP to next level")

    streak: Dict[str, Any] = Field(..., description="Streak information")
    activities: Dict[str, int] = Field(..., description="Activity counters")
    week7_quest: Optional[Dict[str, Any]] = Field(None, description="Week 7 quest info if active")


# =============================================================================
# XP Configuration Models
# =============================================================================

class XPConfig(BaseModel):
    """XP configuration for activities.

    Stored in Firestore: xp_config/default
    """

    flashcard_set_completed: int = Field(5, ge=0, description="XP per 10 cards reviewed correctly")
    study_guide_completed: int = Field(15, ge=0, description="XP per study guide completion")
    quiz_easy_passed: int = Field(10, ge=0, description="XP for passing easy quiz")
    quiz_hard_passed: int = Field(25, ge=0, description="XP for passing hard quiz")
    evaluation_low: int = Field(20, ge=0, description="XP for AI evaluation grade 1-6")
    evaluation_high: int = Field(50, ge=0, description="XP for AI evaluation grade 7-10")

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When config was last updated"
    )
    updated_by: Optional[str] = Field(None, description="User who updated the config")


class XPConfigResponse(BaseModel):
    """Response with XP configuration."""

    flashcard_set_completed: int
    study_guide_completed: int
    quiz_easy_passed: int
    quiz_hard_passed: int
    evaluation_low: int
    evaluation_high: int
    updated_at: datetime
    updated_by: Optional[str]


class XPConfigUpdateRequest(BaseModel):
    """Request to update XP configuration."""

    flashcard_set_completed: Optional[int] = Field(None, ge=0)
    study_guide_completed: Optional[int] = Field(None, ge=0)
    quiz_easy_passed: Optional[int] = Field(None, ge=0)
    quiz_hard_passed: Optional[int] = Field(None, ge=0)
    evaluation_low: Optional[int] = Field(None, ge=0)
    evaluation_high: Optional[int] = Field(None, ge=0)


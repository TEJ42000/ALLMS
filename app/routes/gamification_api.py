"""
Gamification API Routes
Handles achievements, badges, and user stats
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging

from app.services.gcp_service import get_firestore_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gamification", tags=["Gamification"])


class UserStatsUpdate(BaseModel):
    """User stats update request"""
    achievements: List[str]
    total_points: int
    quiz_questions_answered: int
    quiz_questions_correct: int
    flashcards_mastered: int
    current_streak: int
    last_activity_date: Optional[str] = None
    daily_logins: int


@router.get("/stats")
async def get_user_stats(request: Request):
    """
    Get user gamification stats

    Returns:
        User stats including achievements, points, streaks
    """
    try:
        user = getattr(request.state, 'user', None)
        if not user or not hasattr(user, 'email'):
            raise HTTPException(status_code=401, detail="Not authenticated")

        user_email = user.email
        
        db = get_firestore_client()
        
        # Get user stats document
        user_ref = db.collection("users").document(user_email)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            # Create default stats
            default_stats = {
                "achievements": [],
                "total_points": 0,
                "quiz_questions_answered": 0,
                "quiz_questions_correct": 0,
                "flashcards_mastered": 0,
                "current_streak": 0,
                "last_activity_date": None,
                "daily_logins": 0,
                "created_at": datetime.utcnow().isoformat()
            }
            user_ref.set(default_stats)
            return default_stats
        
        user_data = user_doc.to_dict()
        
        return {
            "achievements": user_data.get("achievements", []),
            "total_points": user_data.get("total_points", 0),
            "quiz_questions_answered": user_data.get("quiz_questions_answered", 0),
            "quiz_questions_correct": user_data.get("quiz_questions_correct", 0),
            "flashcards_mastered": user_data.get("flashcards_mastered", 0),
            "current_streak": user_data.get("current_streak", 0),
            "last_activity_date": user_data.get("last_activity_date"),
            "daily_logins": user_data.get("daily_logins", 0)
        }
        
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stats")
async def update_user_stats(request: Request, stats: UserStatsUpdate):
    """
    Update user gamification stats

    Args:
        stats: Updated user stats

    Returns:
        Success message
    """
    try:
        user = getattr(request.state, 'user', None)
        if not user or not hasattr(user, 'email'):
            raise HTTPException(status_code=401, detail="Not authenticated")

        user_email = user.email
        
        db = get_firestore_client()
        
        # Update user stats document
        user_ref = db.collection("users").document(user_email)
        
        update_data = {
            "achievements": stats.achievements,
            "total_points": stats.total_points,
            "quiz_questions_answered": stats.quiz_questions_answered,
            "quiz_questions_correct": stats.quiz_questions_correct,
            "flashcards_mastered": stats.flashcards_mastered,
            "current_streak": stats.current_streak,
            "last_activity_date": stats.last_activity_date,
            "daily_logins": stats.daily_logins,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        user_ref.set(update_data, merge=True)
        
        logger.info(f"Updated stats for user {user_email}")
        
        return {"status": "success", "message": "Stats updated"}
        
    except Exception as e:
        logger.error(f"Error updating user stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leaderboard")
async def get_leaderboard(request: Request, limit: int = 10):
    """
    Get top users by points

    Args:
        limit: Number of users to return

    Returns:
        List of top users with points
    """
    try:
        user = getattr(request.state, 'user', None)
        if not user or not hasattr(user, 'email'):
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        db = get_firestore_client()
        
        # Query top users by total_points
        users_ref = db.collection("users")
        query = users_ref.order_by("total_points", direction="DESCENDING").limit(limit)
        
        leaderboard = []
        for doc in query.stream():
            user_data = doc.to_dict()
            leaderboard.append({
                "email": doc.id,
                "total_points": user_data.get("total_points", 0),
                "achievements_count": len(user_data.get("achievements", [])),
                "current_streak": user_data.get("current_streak", 0)
            })
        
        return {"leaderboard": leaderboard}
        
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


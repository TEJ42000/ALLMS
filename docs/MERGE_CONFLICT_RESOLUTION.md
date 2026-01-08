# Merge Conflict Resolution Guide

**Date:** 2026-01-08  
**Branches:** feature/phase5-week7-boss-quest → main  
**File:** app/routes/gamification.py

---

## Conflict Overview

When merging the Week 7 Quest feature branch into main, there's a conflict at the end of `app/routes/gamification.py` where both branches added new endpoints.

---

## Conflict Details

**Location:** End of `app/routes/gamification.py` (around line 454)

**Feature Branch (Week 7 Quest):** Added 3 new quest endpoints
**Main Branch:** Added `seed_all_badges` endpoint (renamed from `seed_badges`)

---

## Resolution Strategy

**Keep BOTH sets of endpoints** - They serve different purposes and don't conflict functionally.

---

## Step-by-Step Resolution

### Step 1: Start the Merge

```bash
git checkout feature/phase5-week7-boss-quest
git merge main
```

This will trigger the conflict.

---

### Step 2: Locate the Conflict

Open `app/routes/gamification.py` and find the conflict markers:

```python
<<<<<<< feature/phase5-week7-boss-quest
# Week 7 Quest endpoints...
=======
# seed_all_badges endpoint...
>>>>>>> main
```

---

### Step 3: Resolve the Conflict

**Replace the entire conflict section with BOTH endpoints:**

```python
# =============================================================================
# Week 7 Quest Endpoints
# =============================================================================

@router.post("/quest/week7/activate")
def activate_week7_quest(
    current_week: int = Query(..., ge=1, le=13, description="Current week number"),
    course_id: str = Query(..., description="Course ID"),
    user: User = Depends(get_current_user)
):
    """Activate Week 7 Boss Quest for current user.
    
    HIGH: Added API endpoint to activate quest
    
    Args:
        current_week: Current week number (1-13)
        course_id: Course ID
        user: Current authenticated user
        
    Returns:
        Activation status and message
        
    Raises:
        HTTPException: If activation fails
    """
    try:
        from app.services.week7_quest_service import get_week7_quest_service
        
        quest_service = get_week7_quest_service()
        activated, message = quest_service.check_and_activate_quest(
            user_id=user.user_id,
            course_id=course_id,
            current_week=current_week
        )
        
        if not activated and message:
            raise HTTPException(400, detail=message)
        
        logger.info(f"Week 7 quest activation attempt for user {user.user_id[:8]}... - Result: {activated}")
        return {"status": "activated" if activated else "not_activated", "message": message}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating Week 7 quest: {e}", exc_info=True)
        raise HTTPException(500, detail=str(e)) from e


@router.get("/quest/week7/progress")
def get_week7_quest_progress(
    user: User = Depends(get_current_user)
):
    """Get detailed Week 7 quest progress for current user.
    
    HIGH: Added API endpoint to get quest progress
    
    Args:
        user: Current authenticated user
        
    Returns:
        Quest progress including exam readiness, double XP earned, etc.
        
    Raises:
        HTTPException: If retrieval fails
    """
    try:
        from app.services.gamification_service import get_gamification_service
        
        service = get_gamification_service()
        stats = service.get_or_create_user_stats(
            user_id=user.user_id,
            user_email=user.email,
            course_id=None  # Will use existing course_id from stats
        )
        
        if not stats:
            raise HTTPException(404, detail="User stats not found")
        
        return {
            "active": stats.week7_quest.active,
            "course_id": stats.week7_quest.course_id,
            "exam_readiness_percent": stats.week7_quest.exam_readiness_percent,
            "boss_battle_completed": stats.week7_quest.boss_battle_completed,
            "double_xp_earned": stats.week7_quest.double_xp_earned
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Week 7 quest progress: {e}", exc_info=True)
        raise HTTPException(500, detail=str(e)) from e


@router.get("/quest/week7/requirements")
def get_week7_quest_requirements():
    """Get Week 7 quest requirements and thresholds.
    
    HIGH: Added API endpoint to get quest requirements
    
    Returns:
        Quest requirements including exam readiness thresholds
    """
    try:
        from app.services.week7_quest_service import get_week7_quest_service
        
        quest_service = get_week7_quest_service()
        return quest_service.get_quest_requirements()
        
    except Exception as e:
        logger.error(f"Error getting Week 7 quest requirements: {e}", exc_info=True)
        raise HTTPException(500, detail=str(e)) from e


@router.post("/badges/seed")
def seed_all_badges(
    user: User = Depends(get_current_user)
):
    """Seed all badge definitions (admin only).
    
    CRITICAL: Function renamed from seed_badges to seed_all_badges to avoid duplicate
    
    Returns:
        Number of badges seeded
    """
    # Admin check
    admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")
    admin_emails = [email.strip() for email in admin_emails if email.strip()]
    
    if not admin_emails:
        logger.error("ADMIN_EMAILS not configured")
        raise HTTPException(403, detail="Admin configuration required")
    
    if user.email not in admin_emails:
        logger.warning(f"Non-admin {user.email} attempted to seed badges")
        raise HTTPException(403, detail="Admin access required")
    
    try:
        from app.services.badge_definitions import seed_badge_definitions
        from app.services.gcp_service import get_firestore_client
        
        db = get_firestore_client()
        count = seed_badge_definitions(db)
        
        logger.info(f"Badges seeded by {user.email}: {count} badges")
        return {
            "status": "ok",
            "badges_seeded": count,
            "message": f"Successfully seeded {count} badge definitions"
        }
        
    except Exception as e:
        logger.error(f"Error seeding badges: {e}")
        raise HTTPException(500, detail=str(e)) from e
```

---

### Step 4: Remove Conflict Markers

Make sure to remove ALL conflict markers:
- `<<<<<<< feature/phase5-week7-boss-quest`
- `=======`
- `>>>>>>> main`

---

### Step 5: Verify the Resolution

Check that the file has:
1. ✅ Week 7 Quest endpoints (3 endpoints)
2. ✅ Badge seeding endpoint (1 endpoint)
3. ✅ No conflict markers
4. ✅ Proper formatting and indentation

---

### Step 6: Mark as Resolved

```bash
git add app/routes/gamification.py
```

---

### Step 7: Complete the Merge

```bash
git commit -m "Merge main into feature/phase5-week7-boss-quest

Resolved conflict in app/routes/gamification.py by keeping both:
- Week 7 Quest endpoints (3 endpoints)
- Badge seeding endpoint (seed_all_badges)

Both sets of endpoints serve different purposes and are compatible."
```

---

## Verification Checklist

After resolving the conflict, verify:

- [ ] File has no conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`)
- [ ] All 4 endpoints are present and complete
- [ ] Proper indentation and formatting
- [ ] No syntax errors (`python -m py_compile app/routes/gamification.py`)
- [ ] All imports are present
- [ ] Docstrings are complete

---

## Testing After Merge

Run these tests to ensure everything works:

```bash
# Check Python syntax
python -m py_compile app/routes/gamification.py

# Run tests
pytest tests/test_week7_quest_service.py -v

# Start server and test endpoints
# POST /api/gamification/quest/week7/activate
# GET /api/gamification/quest/week7/progress
# GET /api/gamification/quest/week7/requirements
# POST /api/gamification/badges/seed
```

---

## Alternative: Use Git Mergetool

If you prefer a visual merge tool:

```bash
git mergetool
```

This will open your configured merge tool (e.g., VS Code, Meld, KDiff3) to resolve the conflict visually.

---

## Rollback if Needed

If something goes wrong:

```bash
# Abort the merge
git merge --abort

# Or reset to before merge
git reset --hard HEAD
```

---

## Summary

**Conflict Type:** Both branches added new endpoints at the same location  
**Resolution:** Keep BOTH sets of endpoints  
**Result:** 4 total endpoints (3 quest + 1 badge seeding)  
**Compatibility:** No functional conflicts, endpoints serve different purposes

---

**Last Updated:** 2026-01-08  
**Status:** Ready for merge resolution


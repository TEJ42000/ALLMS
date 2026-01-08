# Badge Criteria Schema Documentation

**Date:** 2026-01-08  
**Version:** 1.0  
**Status:** Official schema for Phase 4 Badge System

---

## Overview

This document defines the official schema for badge criteria in the gamification system. All badge definitions must conform to this schema.

---

## Badge Definition Model

```python
class BadgeDefinition(BaseModel):
    badge_id: str              # Unique identifier (lowercase, alphanumeric, underscores)
    name: str                  # Display name
    description: str           # User-facing description
    category: str              # Badge category (see Categories section)
    icon: str                  # Emoji or icon character
    rarity: str                # Rarity level (see Rarity Levels section)
    criteria: Dict[str, Any]   # Criteria for earning (see Criteria Types section)
    points: int                # Points awarded when earned
    active: bool = True        # Whether badge is active (default: True)
```

---

## Categories

### Valid Categories

| Category | Description | Example Badges |
|----------|-------------|----------------|
| `xp` | Total XP milestones | Novice, Expert, Master |
| `streak` | Consecutive day streaks | On Fire, Blazing, Inferno |
| `activity` | Activity completion counts | Flashcard Fanatic, Quiz Master |
| `consistency` | Long-term consistency | Consistent Learner, Dedication |
| `special` | Special achievements | Early Adopter, Perfect Week |

---

## Rarity Levels

### Valid Rarity Values

| Rarity | Description | Points Range | Color |
|--------|-------------|--------------|-------|
| `common` | Easy to earn | 10-25 | Gray |
| `uncommon` | Moderate difficulty | 50-75 | Green |
| `rare` | Challenging | 100-150 | Blue |
| `epic` | Very challenging | 200-300 | Purple |
| `legendary` | Extremely rare | 500+ | Gold |

---

## Criteria Types

### 1. XP Criteria

**Purpose:** Badges earned by reaching total XP milestones

**Schema:**
```json
{
  "total_xp": <integer>
}
```

**Example:**
```json
{
  "badge_id": "novice",
  "name": "Novice",
  "category": "xp",
  "criteria": {
    "total_xp": 500
  },
  "points": 10
}
```

**Field Mapping:**
- `total_xp` → `UserStats.total_xp`

**Validation:**
- `total_xp` must be positive integer
- Recommended increments: 500, 1000, 2500, 5000, 10000, 25000

---

### 2. Streak Criteria

**Purpose:** Badges earned by maintaining consecutive day streaks

**Schema:**
```json
{
  "streak_days": <integer>
}
```

**Example:**
```json
{
  "badge_id": "on_fire",
  "name": "On Fire",
  "category": "streak",
  "criteria": {
    "streak_days": 14
  },
  "points": 50
}
```

**Field Mapping:**
- `streak_days` → `UserStats.streak.current_count`

**Validation:**
- `streak_days` must be positive integer
- Recommended milestones: 1, 7, 14, 30, 60, 90

---

### 3. Streak Rebuild Criteria

**Purpose:** Special badge for rebuilding a lost streak

**Schema:**
```json
{
  "rebuild_after_days": <integer>
}
```

**Example:**
```json
{
  "badge_id": "phoenix",
  "name": "Phoenix",
  "category": "streak",
  "criteria": {
    "rebuild_after_days": 30
  },
  "points": 100
}
```

**Field Mapping:**
- `rebuild_after_days` → Custom logic in streak service

**Validation:**
- `rebuild_after_days` must be positive integer
- Typically set to 30 or higher

---

### 4. Activity Criteria

**Purpose:** Badges earned by completing specific activities

**Schema:**
```json
{
  "flashcard_sets": <integer>,     // Optional
  "quizzes_passed": <integer>,     // Optional
  "evaluations": <integer>,        // Optional
  "study_guides": <integer>        // Optional
}
```

**Single Activity Example:**
```json
{
  "badge_id": "flashcard_fanatic",
  "name": "Flashcard Fanatic",
  "category": "activity",
  "criteria": {
    "flashcard_sets": 100
  },
  "points": 100
}
```

**Multiple Activities Example (Well-Rounded):**
```json
{
  "badge_id": "well_rounded",
  "name": "Well-Rounded",
  "category": "activity",
  "criteria": {
    "flashcard_sets": 10,
    "quizzes_passed": 10,
    "evaluations": 10,
    "study_guides": 10
  },
  "points": 150
}
```

**Field Mapping:**
- `flashcard_sets` → `UserStats.activities.flashcards_reviewed`
- `quizzes_passed` → `UserStats.activities.quizzes_passed`
- `evaluations` → `UserStats.activities.evaluations_submitted`
- `study_guides` → `UserStats.activities.guides_completed`

**Validation:**
- All values must be positive integers
- Multiple criteria use AND logic (all must be met)
- Recommended increments: 10, 25, 50, 100

---

### 5. Consistency Criteria

**Purpose:** Badges for long-term consistency (weekly bonuses)

**Schema:**
```json
{
  "consecutive_weeks_bonus": <integer>
}
```

**Example:**
```json
{
  "badge_id": "consistent_learner",
  "name": "Consistent Learner",
  "category": "consistency",
  "criteria": {
    "consecutive_weeks_bonus": 4
  },
  "points": 50
}
```

**Field Mapping:**
- `consecutive_weeks_bonus` → Custom tracking (not yet implemented)

**Status:** ⚠️ INACTIVE - Requires weekly bonus tracking implementation

**Validation:**
- `consecutive_weeks_bonus` must be positive integer
- Recommended milestones: 4, 8, 12, 26

---

### 6. Special Criteria

**Purpose:** Unique badges with special conditions

#### 6.1 Early Adopter

**Schema:**
```json
{
  "joined_before": "<ISO 8601 datetime>"
}
```

**Example:**
```json
{
  "badge_id": "early_adopter",
  "name": "Early Adopter",
  "category": "special",
  "criteria": {
    "joined_before": "2026-03-01T00:00:00+00:00"
  },
  "points": 100
}
```

**Field Mapping:**
- `joined_before` → `UserStats.created_at`

**Validation:**
- Must be valid ISO 8601 datetime string
- Must include timezone (UTC recommended)

#### 6.2 Other Special Criteria (Not Yet Implemented)

**Perfect Week:**
```json
{
  "perfect_week": true
}
```
- Status: ⚠️ INACTIVE - Requires daily completion tracking

**Night Owl / Early Bird:**
```json
{
  "night_activities": <integer>,
  "early_activities": <integer>
}
```
- Status: ⚠️ INACTIVE - Requires activity timestamp tracking

**Combo King:**
```json
{
  "flashcard_combo": <integer>
}
```
- Status: ⚠️ INACTIVE - Requires combo tracking

---

## Criteria Validation Rules

### General Rules

1. **Required Fields:**
   - All badge definitions must have `criteria` object
   - Criteria must not be empty
   - All criteria values must be valid for their type

2. **Type Validation:**
   - Integer criteria: Must be positive integers
   - Datetime criteria: Must be valid ISO 8601 strings
   - Boolean criteria: Must be true/false

3. **Logical Validation:**
   - Multiple criteria in same badge use AND logic
   - All criteria must be met to earn badge
   - Criteria should be achievable

### Category-Specific Rules

**XP Badges:**
- Must have exactly one criterion: `total_xp`
- Value should increase progressively

**Streak Badges:**
- Must have `streak_days` OR `rebuild_after_days`
- Cannot have both in same badge

**Activity Badges:**
- Must have at least one activity criterion
- Can have multiple criteria (AND logic)
- All values should be achievable

**Special Badges:**
- Can have custom criteria
- Must be documented if new type added

---

## Progress Calculation

### How Progress is Calculated

**Formula:**
```
percentage = min(100, (current / required) * 100)
```

**Example:**
```python
# User has 250 XP, badge requires 500 XP
current = 250
required = 500
percentage = min(100, (250 / 500) * 100) = 50%
```

### Progress Response Format

```json
{
  "current": <integer>,
  "required": <integer>,
  "percentage": <integer>
}
```

---

## Examples

### Complete Badge Definition Examples

**1. XP Badge:**
```json
{
  "badge_id": "expert",
  "name": "Expert",
  "description": "Reach 5,000 XP - you're becoming an expert!",
  "category": "xp",
  "icon": "⭐",
  "rarity": "rare",
  "criteria": {
    "total_xp": 5000
  },
  "points": 100,
  "active": true
}
```

**2. Streak Badge:**
```json
{
  "badge_id": "blazing",
  "name": "Blazing",
  "description": "Maintain a 30-day streak - you're on fire!",
  "category": "streak",
  "icon": "🔥",
  "rarity": "rare",
  "criteria": {
    "streak_days": 30
  },
  "points": 100,
  "active": true
}
```

**3. Activity Badge:**
```json
{
  "badge_id": "quiz_master",
  "name": "Quiz Master",
  "description": "Pass 50 quizzes - you're a testing pro!",
  "category": "activity",
  "icon": "📝",
  "rarity": "rare",
  "criteria": {
    "quizzes_passed": 50
  },
  "points": 100,
  "active": true
}
```

**4. Multi-Criteria Badge:**
```json
{
  "badge_id": "well_rounded",
  "name": "Well-Rounded",
  "description": "Complete 10 of each activity type - balanced learning!",
  "category": "activity",
  "icon": "🎯",
  "rarity": "epic",
  "criteria": {
    "flashcard_sets": 10,
    "quizzes_passed": 10,
    "evaluations": 10,
    "study_guides": 10
  },
  "points": 200,
  "active": true
}
```

---

## Adding New Criteria Types

### Process for Adding New Criteria

1. **Define Schema:**
   - Document new criteria type
   - Specify field names and types
   - Define validation rules

2. **Update Badge Service:**
   - Add criteria checking logic
   - Add progress calculation logic
   - Add field mapping

3. **Update Documentation:**
   - Add to this schema document
   - Update examples
   - Document field mapping

4. **Add Tests:**
   - Unit tests for criteria checking
   - Integration tests for badge unlocking
   - Progress calculation tests

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-08 | Initial schema documentation |

---

**Last Updated:** 2026-01-08  
**Maintained By:** Development Team


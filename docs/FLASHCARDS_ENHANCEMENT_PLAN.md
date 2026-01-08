# Flashcards UI Enhancement Plan

**Issue:** #158  
**Branch:** `feature/flashcards-ui-enhancements`  
**Priority:** HIGH

---

## Current Implementation Status

### ✅ Already Implemented (Phase 1 Complete)

#### 1. Core Flashcard Display
- ✅ Card front (question/term)
- ✅ Card back (answer/definition)
- ✅ 3D flip animation
- ✅ Card counter ("Card 5 of 20")
- ✅ Progress indicator
- ✅ Shuffle option

#### 2. Navigation Controls
- ✅ "Previous" button
- ✅ "Next" button
- ✅ "Flip" button/click to flip
- ✅ Keyboard shortcuts (arrow keys, spacebar, Enter)
- ✅ Swipe gestures (mobile)
- ✅ "Restart" option

#### 3. Study Modes
- ✅ **Study Mode** - Review all cards
- ✅ **Quiz Mode** - Self-assessment (know/don't know)
- ✅ **Shuffle Mode** - Random order
- ✅ **Starred Mode** - Review flagged cards only
- ❌ **Spaced Repetition** - NOT YET IMPLEMENTED

#### 4. Card Actions
- ✅ Star/flag card for review
- ✅ Mark as "known" or "unknown"
- ❌ Add notes to card - NOT YET IMPLEMENTED
- ❌ Report issue with card - NOT YET IMPLEMENTED
- ❌ Share card - NOT YET IMPLEMENTED

#### 5. Progress Tracking
- ✅ Cards reviewed count
- ✅ Cards remaining count
- ✅ Accuracy percentage
- ❌ Time spent - NOT YET IMPLEMENTED
- ❌ XP earned display - NOT YET IMPLEMENTED
- ❌ Streak contribution indicator - NOT YET IMPLEMENTED

#### 6. Animations & Interactions
- ✅ Smooth flip animation (3D CSS)
- ✅ Slide transitions between cards
- ✅ Hover effects
- ✅ Loading states
- ✅ Success animations (completion message)

#### 7. Accessibility
- ✅ ARIA labels for all controls
- ✅ Keyboard navigation (Tab, Enter, Space, Arrows)
- ✅ Screen reader support
- ✅ Focus indicators
- ✅ High contrast mode support

#### 8. Mobile Responsiveness
- ✅ Touch-friendly card size
- ✅ Swipe to flip
- ✅ Swipe to navigate
- ✅ Responsive layout
- ✅ Optimized for portrait and landscape

---

## Phase 2: Missing Features to Implement

### Priority 1: Gamification Integration (HIGH)

#### 1.1 XP Tracking
- [ ] Display XP earned per card
- [ ] Show total XP for session
- [ ] Animate XP gains
- [ ] Integrate with backend XP API

#### 1.2 Streak Integration
- [ ] Show current streak
- [ ] Indicate streak contribution
- [ ] Warn before breaking streak
- [ ] Celebrate streak milestones

### Priority 2: Enhanced Features (MEDIUM)

#### 2.1 Time Tracking
- [ ] Track time per card
- [ ] Track total session time
- [ ] Display average time per card
- [ ] Show time remaining estimate

#### 2.2 Card Notes
- [ ] Add note button on each card
- [ ] Note input modal
- [ ] Display notes on card
- [ ] Persist notes to backend
- [ ] Edit/delete notes

#### 2.3 Report Issue
- [ ] Report button on each card
- [ ] Issue type selection (typo, incorrect, unclear)
- [ ] Comment field
- [ ] Submit to backend
- [ ] Confirmation message

### Priority 3: Social Features (LOW)

#### 3.1 Share Card
- [ ] Share button
- [ ] Copy link to clipboard
- [ ] Share via social media
- [ ] Generate shareable image

### Priority 4: Spaced Repetition (MEDIUM)

#### 4.1 Algorithm Implementation
- [ ] SM-2 algorithm (SuperMemo 2)
- [ ] Track card difficulty
- [ ] Calculate next review date
- [ ] Schedule cards for review
- [ ] Filter by due cards

#### 4.2 Review Scheduling
- [ ] Show cards due today
- [ ] Show upcoming reviews
- [ ] Adjust difficulty based on performance
- [ ] Persist schedule to backend

---

## Implementation Plan

### Phase 2A: Gamification (Week 1)
**Estimated:** 2-3 days

1. **XP Integration**
   - Add XP display to flashcard viewer
   - Integrate with `/api/gamification/xp` endpoint
   - Add XP animation on card completion
   - Update completion screen with total XP

2. **Streak Integration**
   - Add streak display to header
   - Integrate with `/api/gamification/streak` endpoint
   - Add streak contribution indicator
   - Warn before session abandonment

### Phase 2B: Enhanced Features (Week 1-2)
**Estimated:** 2-3 days

1. **Time Tracking**
   - Add timer to flashcard viewer
   - Track time per card
   - Display session statistics
   - Add to completion screen

2. **Card Notes**
   - Add notes button to card actions
   - Create notes modal component
   - Implement notes CRUD operations
   - Add backend API endpoints

3. **Report Issue**
   - Add report button to card actions
   - Create report modal component
   - Implement issue submission
   - Add backend API endpoint

### Phase 2C: Spaced Repetition (Week 2)
**Estimated:** 3-4 days

1. **Algorithm Implementation**
   - Implement SM-2 algorithm
   - Add difficulty tracking
   - Calculate review intervals
   - Add review scheduling

2. **Backend Integration**
   - Create review schedule API
   - Persist card performance
   - Track review history
   - Filter by due cards

---

## API Endpoints Needed

### Existing Endpoints
- ✅ `POST /api/files/flashcards` - Generate flashcards
- ✅ `GET /api/gamification/xp` - Get user XP
- ✅ `GET /api/gamification/streak` - Get user streak

### New Endpoints Required

#### Progress Tracking
```
POST /api/flashcards/progress
GET /api/flashcards/progress/{user_id}
```

#### Notes
```
POST /api/flashcards/{card_id}/notes
GET /api/flashcards/{card_id}/notes
PUT /api/flashcards/notes/{note_id}
DELETE /api/flashcards/notes/{note_id}
```

#### Issue Reporting
```
POST /api/flashcards/{card_id}/report
```

#### Spaced Repetition
```
GET /api/flashcards/due
POST /api/flashcards/{card_id}/review
GET /api/flashcards/schedule
```

---

## Files to Modify

### JavaScript
- `app/static/js/flashcard-viewer.js` - Add new features
- `app/static/js/flashcard-page.js` - Add gamification integration

### CSS
- `app/static/css/flashcard-viewer.css` - Add new styles
- `app/static/css/flashcard-page.css` - Add gamification styles

### Backend
- `app/routes/flashcards.py` - NEW FILE - Flashcard API routes
- `app/models/flashcard_models.py` - NEW FILE - Flashcard data models
- `app/services/spaced_repetition.py` - NEW FILE - SR algorithm

### Templates
- `templates/flashcards.html` - Add gamification elements

---

## Success Criteria

### Phase 2A (Gamification)
- [ ] XP displayed and updated correctly
- [ ] Streak displayed and tracked
- [ ] XP animations smooth and engaging
- [ ] Backend integration working

### Phase 2B (Enhanced Features)
- [ ] Time tracking accurate
- [ ] Notes can be added/edited/deleted
- [ ] Issues can be reported
- [ ] All features persist to backend

### Phase 2C (Spaced Repetition)
- [ ] SM-2 algorithm implemented correctly
- [ ] Review scheduling working
- [ ] Due cards filtered properly
- [ ] Performance tracked accurately

---

## Testing Plan

### Unit Tests
- [ ] Test XP calculation
- [ ] Test streak tracking
- [ ] Test time tracking
- [ ] Test SM-2 algorithm
- [ ] Test notes CRUD
- [ ] Test issue reporting

### Integration Tests
- [ ] Test backend API integration
- [ ] Test progress persistence
- [ ] Test review scheduling
- [ ] Test gamification integration

### E2E Tests
- [ ] Test complete study session
- [ ] Test spaced repetition flow
- [ ] Test notes workflow
- [ ] Test issue reporting workflow

---

## Next Steps

1. ✅ Create enhancement plan (this document)
2. [ ] Implement Phase 2A: Gamification
3. [ ] Implement Phase 2B: Enhanced Features
4. [ ] Implement Phase 2C: Spaced Repetition
5. [ ] Write tests
6. [ ] Update documentation
7. [ ] Create PR

---

**Status:** Planning Complete - Ready for Implementation


# Phase 2: Card Actions Enhancement - Implementation Plan

**Issue:** #158  
**PR:** TBD  
**Branch:** `feature/flashcards-ui-phase-2-card-actions`  
**Base:** `main` (includes merged PR #235 - Quiz Mode)  
**Status:** 🚧 In Progress

---

## Overview

Phase 2 focuses on enhancing card actions with backend integration for:
1. **Notes Feature** - Add/edit/delete notes on individual flashcards
2. **Report Issue** - Allow users to report problems with flashcards
3. **Share Card** - Share individual flashcards (optional)

### Current Status

**Frontend (Already Implemented):**
- ✅ Notes button UI (`btn-notes`)
- ✅ Report button UI (`btn-report`)
- ✅ `showNotesDialog()` method (lines 1526-1550)
- ✅ `showReportDialog()` method (lines 1555-1577)
- ✅ `cardNotes` Map for local storage (line 97)

**Backend (Needs Implementation):**
- ❌ API endpoints for notes CRUD
- ❌ API endpoint for issue reporting
- ❌ Database models for notes and issues
- ❌ Persistence layer integration

---

## Implementation Tasks

### Task 1: Backend API - Notes CRUD

**Files to Create:**
- `app/routes/flashcard_notes.py` - Notes API endpoints
- `app/models/flashcard_models.py` - Flashcard note models

**Endpoints:**
```python
POST   /api/flashcards/notes              # Create note
GET    /api/flashcards/notes/{card_id}    # Get note for card
PUT    /api/flashcards/notes/{note_id}    # Update note
DELETE /api/flashcards/notes/{note_id}    # Delete note
GET    /api/flashcards/notes              # Get all user notes
```

**Data Model:**
```python
class FlashcardNote(BaseModel):
    id: str
    user_id: str
    card_id: str  # Unique identifier for the flashcard
    set_id: str   # Flashcard set identifier
    note_text: str
    created_at: datetime
    updated_at: datetime
```

**Firestore Structure:**
```
users/{user_id}/flashcard_notes/{note_id}
{
    "card_id": "card_123",
    "set_id": "set_456",
    "note_text": "Remember: This is important for exam",
    "created_at": "2026-01-09T10:00:00Z",
    "updated_at": "2026-01-09T10:00:00Z"
}
```

---

### Task 2: Backend API - Issue Reporting

**Files to Create:**
- `app/routes/flashcard_issues.py` - Issue reporting endpoints

**Endpoints:**
```python
POST   /api/flashcards/issues             # Report issue
GET    /api/flashcards/issues             # Get all issues (admin)
GET    /api/flashcards/issues/{issue_id}  # Get specific issue
PATCH  /api/flashcards/issues/{issue_id}  # Update issue status (admin)
```

**Data Model:**
```python
class FlashcardIssue(BaseModel):
    id: str
    user_id: str
    card_id: str
    set_id: str
    issue_type: str  # 'incorrect', 'typo', 'unclear', 'other'
    description: str
    status: str  # 'open', 'in_review', 'resolved', 'closed'
    created_at: datetime
    resolved_at: Optional[datetime]
    admin_notes: Optional[str]
```

**Firestore Structure:**
```
flashcard_issues/{issue_id}
{
    "user_id": "user_123",
    "card_id": "card_456",
    "set_id": "set_789",
    "issue_type": "typo",
    "description": "The answer has a spelling mistake",
    "status": "open",
    "created_at": "2026-01-09T10:00:00Z"
}
```

---

### Task 3: Frontend Integration

**Files to Modify:**
- `app/static/js/flashcard-viewer.js`

**Changes Needed:**

1. **Update `showNotesDialog()` to persist to backend:**
```javascript
async showNotesDialog() {
    const currentNote = this.cardNotes.get(this.currentIndex) || '';
    const cardId = this.getCardId(this.currentIndex);
    
    // Fetch existing note from backend
    const existingNote = await this.fetchNote(cardId);
    
    this.showConfirm(
        'Card Notes',
        `<textarea id="card-note-input" rows="5">${this.escapeHtml(existingNote || '')}</textarea>`,
        async (confirmed) => {
            if (confirmed) {
                const noteText = document.getElementById('card-note-input').value.trim();
                
                if (noteText) {
                    await this.saveNote(cardId, noteText);
                    this.cardNotes.set(this.currentIndex, noteText);
                } else {
                    await this.deleteNote(cardId);
                    this.cardNotes.delete(this.currentIndex);
                }
                
                this.render();
            }
        }
    );
}
```

2. **Update `showReportDialog()` to submit to backend:**
```javascript
async showReportDialog() {
    this.showConfirm(
        'Report Issue',
        `<p>Report an issue with this flashcard:</p>
         <select id="issue-type">
             <option value="incorrect">Incorrect Answer</option>
             <option value="typo">Typo/Spelling</option>
             <option value="unclear">Unclear Question</option>
             <option value="other">Other</option>
         </select>
         <textarea id="report-issue-input" rows="4" placeholder="Describe the issue..."></textarea>`,
        async (confirmed) => {
            if (confirmed) {
                const issueType = document.getElementById('issue-type').value;
                const description = document.getElementById('report-issue-input').value.trim();
                
                if (description) {
                    await this.submitIssue(this.getCardId(this.currentIndex), issueType, description);
                    this.showSuccess('Thank you! Your report has been submitted.');
                }
            }
        }
    );
}
```

3. **Add API helper methods:**
```javascript
async fetchNote(cardId) {
    try {
        const response = await fetch(`/api/flashcards/notes/${cardId}`);
        if (response.ok) {
            const data = await response.json();
            return data.note_text;
        }
    } catch (error) {
        console.error('[FlashcardViewer] Failed to fetch note:', error);
    }
    return null;
}

async saveNote(cardId, noteText) {
    try {
        const response = await fetch('/api/flashcards/notes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                card_id: cardId,
                set_id: this.setId,
                note_text: noteText
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to save note');
        }
    } catch (error) {
        console.error('[FlashcardViewer] Failed to save note:', error);
        this.showError('Failed to save note. Please try again.');
    }
}

async deleteNote(cardId) {
    try {
        const response = await fetch(`/api/flashcards/notes/${cardId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error('Failed to delete note');
        }
    } catch (error) {
        console.error('[FlashcardViewer] Failed to delete note:', error);
    }
}

async submitIssue(cardId, issueType, description) {
    try {
        const response = await fetch('/api/flashcards/issues', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                card_id: cardId,
                set_id: this.setId,
                issue_type: issueType,
                description: description
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to submit issue');
        }
    } catch (error) {
        console.error('[FlashcardViewer] Failed to submit issue:', error);
        this.showError('Failed to submit report. Please try again.');
    }
}

getCardId(index) {
    // Generate unique card ID based on content hash or use provided ID
    const card = this.flashcards[index];
    return card.id || `card_${btoa(card.question).substring(0, 16)}`;
}
```

---

### Task 4: Constructor Enhancement

**Add setId parameter:**
```javascript
constructor(containerId, flashcards, options = {}) {
    // ... existing code ...
    
    this.setId = options.setId || 'default';  // NEW: Track flashcard set ID
    
    // ... rest of constructor ...
}
```

---

### Task 5: Testing

**Unit Tests:**
- Test note CRUD operations
- Test issue submission
- Test error handling
- Test input validation

**Integration Tests:**
- Test API endpoints with authentication
- Test Firestore persistence
- Test concurrent note updates

**E2E Tests:**
- Test notes dialog workflow
- Test report dialog workflow
- Test note persistence across sessions

---

## Files to Create/Modify

### New Files:
1. `app/routes/flashcard_notes.py` (+150 lines)
2. `app/routes/flashcard_issues.py` (+100 lines)
3. `app/models/flashcard_models.py` (+80 lines)
4. `tests/test_flashcard_notes.py` (+200 lines)
5. `tests/test_flashcard_issues.py` (+150 lines)

### Modified Files:
1. `app/static/js/flashcard-viewer.js` (+120 lines)
2. `app/main.py` (+2 lines - register routers)
3. `docs/API.md` (+50 lines - document new endpoints)

---

## Success Criteria

- ✅ Notes can be created, read, updated, and deleted
- ✅ Notes persist across sessions
- ✅ Issues can be reported with type and description
- ✅ All API endpoints have proper authentication
- ✅ Input validation prevents XSS and injection
- ✅ Error handling provides user-friendly messages
- ✅ All tests pass (unit, integration, E2E)
- ✅ Documentation is complete
- ✅ Backward compatible with existing features

---

## Timeline

**Estimated:** 2-3 days

- Day 1: Backend API implementation (Tasks 1-2)
- Day 2: Frontend integration (Tasks 3-4)
- Day 3: Testing and documentation (Task 5)

---

**Status:** Ready to begin implementation  
**Next Step:** Implement Task 1 - Backend API for Notes CRUD


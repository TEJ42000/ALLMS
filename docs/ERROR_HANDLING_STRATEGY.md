# Error Handling Strategy - Flashcard Viewer

## Overview

This document defines the **consistent error handling strategy** used throughout the FlashcardViewer component, specifically for defensive checks in `reviewStarredCards()` and `restoreFullDeck()` methods.

## Core Principles

### 1. **Fail Fast for Critical Errors**
Critical errors indicate data corruption or missing essential data that prevents the operation from completing safely. These errors should:
- Stop execution immediately
- Log detailed error information
- Show user-friendly error message
- Suggest user action (usually "refresh the page")

### 2. **Recover Gracefully for Minor Issues**
Minor issues are problems that can be worked around without compromising data integrity. These should:
- Log warning information
- Attempt automatic recovery
- Continue execution if possible
- Notify user if data was filtered/modified

### 3. **Always Log for Debugging**
All error paths should:
- Use consistent log prefixes (`[FlashcardViewer]`)
- Include severity level (`CRITICAL`, `RECOVERY`)
- Provide context (variable values, state)
- Help developers diagnose issues

### 4. **Always Show User-Friendly Messages**
All user-facing messages should:
- Be clear and actionable
- Avoid technical jargon
- Suggest next steps
- Use consistent tone

---

## Error Categories

### Critical Errors (Fail Fast)

**Definition:** Errors that prevent safe operation and indicate data corruption.

**Examples:**
- `originalFlashcards` is null or undefined
- `originalFlashcards` is not an array
- `originalFlashcards` is empty
- All Sets are missing (in `restoreFullDeck()`)
- No valid cards after filtering
- All cards are null/undefined

**Handling:**
```javascript
// CRITICAL ERROR: originalFlashcards is null/undefined (fail fast)
if (!this.originalFlashcards || !Array.isArray(this.originalFlashcards)) {
    console.error('[FlashcardViewer] CRITICAL: originalFlashcards is not properly initialized:', this.originalFlashcards);
    this.showError('Unable to review starred cards. Please refresh the page.');
    return;
}
```

**User Messages:**
- "Unable to review starred cards. Please refresh the page."
- "No flashcards available to review. Please refresh the page."
- "Unable to restore full deck. Please refresh the page."
- "No valid starred cards found. Please refresh the page."

---

### Minor Issues (Recover Gracefully)

**Definition:** Issues that can be worked around without compromising data integrity.

**Examples:**
- Individual Set is null/undefined (create new Set)
- Invalid index types (filter out)
- Out-of-bounds indices (filter out)
- Individual null/undefined cards (filter out)

**Handling:**
```javascript
// MINOR ISSUE: Individual Set corruption (recover gracefully)
if (!this.originalReviewedCards || !(this.originalReviewedCards instanceof Set)) {
    console.warn('[FlashcardViewer] RECOVERY: originalReviewedCards is not a Set, creating new Set');
    this.originalReviewedCards = new Set();
}

// MINOR ISSUE: Invalid indices (filter out)
const validIndices = starredIndices.filter(index => {
    if (typeof index !== 'number') {
        console.warn('[FlashcardViewer] RECOVERY: Invalid index type:', typeof index, index);
        return false;
    }
    return true;
});
```

**User Messages:**
- Warning notification when cards are filtered
- No message if recovery is transparent

---

### Informational (No Error)

**Definition:** Expected conditions that don't indicate errors.

**Examples:**
- No starred cards to review
- Not in filtered view

**Handling:**
```javascript
// Early return if not in filtered view (not an error)
if (!this.isFilteredView) {
    console.log('[FlashcardViewer] Not in filtered view, nothing to restore');
    return;
}
```

---

## Consistency Rules

### 1. Log Prefixes

**Format:** `[FlashcardViewer] SEVERITY: Message`

**Severity Levels:**
- `CRITICAL:` - Critical errors (fail fast)
- `RECOVERY:` - Minor issues (recover gracefully)
- No prefix - Informational

**Examples:**
```javascript
console.error('[FlashcardViewer] CRITICAL: originalFlashcards is empty');
console.warn('[FlashcardViewer] RECOVERY: Invalid index type:', typeof index, index);
console.log('[FlashcardViewer] Not in filtered view, nothing to restore');
```

### 2. Error Messages

**Critical Errors:**
- Always end with "Please refresh the page."
- Use `this.showError()`
- Be specific about what failed

**Minor Issues:**
- Use warning notifications when data is filtered
- Use `showNotification()` with fallback to `this.showError()`
- Include counts of filtered/valid items

### 3. Return Behavior

**Critical Errors:**
```javascript
if (criticalError) {
    console.error('[FlashcardViewer] CRITICAL: ...');
    this.showError('...');
    return; // Stop execution
}
```

**Minor Issues:**
```javascript
if (minorIssue) {
    console.warn('[FlashcardViewer] RECOVERY: ...');
    // Recover and continue
}
```

---

## Method-Specific Strategies

### reviewStarredCards()

**Critical Errors (Fail Fast):**
1. No starred cards
2. originalFlashcards is null/undefined/not array
3. originalFlashcards is empty
4. No valid indices after filtering
5. All cards are null/undefined

**Minor Issues (Recover):**
1. Invalid index types → filter out
2. Out-of-bounds indices → filter out
3. Individual null/undefined cards → filter out and warn

### restoreFullDeck()

**Critical Errors (Fail Fast):**
1. originalFlashcards is null/undefined/not array
2. originalFlashcards is empty
3. All Sets are missing

**Minor Issues (Recover):**
1. Individual Set is null/undefined → create new Set
2. Individual Set is not a Set → create new Set

---

## Runtime Error Prevention

### showNotification Safety

**Problem:** `showNotification()` might not be defined if utils.js fails to load.

**Solution:** Always check before calling:
```javascript
if (typeof showNotification === 'function') {
    showNotification(message, 'warning', 5000);
} else {
    // Fallback to showError
    this.showError(message);
}
```

---

## Testing Strategy

### E2E Tests (Playwright)
- Test critical error paths in real browser
- Verify error messages display correctly
- Test corrupted localStorage scenarios
- Verify console logging

### Unit Tests (Jest)
- Test error detection logic
- Test recovery mechanisms
- Test edge cases
- Mock dependencies

---

## Examples

### Complete Error Handling Flow

```javascript
reviewStarredCards() {
    // CRITICAL ERROR: No starred cards (fail fast)
    if (this.starredCards.size === 0) {
        console.warn('[FlashcardViewer] No starred cards to review');
        this.showError('No starred cards to review!');
        return;
    }

    // Store original data
    if (!this.isFilteredView) {
        this.originalFlashcards = [...this.flashcards];
        // ...
    }

    // CRITICAL ERROR: originalFlashcards invalid (fail fast)
    if (!this.originalFlashcards || !Array.isArray(this.originalFlashcards)) {
        console.error('[FlashcardViewer] CRITICAL: originalFlashcards is not properly initialized');
        this.showError('Unable to review starred cards. Please refresh the page.');
        return;
    }

    // MINOR ISSUE: Invalid indices (recover gracefully)
    const validIndices = starredIndices.filter(index => {
        if (typeof index !== 'number') {
            console.warn('[FlashcardViewer] RECOVERY: Invalid index type:', typeof index);
            return false;
        }
        return true;
    });

    // CRITICAL ERROR: No valid indices (fail fast)
    if (validIndices.length === 0) {
        console.error('[FlashcardViewer] CRITICAL: No valid starred card indices found');
        this.showError('No valid starred cards found. Please refresh the page.');
        return;
    }

    // MINOR ISSUE: Null cards (recover gracefully and warn)
    const validCards = starredCards.filter(card => card !== null);
    const filteredCount = starredIndices.length - validCards.length;
    
    if (filteredCount > 0) {
        console.warn(`[FlashcardViewer] RECOVERY: ${filteredCount} cards filtered out`);
        if (typeof showNotification === 'function') {
            showNotification(`${filteredCount} cards filtered out`, 'warning', 5000);
        }
    }

    // Continue with valid cards
    this.flashcards = validCards;
    // ...
}
```

---

## Benefits

✅ **Predictable:** Same pattern across all methods  
✅ **Debuggable:** Consistent logging with severity levels  
✅ **User-Friendly:** Clear error messages with actions  
✅ **Robust:** Handles both critical and minor issues  
✅ **Safe:** Prevents runtime errors (showNotification check)  
✅ **Testable:** Clear error paths for testing  

---

## Maintenance

When adding new defensive checks:

1. **Identify severity:** Is this critical or minor?
2. **Choose strategy:** Fail fast or recover gracefully?
3. **Add logging:** Use consistent prefix and severity
4. **Add user message:** Clear and actionable
5. **Add tests:** E2E and unit tests
6. **Document:** Update this file if needed


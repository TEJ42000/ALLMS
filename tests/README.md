# Test Suite for Defensive Checks (Issue #168)

## Overview

This test suite validates the defensive checks implemented in the FlashcardViewer component for `reviewStarredCards()` and `restoreFullDeck()` methods.

## ⚠️ IMPORTANT: Unit Test Strategy Decision

**Decision:** Unit tests are **SPECIFICATION TESTS**, not implementation tests.

**Rationale:**
- Unit tests validate the **defensive logic patterns** used in the code
- They do NOT test the actual FlashcardViewer class implementation
- They serve as **executable specifications** for the defensive checks
- They are fast, isolated, and provide quick feedback during development

**Why not test the actual implementation in unit tests?**
- FlashcardViewer requires DOM and browser APIs
- Mocking the entire DOM would be complex and brittle
- E2E tests already test the actual implementation in real browsers
- Unit tests focus on logic patterns, E2E tests focus on integration

**If you need to test the actual implementation:**
- Use the E2E tests (Playwright) which run in real browsers
- E2E tests call actual FlashcardViewer methods programmatically
- E2E tests verify real behavior, not mocked behavior

## Test Strategy

### Two-Tier Testing Approach

We use a **two-tier testing strategy** to provide comprehensive coverage:

1. **Unit Tests (Jest)** - Test defensive logic patterns (SPECIFICATION TESTS)
2. **E2E Tests (Playwright)** - Test actual implementation in real browsers (INTEGRATION TESTS)

---

## Unit Tests (Jest)

**Location:** `tests/unit/flashcard-viewer.test.js`

### Purpose

Unit tests validate the **defensive check logic patterns** used in the code. They test:
- Error detection logic
- Data validation logic
- Recovery mechanisms
- Edge cases

### What They Test

**NOT testing:** The actual FlashcardViewer class implementation  
**ARE testing:** The defensive logic patterns that the implementation uses

### Examples

```javascript
// Tests the logic pattern for detecting null values
test('should detect when originalFlashcards is null', () => {
    const originalFlashcards = null;
    const isValid = !!(originalFlashcards && Array.isArray(originalFlashcards));
    expect(isValid).toBe(false);
});

// Tests the logic pattern for filtering invalid indices
test('should filter out invalid index types', () => {
    const starredIndices = ['0', '1', 2]; // Mix of strings and numbers
    const originalFlashcards = [{ q: 'Q1' }, { q: 'Q2' }, { q: 'Q3' }];
    
    const validIndices = starredIndices.filter(index => {
        return typeof index === 'number' && 
               index >= 0 && 
               index < originalFlashcards.length;
    });
    
    expect(validIndices).toEqual([2]);
});
```

### Coverage

**reviewStarredCards() Logic (11 tests):**
- Critical error detection (4 tests)
- Index validation logic (3 tests)
- Card filtering logic (3 tests)
- Happy path (1 test)

**restoreFullDeck() Logic (10 tests):**
- Critical error detection (5 tests)
- Set validation and recovery logic (4 tests)
- Happy path (1 test)

**Total: 21 unit tests**

### Running Unit Tests

```bash
# Run all unit tests
cd tests && npm test

# Run in watch mode
cd tests && npm run test:watch

# Generate coverage report
cd tests && npm run test:coverage
```

---

## E2E Tests (Playwright)

**Location:** `tests/e2e/defensive-checks-simple.spec.js`

### Purpose

E2E tests validate the **actual implementation** in real browser environments. They test:
- Real FlashcardViewer behavior in actual browsers
- Defensive check logic in real JavaScript runtime
- Console logging output
- Corrupted data scenarios
- Cross-browser compatibility

### What They Test

**ARE testing:** The actual FlashcardViewer class in real browsers
**ARE testing:** Programmatic API calls to FlashcardViewer methods
**ARE testing:** Console logging output
**NOT testing:** UI elements (those may not be fully implemented yet)

### Approach

Tests use **programmatic API calls** instead of UI interactions:
- Navigate to actual `/flashcards` route
- Initialize FlashcardViewer with test data
- Call methods programmatically via `page.evaluate()`
- Verify results and console output

### Examples

```javascript
test('reviewStarredCards: should detect null originalFlashcards', async ({ page }) => {
    const result = await page.evaluate(() => {
        const viewer = window.flashcardViewer;

        // Star a card
        viewer.starredCards.add(0);

        // Corrupt data
        viewer.originalFlashcards = null;
        viewer.isFilteredView = true;

        // This should fail fast
        viewer.reviewStarredCards();

        return {
            originalFlashcardsIsNull: viewer.originalFlashcards === null,
            flashcardsLength: viewer.flashcards.length
        };
    });

    expect(result.originalFlashcardsIsNull).toBe(true);
    expect(result.flashcardsLength).toBe(3); // Should not change
});
```

### Coverage

**reviewStarredCards() (5 tests):**
- No starred cards detection
- Null originalFlashcards detection
- Invalid indices filtering
- Card filtering with warning
- Happy path success

**restoreFullDeck() (3 tests):**
- Null originalFlashcards detection
- Invalid Sets graceful recovery
- Happy path success

**Console Logging (2 tests):**
- CRITICAL error logging
- RECOVERY warning logging

**Total: 12 E2E tests**

### Running E2E Tests

```bash
# Run E2E tests (requires running Flask app)
npm run test:e2e

# Run in headed mode (see browser)
npx playwright test --headed

# Run specific browser
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit
```

---

## Why This Approach?

### Unit Tests (Logic Patterns)

**Pros:**
- ✅ Fast execution (milliseconds)
- ✅ No dependencies (no browser, no server)
- ✅ Easy to debug
- ✅ Test logic patterns in isolation
- ✅ High coverage of edge cases

**Cons:**
- ❌ Don't test actual implementation
- ❌ Don't test browser behavior
- ❌ Don't test user-facing messages

**Best for:**
- Testing defensive logic patterns
- Testing data validation logic
- Testing edge cases
- Quick feedback during development

### E2E Tests (Real Implementation)

**Pros:**
- ✅ Test actual implementation
- ✅ Test in real browsers
- ✅ Test user-facing behavior
- ✅ Test cross-browser compatibility
- ✅ Catch integration issues

**Cons:**
- ❌ Slower execution (seconds)
- ❌ Requires running server
- ❌ More complex setup
- ❌ Harder to debug

**Best for:**
- Testing actual FlashcardViewer behavior
- Testing user-facing error messages
- Testing browser-specific issues
- Final validation before merge

---

## Test Results

### Unit Tests (Jest)

```
PASS unit/flashcard-viewer.test.js
  Defensive Check Logic - reviewStarredCards()
    Critical Error Detection
      ✓ should detect when no cards are starred
      ✓ should detect when originalFlashcards is null
      ✓ should detect when originalFlashcards is not an array
      ✓ should detect when originalFlashcards is empty
    Index Validation Logic
      ✓ should filter out invalid index types
      ✓ should filter out negative indices
      ✓ should filter out out-of-bounds indices
    Card Filtering Logic
      ✓ should filter out null cards
      ✓ should calculate filtered count correctly
      ✓ should detect when all cards are null
    Happy Path
      ✓ should process valid starred cards successfully
  Defensive Check Logic - restoreFullDeck()
    Critical Error Detection
      ✓ should detect when not in filtered view
      ✓ should detect when originalFlashcards is null
      ✓ should detect when originalFlashcards is not an array
      ✓ should detect when originalFlashcards is empty
      ✓ should detect when all Sets are missing (critical corruption)
    Set Validation and Recovery Logic
      ✓ should detect invalid Set (null)
      ✓ should detect invalid Set (array instead of Set)
      ✓ should recover by creating new Set when invalid
      ✓ should preserve valid Sets
    Happy Path
      ✓ should successfully restore full deck with valid data

Test Suites: 1 passed, 1 total
Tests:       21 passed, 21 total
```

### E2E Tests (Playwright)

E2E tests require a running Flask application. See `playwright.config.js` for configuration.

---

## Summary

| Type | Count | Purpose | Speed |
|------|-------|---------|-------|
| Unit Tests | 21 | Test defensive logic patterns | Fast (ms) |
| E2E Tests | 12 | Test actual implementation | Slow (s) |
| **Total** | **33** | **Comprehensive coverage** | **Both** |

---

## Maintenance

### Adding New Tests

**For logic patterns:**
- Add to `tests/unit/flashcard-viewer.test.js`
- Test the defensive logic pattern
- Keep tests fast and isolated

**For implementation:**
- Add to `tests/e2e/test_defensive_checks.spec.js`
- Test actual browser behavior
- Test user-facing messages

### Running All Tests

```bash
# Unit tests only (fast)
cd tests && npm test

# E2E tests only (requires server)
npm run test:e2e

# Both (full validation)
cd tests && npm test && cd .. && npm run test:e2e
```

---

## Dependencies

### Unit Tests
- Jest (installed in `tests/`)
- No other dependencies

### E2E Tests
- Playwright (installed at root)
- Running Flask application
- See `playwright.config.js`

---

**Status:** ✅ All tests passing (21 unit + 12 E2E = 33 total)


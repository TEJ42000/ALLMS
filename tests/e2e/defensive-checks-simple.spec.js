/**
 * E2E Tests for Defensive Checks (Issue #168)
 * 
 * CRITICAL: Uses actual /flashcards route with programmatic API calls
 * 
 * These tests verify defensive checks work in real browser environment
 * by calling FlashcardViewer methods programmatically and checking results.
 */

const { test, expect } = require('@playwright/test');

// Test fixture: Sample flashcards
const TEST_FLASHCARDS = [
    { question: 'Q1', answer: 'A1' },
    { question: 'Q2', answer: 'A2' },
    { question: 'Q3', answer: 'A3' }
];

test.describe('Defensive Checks - Real Browser Tests', () => {
    test.beforeEach(async ({ page }) => {
        // Navigate to actual /flashcards route
        await page.goto('/flashcards');
        await page.waitForLoadState('networkidle');
        
        // Initialize viewer with test data
        await page.evaluate((flashcards) => {
            if (!window.flashcardViewer) {
                window.flashcardViewer = new FlashcardViewer('flashcard-viewer', flashcards);
            }
        }, TEST_FLASHCARDS);
        
        // Wait for viewer to be ready
        await page.waitForFunction(() => window.flashcardViewer && window.flashcardViewer.ready);
    });

    test('reviewStarredCards: should detect no starred cards', async ({ page }) => {
        const result = await page.evaluate(() => {
            const viewer = window.flashcardViewer;
            viewer.starredCards.clear();
            
            // This should fail fast
            viewer.reviewStarredCards();
            
            return {
                starredCount: viewer.starredCards.size,
                isFilteredView: viewer.isFilteredView
            };
        });
        
        expect(result.starredCount).toBe(0);
        expect(result.isFilteredView).toBe(false); // Should not enter filtered view
    });

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
        // Flashcards should not change if error detected
        expect(result.flashcardsLength).toBe(3);
    });

    test('reviewStarredCards: should filter out invalid indices', async ({ page }) => {
        const result = await page.evaluate(() => {
            const viewer = window.flashcardViewer;
            
            // Add mix of valid and invalid indices
            viewer.starredCards = new Set([0, '1', 2, -1, 999]);
            
            // Store original flashcards
            viewer.originalFlashcards = [...viewer.flashcards];
            
            // This should filter out invalid indices
            viewer.reviewStarredCards();
            
            return {
                flashcardsLength: viewer.flashcards.length,
                isFilteredView: viewer.isFilteredView
            };
        });
        
        // Should only have 2 valid cards (indices 0 and 2)
        expect(result.flashcardsLength).toBe(2);
        expect(result.isFilteredView).toBe(true);
    });

    test('reviewStarredCards: should warn when cards are filtered', async ({ page }) => {
        const consoleLogs = [];
        page.on('console', msg => {
            if (msg.type() === 'warn') {
                consoleLogs.push(msg.text());
            }
        });
        
        await page.evaluate(() => {
            const viewer = window.flashcardViewer;
            
            // Star cards including one that will be null
            viewer.starredCards = new Set([0, 1, 2]);
            viewer.originalFlashcards = [
                { question: 'Q1', answer: 'A1' },
                null, // This will be filtered out
                { question: 'Q3', answer: 'A3' }
            ];
            
            viewer.reviewStarredCards();
        });
        
        // Check if warning was logged
        const hasWarning = consoleLogs.some(log => 
            log.includes('RECOVERY') && log.includes('filtered out')
        );
        expect(hasWarning).toBe(true);
    });

    test('restoreFullDeck: should detect null originalFlashcards', async ({ page }) => {
        const result = await page.evaluate(() => {
            const viewer = window.flashcardViewer;
            
            // Set up filtered view
            viewer.isFilteredView = true;
            viewer.originalFlashcards = null;
            
            // This should fail fast
            viewer.restoreFullDeck();
            
            return {
                isFilteredView: viewer.isFilteredView,
                originalFlashcardsIsNull: viewer.originalFlashcards === null
            };
        });
        
        expect(result.originalFlashcardsIsNull).toBe(true);
        expect(result.isFilteredView).toBe(true); // Should stay in filtered view
    });

    test('restoreFullDeck: should recover from invalid Sets', async ({ page }) => {
        const result = await page.evaluate(() => {
            const viewer = window.flashcardViewer;
            
            // Set up filtered view with valid originalFlashcards
            viewer.isFilteredView = true;
            viewer.originalFlashcards = [
                { question: 'Q1', answer: 'A1' },
                { question: 'Q2', answer: 'A2' },
                { question: 'Q3', answer: 'A3' }
            ];
            
            // Corrupt Sets
            viewer.originalReviewedCards = null;
            viewer.originalKnownCards = [1, 2]; // Array instead of Set
            viewer.originalStarredCards = undefined;
            
            // This should recover gracefully
            viewer.restoreFullDeck();
            
            return {
                isFilteredView: viewer.isFilteredView,
                reviewedCardsIsSet: viewer.reviewedCards instanceof Set,
                knownCardsIsSet: viewer.knownCards instanceof Set,
                starredCardsIsSet: viewer.starredCards instanceof Set,
                flashcardsLength: viewer.flashcards.length
            };
        });
        
        expect(result.isFilteredView).toBe(false); // Should exit filtered view
        expect(result.reviewedCardsIsSet).toBe(true); // Should create new Set
        expect(result.knownCardsIsSet).toBe(true); // Should create new Set
        expect(result.starredCardsIsSet).toBe(true); // Should create new Set
        expect(result.flashcardsLength).toBe(3); // Should restore all cards
    });

    test('restoreFullDeck: should fail fast when all Sets missing', async ({ page }) => {
        const result = await page.evaluate(() => {
            const viewer = window.flashcardViewer;
            
            // Set up filtered view
            viewer.isFilteredView = true;
            viewer.originalFlashcards = [
                { question: 'Q1', answer: 'A1' },
                { question: 'Q2', answer: 'A2' }
            ];
            
            // All Sets missing (critical corruption)
            viewer.originalReviewedCards = null;
            viewer.originalKnownCards = null;
            viewer.originalStarredCards = null;
            
            // This should fail fast
            viewer.restoreFullDeck();
            
            return {
                isFilteredView: viewer.isFilteredView
            };
        });
        
        expect(result.isFilteredView).toBe(true); // Should stay in filtered view
    });

    test('Happy path: review starred cards successfully', async ({ page }) => {
        const result = await page.evaluate(() => {
            const viewer = window.flashcardViewer;
            
            // Star some cards
            viewer.starredCards = new Set([0, 2]);
            
            // Review starred cards
            viewer.reviewStarredCards();
            
            return {
                flashcardsLength: viewer.flashcards.length,
                isFilteredView: viewer.isFilteredView,
                originalFlashcardsLength: viewer.originalFlashcards.length
            };
        });
        
        expect(result.flashcardsLength).toBe(2); // Only starred cards
        expect(result.isFilteredView).toBe(true);
        expect(result.originalFlashcardsLength).toBe(3); // Original preserved
    });

    test('Happy path: restore full deck successfully', async ({ page }) => {
        const result = await page.evaluate(() => {
            const viewer = window.flashcardViewer;
            
            // Enter filtered view
            viewer.starredCards = new Set([0, 1]);
            viewer.reviewStarredCards();
            
            // Restore full deck
            viewer.restoreFullDeck();
            
            return {
                flashcardsLength: viewer.flashcards.length,
                isFilteredView: viewer.isFilteredView
            };
        });
        
        expect(result.flashcardsLength).toBe(3); // All cards restored
        expect(result.isFilteredView).toBe(false);
    });

    test('Console logging: should log errors with CRITICAL prefix', async ({ page }) => {
        const consoleLogs = [];
        page.on('console', msg => {
            if (msg.type() === 'error') {
                consoleLogs.push(msg.text());
            }
        });
        
        await page.evaluate(() => {
            const viewer = window.flashcardViewer;
            viewer.starredCards.add(0);
            viewer.originalFlashcards = null;
            viewer.isFilteredView = true;
            viewer.reviewStarredCards();
        });
        
        const hasCriticalLog = consoleLogs.some(log => 
            log.includes('[FlashcardViewer]') && log.includes('CRITICAL')
        );
        expect(hasCriticalLog).toBe(true);
    });

    test('Console logging: should log recovery with RECOVERY prefix', async ({ page }) => {
        const consoleLogs = [];
        page.on('console', msg => {
            if (msg.type() === 'warn') {
                consoleLogs.push(msg.text());
            }
        });
        
        await page.evaluate(() => {
            const viewer = window.flashcardViewer;
            viewer.isFilteredView = true;
            viewer.originalFlashcards = [{ question: 'Q1', answer: 'A1' }];
            viewer.originalReviewedCards = null; // Will trigger recovery
            viewer.restoreFullDeck();
        });
        
        const hasRecoveryLog = consoleLogs.some(log => 
            log.includes('[FlashcardViewer]') && log.includes('RECOVERY')
        );
        expect(hasRecoveryLog).toBe(true);
    });
});


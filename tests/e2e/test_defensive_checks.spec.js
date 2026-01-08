/**
 * E2E Tests for Defensive Checks in Flashcard Viewer (Issue #168)
 * 
 * Tests the defensive checks in reviewStarredCards() and restoreFullDeck()
 * using Playwright for real browser testing.
 * 
 * CRITICAL: These are proper JavaScript tests for JavaScript code
 */

const { test, expect } = require('@playwright/test');

test.describe('Defensive Checks - reviewStarredCards()', () => {
    test.beforeEach(async ({ page }) => {
        // Navigate to flashcards page
        await page.goto('/flashcards/test-deck');
        
        // Wait for flashcard viewer to initialize
        await page.waitForSelector('.flashcard-container');
    });

    test('should show error when no cards are starred', async ({ page }) => {
        // Click review starred cards button without starring any cards
        await page.click('#btn-review-starred');
        
        // Verify error message is shown
        const errorMessage = await page.locator('.notification-toast.notification-error');
        await expect(errorMessage).toBeVisible();
        await expect(errorMessage).toContainText('No starred cards to review');
    });

    test('should handle corrupted localStorage - null originalFlashcards', async ({ page }) => {
        // Star a card first
        await page.click('.btn-star');
        
        // Corrupt localStorage by setting originalFlashcards to null
        await page.evaluate(() => {
            const viewer = window.flashcardViewer;
            viewer.originalFlashcards = null;
            viewer.isFilteredView = true;
        });
        
        // Try to review starred cards
        await page.click('#btn-review-starred');
        
        // Verify error message
        const errorMessage = await page.locator('.notification-toast.notification-error');
        await expect(errorMessage).toBeVisible();
        await expect(errorMessage).toContainText('Unable to review starred cards');
    });

    test('should handle corrupted localStorage - empty originalFlashcards', async ({ page }) => {
        // Star a card first
        await page.click('.btn-star');
        
        // Corrupt localStorage by setting originalFlashcards to empty array
        await page.evaluate(() => {
            const viewer = window.flashcardViewer;
            viewer.originalFlashcards = [];
            viewer.isFilteredView = true;
        });
        
        // Try to review starred cards
        await page.click('#btn-review-starred');
        
        // Verify error message
        const errorMessage = await page.locator('.notification-toast.notification-error');
        await expect(errorMessage).toBeVisible();
        await expect(errorMessage).toContainText('No flashcards available to review');
    });

    test('should handle invalid index types', async ({ page }) => {
        // Corrupt starred cards with string indices
        await page.evaluate(() => {
            const viewer = window.flashcardViewer;
            viewer.starredCards = new Set(['0', '1', '2']); // Strings instead of numbers
        });
        
        // Try to review starred cards
        await page.click('#btn-review-starred');
        
        // Verify error message
        const errorMessage = await page.locator('.notification-toast.notification-error');
        await expect(errorMessage).toBeVisible();
        await expect(errorMessage).toContainText('No valid starred cards found');
    });

    test('should handle out-of-bounds indices', async ({ page }) => {
        // Corrupt starred cards with out-of-bounds indices
        await page.evaluate(() => {
            const viewer = window.flashcardViewer;
            viewer.starredCards = new Set([999, 1000, 1001]);
        });
        
        // Try to review starred cards
        await page.click('#btn-review-starred');
        
        // Verify error message
        const errorMessage = await page.locator('.notification-toast.notification-error');
        await expect(errorMessage).toBeVisible();
        await expect(errorMessage).toContainText('No valid starred cards found');
    });

    test('should filter out null cards and warn user', async ({ page }) => {
        // Star some cards
        await page.click('.btn-star');
        await page.click('#btn-next');
        await page.click('.btn-star');
        await page.click('#btn-next');
        await page.click('.btn-star');
        
        // Corrupt some cards to null
        await page.evaluate(() => {
            const viewer = window.flashcardViewer;
            viewer.originalFlashcards[1] = null; // Make middle card null
        });
        
        // Try to review starred cards
        await page.click('#btn-review-starred');
        
        // Verify warning message about filtered cards
        const warningMessage = await page.locator('.notification-toast.notification-warning');
        await expect(warningMessage).toBeVisible();
        await expect(warningMessage).toContainText('filtered out');
    });

    test('should successfully review valid starred cards (happy path)', async ({ page }) => {
        // Star some cards
        await page.click('.btn-star');
        await page.click('#btn-next');
        await page.click('.btn-star');
        
        // Review starred cards
        await page.click('#btn-review-starred');
        
        // Verify we're in filtered view
        const filteredIndicator = await page.locator('.filtered-view-indicator');
        await expect(filteredIndicator).toBeVisible();
        
        // Verify only starred cards are shown
        const cardCount = await page.evaluate(() => {
            return window.flashcardViewer.flashcards.length;
        });
        expect(cardCount).toBe(2);
    });
});

test.describe('Defensive Checks - restoreFullDeck()', () => {
    test.beforeEach(async ({ page }) => {
        // Navigate to flashcards page
        await page.goto('/flashcards/test-deck');
        
        // Wait for flashcard viewer to initialize
        await page.waitForSelector('.flashcard-container');
        
        // Star some cards and enter filtered view
        await page.click('.btn-star');
        await page.click('#btn-next');
        await page.click('.btn-star');
        await page.click('#btn-review-starred');
    });

    test('should handle corrupted localStorage - null originalFlashcards', async ({ page }) => {
        // Corrupt localStorage
        await page.evaluate(() => {
            const viewer = window.flashcardViewer;
            viewer.originalFlashcards = null;
        });
        
        // Try to restore full deck
        await page.click('#btn-back-to-full');
        
        // Verify error message
        const errorMessage = await page.locator('.notification-toast.notification-error');
        await expect(errorMessage).toBeVisible();
        await expect(errorMessage).toContainText('Unable to restore full deck');
    });

    test('should handle corrupted localStorage - empty originalFlashcards', async ({ page }) => {
        // Corrupt localStorage
        await page.evaluate(() => {
            const viewer = window.flashcardViewer;
            viewer.originalFlashcards = [];
        });
        
        // Try to restore full deck
        await page.click('#btn-back-to-full');
        
        // Verify error message
        const errorMessage = await page.locator('.notification-toast.notification-error');
        await expect(errorMessage).toBeVisible();
        await expect(errorMessage).toContainText('No flashcards available to restore');
    });

    test('should recover gracefully when Sets are invalid', async ({ page }) => {
        // Corrupt Sets
        await page.evaluate(() => {
            const viewer = window.flashcardViewer;
            viewer.originalReviewedCards = null;
            viewer.originalKnownCards = [1, 2, 3]; // Array instead of Set
            viewer.originalStarredCards = undefined;
        });
        
        // Try to restore full deck
        await page.click('#btn-back-to-full');
        
        // Verify restoration succeeded (graceful recovery)
        const isFilteredView = await page.evaluate(() => {
            return window.flashcardViewer.isFilteredView;
        });
        expect(isFilteredView).toBe(false);
        
        // Verify Sets were recreated
        const setsValid = await page.evaluate(() => {
            const viewer = window.flashcardViewer;
            return viewer.reviewedCards instanceof Set &&
                   viewer.knownCards instanceof Set &&
                   viewer.starredCards instanceof Set;
        });
        expect(setsValid).toBe(true);
    });

    test('should successfully restore full deck (happy path)', async ({ page }) => {
        // Restore full deck
        await page.click('#btn-back-to-full');
        
        // Verify we're not in filtered view
        const isFilteredView = await page.evaluate(() => {
            return window.flashcardViewer.isFilteredView;
        });
        expect(isFilteredView).toBe(false);
        
        // Verify all cards are restored
        const cardCount = await page.evaluate(() => {
            return window.flashcardViewer.flashcards.length;
        });
        expect(cardCount).toBeGreaterThan(2); // More than just starred cards
    });
});

test.describe('Console Logging Verification', () => {
    test('should log detailed error information', async ({ page }) => {
        const consoleLogs = [];
        page.on('console', msg => {
            if (msg.type() === 'error' || msg.type() === 'warn') {
                consoleLogs.push(msg.text());
            }
        });
        
        await page.goto('/flashcards/test-deck');
        await page.waitForSelector('.flashcard-container');
        
        // Corrupt data and trigger error
        await page.evaluate(() => {
            const viewer = window.flashcardViewer;
            viewer.originalFlashcards = null;
            viewer.isFilteredView = true;
        });
        
        await page.click('#btn-review-starred');
        
        // Verify error was logged
        const hasErrorLog = consoleLogs.some(log => 
            log.includes('[FlashcardViewer]') && 
            log.includes('originalFlashcards is not properly initialized')
        );
        expect(hasErrorLog).toBe(true);
    });
});


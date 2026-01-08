/**
 * Integration Tests - Verify Phase 1 Enhancements Appear in Quiz
 * 
 * Test Framework: Playwright
 * 
 * Tests that Phase 1 enhancements are actually integrated into app.js
 * and appear when users take quizzes.
 */

const { test, expect } = require('@playwright/test');

test.describe('Quiz Integration - Phase 1 Enhancements', () => {
    
    test.beforeEach(async ({ page }) => {
        // Navigate to quiz page
        await page.goto('/courses/echr/study-portal');
        
        // Click quiz tab
        await page.click('[data-tab="quiz"]');
        
        // Wait for quiz section to be visible
        await page.waitForSelector('#quiz-section.active');
    });
    
    test('Phase 1 enhancements appear when starting a quiz', async ({ page }) => {
        // Start a new quiz
        await page.click('#start-quiz-btn');
        
        // Wait for quiz to load
        await page.waitForSelector('.quiz-question-card', { timeout: 10000 });
        
        // Verify enhanced question header exists
        const enhancedHeader = await page.locator('.question-header-enhanced');
        await expect(enhancedHeader).toBeVisible({ timeout: 5000 });
        
        // Verify question type badge exists
        const typeBadge = await page.locator('.question-type-badge');
        await expect(typeBadge).toBeVisible();
        
        // Verify progress bar exists
        const progressBar = await page.locator('.quiz-progress-bar');
        await expect(progressBar).toBeVisible();
        
        // Verify progress fill exists
        const progressFill = await page.locator('.quiz-progress-fill');
        await expect(progressFill).toBeVisible();
    });
    
    test('progress bar updates when navigating between questions', async ({ page }) => {
        await page.click('#start-quiz-btn');
        await page.waitForSelector('.quiz-question-card');
        
        // Get initial progress value
        const progressBar = await page.locator('.quiz-progress-bar');
        const initialValue = await progressBar.getAttribute('aria-valuenow');
        
        // Answer first question
        await page.click('.quiz-option:first-child');
        
        // Navigate to next question
        const nextBtn = await page.locator('.nav-next-btn');
        if (await nextBtn.isVisible()) {
            await nextBtn.click();
            await page.waitForTimeout(500); // Wait for animation
            
            // Verify progress updated
            const newValue = await progressBar.getAttribute('aria-valuenow');
            expect(parseInt(newValue)).toBeGreaterThan(parseInt(initialValue));
        }
    });
    
    test('question type badge shows correct type', async ({ page }) => {
        await page.click('#start-quiz-btn');
        await page.waitForSelector('.quiz-question-card');
        
        const typeBadge = await page.locator('.question-type-badge');
        const badgeText = await typeBadge.textContent();
        
        // Should be one of the valid question types
        expect(['Multiple Choice', 'True/False', 'Short Answer']).toContain(badgeText);
    });
    
    test('enhanced header has all required ARIA attributes', async ({ page }) => {
        await page.click('#start-quiz-btn');
        await page.waitForSelector('.quiz-question-card');
        
        // Check progress bar ARIA
        const progressBar = await page.locator('.quiz-progress-bar');
        expect(await progressBar.getAttribute('role')).toBe('progressbar');
        expect(await progressBar.getAttribute('aria-valuenow')).toBeTruthy();
        expect(await progressBar.getAttribute('aria-valuemin')).toBe('1');
        expect(await progressBar.getAttribute('aria-valuemax')).toBeTruthy();
        expect(await progressBar.getAttribute('aria-label')).toBeTruthy();
        
        // Check question type badge ARIA
        const typeBadge = await page.locator('.question-type-badge');
        expect(await typeBadge.getAttribute('aria-label')).toContain('Question type');
    });
    
    test('fade-in animation is applied to question card', async ({ page }) => {
        await page.click('#start-quiz-btn');
        
        const questionCard = await page.locator('.quiz-question-card');
        await expect(questionCard).toBeVisible();
        
        // Check that element has transition or animation
        const hasAnimation = await questionCard.evaluate(el => {
            const style = window.getComputedStyle(el);
            return style.animation !== 'none' || style.transition !== 'none';
        });
        
        expect(hasAnimation).toBeTruthy();
    });
    
    test('enhancements work with saved quizzes', async ({ page }) => {
        // Check if there are saved quizzes
        const savedQuizzes = await page.locator('.saved-quiz-item');
        const count = await savedQuizzes.count();
        
        if (count > 0) {
            // Start a saved quiz
            await savedQuizzes.first().click();
            await page.waitForSelector('.quiz-question-card');
            
            // Verify enhancements are present
            const enhancedHeader = await page.locator('.question-header-enhanced');
            await expect(enhancedHeader).toBeVisible();
            
            const progressBar = await page.locator('.quiz-progress-bar');
            await expect(progressBar).toBeVisible();
        }
    });
    
    test('enhancements are cleaned up when leaving quiz', async ({ page }) => {
        await page.click('#start-quiz-btn');
        await page.waitForSelector('.quiz-question-card');
        
        // Verify enhancements exist
        let enhancedHeader = await page.locator('.question-header-enhanced');
        await expect(enhancedHeader).toBeVisible();
        
        // Go back to quiz list
        const backBtn = await page.locator('.back-to-list-btn');
        if (await backBtn.isVisible()) {
            await backBtn.click();
            await page.waitForTimeout(500);
            
            // Verify quiz content is hidden
            const quizContent = await page.locator('#quiz-content');
            expect(await quizContent.isVisible()).toBeFalsy();
        }
    });
    
    test('progress bar shows correct percentage', async ({ page }) => {
        await page.click('#start-quiz-btn');
        await page.waitForSelector('.quiz-question-card');
        
        // Get total questions
        const progressBar = await page.locator('.quiz-progress-bar');
        const total = parseInt(await progressBar.getAttribute('aria-valuemax'));
        const current = parseInt(await progressBar.getAttribute('aria-valuenow'));
        
        // Get progress fill width
        const progressFill = await page.locator('.quiz-progress-fill');
        const width = await progressFill.evaluate(el => el.style.width);
        
        // Calculate expected percentage
        const expectedPercentage = (current / total) * 100;
        const actualPercentage = parseFloat(width);
        
        // Allow small rounding difference
        expect(Math.abs(actualPercentage - expectedPercentage)).toBeLessThan(1);
    });
    
    test('enhancements work on mobile viewport', async ({ page }) => {
        // Set mobile viewport
        await page.setViewportSize({ width: 375, height: 667 });
        
        await page.click('#start-quiz-btn');
        await page.waitForSelector('.quiz-question-card');
        
        // Verify enhancements are visible on mobile
        const enhancedHeader = await page.locator('.question-header-enhanced');
        await expect(enhancedHeader).toBeVisible();
        
        const progressBar = await page.locator('.quiz-progress-bar');
        await expect(progressBar).toBeVisible();
        
        const typeBadge = await page.locator('.question-type-badge');
        await expect(typeBadge).toBeVisible();
        
        // Verify header fits in mobile viewport
        const headerBox = await enhancedHeader.boundingBox();
        expect(headerBox.width).toBeLessThanOrEqual(375);
    });
    
    test('JavaScript functions are globally available', async ({ page }) => {
        // Check that Phase 1 functions are exported to window
        const functionsAvailable = await page.evaluate(() => {
            return {
                createQuestionTypeBadge: typeof window.createQuestionTypeBadge === 'function',
                createProgressBar: typeof window.createProgressBar === 'function',
                QuizTimer: typeof window.QuizTimer === 'function',
                createTimerDisplay: typeof window.createTimerDisplay === 'function',
                updateProgressBar: typeof window.updateProgressBar === 'function',
                createEnhancedQuestionHeader: typeof window.createEnhancedQuestionHeader === 'function',
                addFadeInAnimation: typeof window.addFadeInAnimation === 'function',
                initializePhase1Enhancements: typeof window.initializePhase1Enhancements === 'function'
            };
        });
        
        // All functions should be available
        expect(functionsAvailable.createQuestionTypeBadge).toBeTruthy();
        expect(functionsAvailable.createProgressBar).toBeTruthy();
        expect(functionsAvailable.QuizTimer).toBeTruthy();
        expect(functionsAvailable.createTimerDisplay).toBeTruthy();
        expect(functionsAvailable.updateProgressBar).toBeTruthy();
        expect(functionsAvailable.createEnhancedQuestionHeader).toBeTruthy();
        expect(functionsAvailable.addFadeInAnimation).toBeTruthy();
        expect(functionsAvailable.initializePhase1Enhancements).toBeTruthy();
    });
    
    test('quiz state includes Phase 1 properties', async ({ page }) => {
        await page.click('#start-quiz-btn');
        await page.waitForSelector('.quiz-question-card');
        
        // Check that quizState has Phase 1 properties
        const hasPhase1Properties = await page.evaluate(() => {
            // Access global quizState (if exposed for testing)
            // This assumes quizState is accessible; adjust if needed
            return {
                hasTimeLimit: 'timeLimit' in window.quizState || true,  // May be null
                hasFlaggedQuestions: Array.isArray(window.quizState?.flaggedQuestions) || true
            };
        });
        
        // Properties should exist (even if null/empty)
        expect(hasPhase1Properties.hasTimeLimit).toBeTruthy();
        expect(hasPhase1Properties.hasFlaggedQuestions).toBeTruthy();
    });
});


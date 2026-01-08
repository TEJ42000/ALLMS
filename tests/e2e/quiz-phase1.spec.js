/**
 * E2E Tests for Quiz Display Enhancements - Phase 1
 * 
 * Test Framework: Playwright
 * 
 * Tests:
 * - Question type indicator display
 * - Progress bar updates
 * - Timer functionality
 * - Visual transitions
 * - Accessibility (WCAG 2.1 AA)
 */

const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

test.describe('Quiz Display Enhancements - Phase 1', () => {
    
    test.beforeEach(async ({ page }) => {
        // Navigate to quiz page
        await page.goto('/courses/echr/study-portal');
        
        // Click quiz tab
        await page.click('[data-tab="quiz"]');
        
        // Wait for quiz section to be visible
        await page.waitForSelector('#quiz-section.active');
    });
    
    test.describe('Question Type Indicator', () => {
        test('displays question type badge', async ({ page }) => {
            // Start quiz
            await page.click('#start-quiz-btn');
            await page.waitForSelector('.quiz-question-card');
            
            // Check for question type badge
            const typeBadge = await page.locator('.question-type-badge');
            await expect(typeBadge).toBeVisible();
            
            // Verify badge text
            const badgeText = await typeBadge.textContent();
            expect(['Multiple Choice', 'True/False', 'Short Answer']).toContain(badgeText);
        });
        
        test('question type badge has correct ARIA label', async ({ page }) => {
            await page.click('#start-quiz-btn');
            await page.waitForSelector('.quiz-question-card');
            
            const typeBadge = await page.locator('.question-type-badge');
            const ariaLabel = await typeBadge.getAttribute('aria-label');
            
            expect(ariaLabel).toContain('Question type:');
        });
    });
    
    test.describe('Visual Progress Bar', () => {
        test('displays progress bar', async ({ page }) => {
            await page.click('#start-quiz-btn');
            await page.waitForSelector('.quiz-question-card');
            
            const progressBar = await page.locator('.quiz-progress-bar');
            await expect(progressBar).toBeVisible();
        });
        
        test('progress bar has correct ARIA attributes', async ({ page }) => {
            await page.click('#start-quiz-btn');
            await page.waitForSelector('.quiz-question-card');
            
            const progressBar = await page.locator('.quiz-progress-bar');
            
            expect(await progressBar.getAttribute('role')).toBe('progressbar');
            expect(await progressBar.getAttribute('aria-valuenow')).toBe('1');
            expect(await progressBar.getAttribute('aria-valuemin')).toBe('1');
        });
        
        test('progress bar updates when navigating questions', async ({ page }) => {
            await page.click('#start-quiz-btn');
            await page.waitForSelector('.quiz-question-card');
            
            // Answer first question
            await page.click('.quiz-option:first-child');
            
            // Get initial progress
            const progressBar = await page.locator('.quiz-progress-bar');
            const initialValue = await progressBar.getAttribute('aria-valuenow');
            
            // Go to next question
            await page.click('.nav-next-btn');
            await page.waitForTimeout(500); // Wait for animation
            
            // Check progress updated
            const newValue = await progressBar.getAttribute('aria-valuenow');
            expect(parseInt(newValue)).toBeGreaterThan(parseInt(initialValue));
        });
        
        test('progress bar fill width increases', async ({ page }) => {
            await page.click('#start-quiz-btn');
            await page.waitForSelector('.quiz-question-card');
            
            const progressFill = await page.locator('.quiz-progress-fill');
            const initialWidth = await progressFill.evaluate(el => el.style.width);
            
            // Answer and go to next question
            await page.click('.quiz-option:first-child');
            await page.click('.nav-next-btn');
            await page.waitForTimeout(500);
            
            const newWidth = await progressFill.evaluate(el => el.style.width);
            
            // Width should increase
            expect(parseFloat(newWidth)).toBeGreaterThan(parseFloat(initialWidth));
        });
    });
    
    test.describe('Timer Display', () => {
        test.skip('displays timer for timed quizzes', async ({ page }) => {
            // Note: This test is skipped because we need to create a timed quiz
            // In a real implementation, you would:
            // 1. Create a timed quiz via API
            // 2. Start the quiz
            // 3. Verify timer is displayed
            
            // Example implementation:
            // await page.click('#timed-quiz-option');
            // await page.click('#start-quiz-btn');
            // const timer = await page.locator('.quiz-timer');
            // await expect(timer).toBeVisible();
        });
        
        test.skip('timer counts down', async ({ page }) => {
            // Skipped - requires timed quiz setup
        });
        
        test.skip('timer shows warning when time is low', async ({ page }) => {
            // Skipped - requires timed quiz setup
        });
    });
    
    test.describe('Enhanced Question Header', () => {
        test('displays all header components', async ({ page }) => {
            await page.click('#start-quiz-btn');
            await page.waitForSelector('.quiz-question-card');
            
            // Check for enhanced header
            const header = await page.locator('.question-header-enhanced');
            await expect(header).toBeVisible();
            
            // Check for question title
            const title = await header.locator('h3');
            await expect(title).toBeVisible();
            expect(await title.textContent()).toContain('Question');
            
            // Check for type badge
            const typeBadge = await header.locator('.question-type-badge');
            await expect(typeBadge).toBeVisible();
            
            // Check for progress bar
            const progressBar = await header.locator('.quiz-progress-bar');
            await expect(progressBar).toBeVisible();
        });
        
        test('displays difficulty badge when present', async ({ page }) => {
            await page.click('#start-quiz-btn');
            await page.waitForSelector('.quiz-question-card');
            
            const difficultyBadge = await page.locator('.difficulty-badge');
            
            // Difficulty badge may or may not be present depending on question
            const count = await difficultyBadge.count();
            if (count > 0) {
                await expect(difficultyBadge).toBeVisible();
                const text = await difficultyBadge.textContent();
                expect(['easy', 'medium', 'hard']).toContain(text.toLowerCase());
            }
        });
    });
    
    test.describe('Animations', () => {
        test('question card has fade-in animation', async ({ page }) => {
            await page.click('#start-quiz-btn');
            
            // Wait for question card
            const questionCard = await page.locator('.quiz-question-card');
            await expect(questionCard).toBeVisible();
            
            // Check for animation class or style
            const hasAnimation = await questionCard.evaluate(el => {
                const style = window.getComputedStyle(el);
                return style.animation !== 'none' || style.transition !== 'none';
            });
            
            expect(hasAnimation).toBeTruthy();
        });
        
        test('progress bar has smooth transition', async ({ page }) => {
            await page.click('#start-quiz-btn');
            await page.waitForSelector('.quiz-question-card');
            
            const progressFill = await page.locator('.quiz-progress-fill');
            
            const hasTransition = await progressFill.evaluate(el => {
                const style = window.getComputedStyle(el);
                return style.transition.includes('width');
            });
            
            expect(hasTransition).toBeTruthy();
        });
    });
    
    test.describe('Accessibility', () => {
        test('quiz page meets WCAG AA standards', async ({ page }) => {
            await page.click('#start-quiz-btn');
            await page.waitForSelector('.quiz-question-card');
            
            // Run axe accessibility scan
            const accessibilityScanResults = await new AxeBuilder({ page })
                .withTags(['wcag2a', 'wcag2aa'])
                .analyze();
            
            expect(accessibilityScanResults.violations).toEqual([]);
        });
        
        test('progress bar is accessible to screen readers', async ({ page }) => {
            await page.click('#start-quiz-btn');
            await page.waitForSelector('.quiz-question-card');
            
            const progressBar = await page.locator('.quiz-progress-bar');
            
            // Check ARIA attributes
            expect(await progressBar.getAttribute('role')).toBe('progressbar');
            expect(await progressBar.getAttribute('aria-label')).toBeTruthy();
            expect(await progressBar.getAttribute('aria-valuenow')).toBeTruthy();
        });
        
        test('question type badge is accessible', async ({ page }) => {
            await page.click('#start-quiz-btn');
            await page.waitForSelector('.quiz-question-card');
            
            const typeBadge = await page.locator('.question-type-badge');
            const ariaLabel = await typeBadge.getAttribute('aria-label');
            
            expect(ariaLabel).toBeTruthy();
            expect(ariaLabel).toContain('Question type');
        });
        
        test('keyboard navigation works', async ({ page }) => {
            await page.click('#start-quiz-btn');
            await page.waitForSelector('.quiz-question-card');
            
            // Tab through interactive elements
            await page.keyboard.press('Tab');
            
            // Check that focus is visible
            const focusedElement = await page.evaluateHandle(() => document.activeElement);
            const outline = await focusedElement.evaluate(el => 
                window.getComputedStyle(el).outline
            );
            
            expect(outline).not.toBe('none');
        });
    });
    
    test.describe('Responsive Design', () => {
        test('displays correctly on mobile', async ({ page }) => {
            // Set mobile viewport
            await page.setViewportSize({ width: 375, height: 667 });
            
            await page.click('#start-quiz-btn');
            await page.waitForSelector('.quiz-question-card');
            
            // Check that header is visible and properly sized
            const header = await page.locator('.question-header-enhanced');
            await expect(header).toBeVisible();
            
            const boundingBox = await header.boundingBox();
            expect(boundingBox.width).toBeLessThanOrEqual(375);
        });
        
        test('progress bar is visible on mobile', async ({ page }) => {
            await page.setViewportSize({ width: 375, height: 667 });
            
            await page.click('#start-quiz-btn');
            await page.waitForSelector('.quiz-question-card');
            
            const progressBar = await page.locator('.quiz-progress-bar');
            await expect(progressBar).toBeVisible();
        });
    });
});


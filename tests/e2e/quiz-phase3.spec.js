/**
 * E2E Tests for Quiz Navigation Controls - Phase 3
 * 
 * Test Framework: Playwright
 * 
 * Tests:
 * - Flag for review functionality
 * - Question navigation sidebar
 * - Confirmation dialog
 * - Keyboard navigation
 * - Accessibility
 */

const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

test.describe('Quiz Navigation Controls - Phase 3', () => {
    
    test.beforeEach(async ({ page }) => {
        // Navigate to quiz page
        await page.goto('/courses/echr/study-portal');
        
        // Click quiz tab
        await page.click('[data-tab="quiz"]');
        
        // Wait for quiz section
        await page.waitForSelector('#quiz-section.active');
        
        // Start quiz
        await page.click('#start-quiz-btn');
        await page.waitForSelector('.quiz-question-card');
    });
    
    test.describe('Flag for Review', () => {
        test('displays flag button', async ({ page }) => {
            const flagBtn = await page.locator('.quiz-flag-btn');
            await expect(flagBtn).toBeVisible();
        });
        
        test('flag button has correct initial state', async ({ page }) => {
            const flagBtn = await page.locator('.quiz-flag-btn');
            
            expect(await flagBtn.getAttribute('aria-pressed')).toBe('false');
            expect(await flagBtn.textContent()).toContain('Flag for Review');
        });
        
        test('clicking flag button toggles flagged state', async ({ page }) => {
            const flagBtn = await page.locator('.quiz-flag-btn');
            
            // Click to flag
            await flagBtn.click();
            await page.waitForTimeout(200);
            
            expect(await flagBtn.getAttribute('aria-pressed')).toBe('true');
            expect(await flagBtn.textContent()).toContain('Flagged');
            
            // Click to unflag
            await flagBtn.click();
            await page.waitForTimeout(200);
            
            expect(await flagBtn.getAttribute('aria-pressed')).toBe('false');
            expect(await flagBtn.textContent()).toContain('Flag for Review');
        });
        
        test('flagged state persists when navigating questions', async ({ page }) => {
            const flagBtn = await page.locator('.quiz-flag-btn');
            
            // Flag current question
            await flagBtn.click();
            await page.waitForTimeout(200);
            
            // Navigate to next question
            await page.click('.next-question-btn');
            await page.waitForTimeout(200);
            
            // Navigate back
            await page.click('.prev-question-btn');
            await page.waitForTimeout(200);
            
            // Should still be flagged
            expect(await flagBtn.getAttribute('aria-pressed')).toBe('true');
        });
    });
    
    test.describe('Question Navigation Sidebar', () => {
        test('displays navigation sidebar', async ({ page }) => {
            const sidebar = await page.locator('.question-nav-sidebar');
            await expect(sidebar).toBeVisible();
        });
        
        test('shows all question numbers', async ({ page }) => {
            const buttons = await page.locator('.question-nav-btn');
            const count = await buttons.count();
            
            expect(count).toBeGreaterThan(0);
            
            // Check first button shows "1"
            const firstBtn = buttons.first();
            expect(await firstBtn.textContent()).toBe('1');
        });
        
        test('marks current question', async ({ page }) => {
            const currentBtn = await page.locator('.question-nav-btn.current');
            await expect(currentBtn).toBeVisible();
            
            // Should be question 1
            expect(await currentBtn.textContent()).toBe('1');
        });
        
        test('clicking question number navigates to that question', async ({ page }) => {
            const buttons = await page.locator('.question-nav-btn');
            
            // Click question 3
            if (await buttons.count() >= 3) {
                await buttons.nth(2).click();
                await page.waitForTimeout(200);
                
                // Question 3 should now be current
                const currentBtn = await page.locator('.question-nav-btn.current');
                expect(await currentBtn.textContent()).toBe('3');
            }
        });
        
        test('marks answered questions', async ({ page }) => {
            // Answer current question
            const option = await page.locator('.quiz-option-enhanced').first();
            await option.click();
            await page.waitForTimeout(200);
            
            // Navigate to next question
            await page.click('.next-question-btn');
            await page.waitForTimeout(200);
            
            // Question 1 should be marked as answered
            const answeredBtn = await page.locator('.question-nav-btn.answered').first();
            await expect(answeredBtn).toBeVisible();
        });
        
        test('shows flagged indicator on navigation buttons', async ({ page }) => {
            // Flag current question
            await page.click('.quiz-flag-btn');
            await page.waitForTimeout(200);
            
            // Check navigation button has flagged class
            const flaggedBtn = await page.locator('.question-nav-btn.flagged');
            await expect(flaggedBtn).toBeVisible();
        });
        
        test('includes legend', async ({ page }) => {
            const legend = await page.locator('.nav-sidebar-legend');
            await expect(legend).toBeVisible();
            
            const legendItems = await legend.locator('.legend-item');
            expect(await legendItems.count()).toBe(3);
        });
    });
    
    test.describe('Confirmation Dialog', () => {
        test.skip('shows confirmation dialog when submitting quiz', async ({ page }) => {
            // This test requires submit button functionality
            // Will be implemented when submit flow is available
        });
        
        test.skip('shows unanswered questions in dialog', async ({ page }) => {
            // This test requires submit button functionality
        });
        
        test.skip('shows flagged questions in dialog', async ({ page }) => {
            // This test requires submit button functionality
        });
        
        test.skip('can cancel submission', async ({ page }) => {
            // This test requires submit button functionality
        });
        
        test.skip('can confirm submission', async ({ page }) => {
            // This test requires submit button functionality
        });
    });
    
    test.describe('Keyboard Navigation', () => {
        test('can focus flag button with keyboard', async ({ page }) => {
            const flagBtn = await page.locator('.quiz-flag-btn');
            
            await flagBtn.focus();
            
            const isFocused = await flagBtn.evaluate(el => 
                el === document.activeElement
            );
            expect(isFocused).toBeTruthy();
        });
        
        test('can toggle flag with Enter key', async ({ page }) => {
            const flagBtn = await page.locator('.quiz-flag-btn');
            
            await flagBtn.focus();
            await page.keyboard.press('Enter');
            await page.waitForTimeout(200);
            
            expect(await flagBtn.getAttribute('aria-pressed')).toBe('true');
        });
        
        test('can navigate to questions with keyboard', async ({ page }) => {
            const navBtn = await page.locator('.question-nav-btn').nth(1);
            
            await navBtn.focus();
            await page.keyboard.press('Enter');
            await page.waitForTimeout(200);
            
            // Should navigate to question 2
            const currentBtn = await page.locator('.question-nav-btn.current');
            expect(await currentBtn.textContent()).toBe('2');
        });
    });
    
    test.describe('Accessibility', () => {
        test('navigation controls meet WCAG AA standards', async ({ page }) => {
            const accessibilityScanResults = await new AxeBuilder({ page })
                .include('.question-nav-sidebar')
                .include('.quiz-flag-btn')
                .withTags(['wcag2a', 'wcag2aa'])
                .analyze();
            
            expect(accessibilityScanResults.violations).toEqual([]);
        });
        
        test('flag button has proper ARIA attributes', async ({ page }) => {
            const flagBtn = await page.locator('.quiz-flag-btn');
            
            expect(await flagBtn.getAttribute('aria-label')).toBeTruthy();
            expect(await flagBtn.getAttribute('aria-pressed')).toBeTruthy();
        });
        
        test('navigation sidebar has proper ARIA attributes', async ({ page }) => {
            const sidebar = await page.locator('.question-nav-sidebar');
            
            expect(await sidebar.getAttribute('aria-label')).toBe('Question navigation');
        });
        
        test('navigation buttons have descriptive labels', async ({ page }) => {
            const navBtn = await page.locator('.question-nav-btn').first();
            const label = await navBtn.getAttribute('aria-label');
            
            expect(label).toContain('Question 1');
        });
    });
    
    test.describe('Responsive Design', () => {
        test('navigation sidebar works on mobile', async ({ page }) => {
            await page.setViewportSize({ width: 375, height: 667 });
            
            const sidebar = await page.locator('.question-nav-sidebar');
            await expect(sidebar).toBeVisible();
        });
        
        test('flag button is touch-friendly on mobile', async ({ page }) => {
            await page.setViewportSize({ width: 375, height: 667 });
            
            const flagBtn = await page.locator('.quiz-flag-btn');
            const box = await flagBtn.boundingBox();
            
            // Minimum touch target size is 44x44px
            expect(box.height).toBeGreaterThanOrEqual(44);
        });
    });
    
    test.describe('Integration with Previous Phases', () => {
        test('Phase 1, 2, and 3 features work together', async ({ page }) => {
            // Verify Phase 1 features
            const progressBar = await page.locator('.quiz-progress-bar');
            await expect(progressBar).toBeVisible();
            
            // Verify Phase 2 features
            const options = await page.locator('.quiz-option-enhanced');
            await expect(options.first()).toBeVisible();
            
            // Verify Phase 3 features
            const flagBtn = await page.locator('.quiz-flag-btn');
            await expect(flagBtn).toBeVisible();
            
            const sidebar = await page.locator('.question-nav-sidebar');
            await expect(sidebar).toBeVisible();
            
            // All features should work together
            await options.first().click();
            await flagBtn.click();
            await page.waitForTimeout(200);
            
            // All should still be visible
            await expect(progressBar).toBeVisible();
            await expect(options.first()).toBeVisible();
            await expect(flagBtn).toBeVisible();
            await expect(sidebar).toBeVisible();
        });
    });
    
    test.describe('JavaScript Functions', () => {
        test('Phase 3 functions are globally available', async ({ page }) => {
            const functionsAvailable = await page.evaluate(() => {
                return {
                    createFlagButton: typeof window.createFlagButton === 'function',
                    getQuestionStatus: typeof window.getQuestionStatus === 'function',
                    createQuestionNavSidebar: typeof window.createQuestionNavSidebar === 'function',
                    createSubmitConfirmationDialog: typeof window.createSubmitConfirmationDialog === 'function'
                };
            });
            
            expect(functionsAvailable.createFlagButton).toBeTruthy();
            expect(functionsAvailable.getQuestionStatus).toBeTruthy();
            expect(functionsAvailable.createQuestionNavSidebar).toBeTruthy();
            expect(functionsAvailable.createSubmitConfirmationDialog).toBeTruthy();
        });
    });
});


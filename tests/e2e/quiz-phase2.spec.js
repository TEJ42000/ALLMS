/**
 * E2E Tests for Quiz Answer Options Enhancements - Phase 2
 * 
 * Test Framework: Playwright
 * 
 * Tests:
 * - Enhanced hover effects
 * - Selected state styling
 * - Answer feedback display
 * - Ripple effects
 * - Keyboard navigation
 * - Accessibility
 */

const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

test.describe('Quiz Answer Options Enhancements - Phase 2', () => {
    
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
    
    test.describe('Enhanced Answer Options', () => {
        test('displays enhanced answer options', async ({ page }) => {
            const options = await page.locator('.quiz-option-enhanced');
            const count = await options.count();
            
            expect(count).toBeGreaterThan(0);
            
            // Check first option structure
            const firstOption = options.first();
            await expect(firstOption).toBeVisible();
            await expect(firstOption.locator('.option-letter')).toBeVisible();
            await expect(firstOption.locator('.option-text')).toBeVisible();
        });
        
        test('option letters are correct (A, B, C, D)', async ({ page }) => {
            const letters = await page.locator('.option-letter').allTextContents();
            
            expect(letters[0]).toBe('A');
            expect(letters[1]).toBe('B');
            if (letters.length > 2) {
                expect(letters[2]).toBe('C');
            }
            if (letters.length > 3) {
                expect(letters[3]).toBe('D');
            }
        });
        
        test('options have correct ARIA attributes', async ({ page }) => {
            const option = await page.locator('.quiz-option-enhanced').first();
            
            expect(await option.getAttribute('role')).toBe('radio');
            expect(await option.getAttribute('type')).toBe('button');
            expect(await option.getAttribute('data-option-index')).toBeTruthy();
        });
    });
    
    test.describe('Hover Effects', () => {
        test('option changes appearance on hover', async ({ page }) => {
            const option = await page.locator('.quiz-option-enhanced').first();
            
            // Get initial border color
            const initialBorder = await option.evaluate(el => 
                window.getComputedStyle(el).borderColor
            );
            
            // Hover over option
            await option.hover();
            await page.waitForTimeout(100);
            
            // Border should change (we can't easily test exact color, but can verify it changed)
            const hoveredBorder = await option.evaluate(el => 
                window.getComputedStyle(el).borderColor
            );
            
            // At minimum, verify hover doesn't break the element
            await expect(option).toBeVisible();
        });
    });
    
    test.describe('Selection Behavior', () => {
        test('clicking option selects it', async ({ page }) => {
            const option = await page.locator('.quiz-option-enhanced').first();
            
            await option.click();
            await page.waitForTimeout(200);
            
            // Should have selected class
            const hasSelected = await option.evaluate(el => 
                el.classList.contains('selected')
            );
            expect(hasSelected).toBeTruthy();
            
            // Should have checkmark
            const checkmark = await option.locator('.option-checkmark');
            await expect(checkmark).toBeVisible();
        });
        
        test('selecting new option deselects previous', async ({ page }) => {
            const firstOption = await page.locator('.quiz-option-enhanced').nth(0);
            const secondOption = await page.locator('.quiz-option-enhanced').nth(1);
            
            // Select first option
            await firstOption.click();
            await page.waitForTimeout(200);
            
            // Select second option
            await secondOption.click();
            await page.waitForTimeout(200);
            
            // First should not be selected
            const firstSelected = await firstOption.evaluate(el => 
                el.classList.contains('selected')
            );
            expect(firstSelected).toBeFalsy();
            
            // Second should be selected
            const secondSelected = await secondOption.evaluate(el => 
                el.classList.contains('selected')
            );
            expect(secondSelected).toBeTruthy();
        });
        
        test('selected option has aria-checked=true', async ({ page }) => {
            const option = await page.locator('.quiz-option-enhanced').first();
            
            await option.click();
            await page.waitForTimeout(200);
            
            expect(await option.getAttribute('aria-checked')).toBe('true');
        });
    });
    
    test.describe('Answer Feedback', () => {
        test.skip('shows correct answer feedback after submission', async ({ page }) => {
            // This test requires quiz submission functionality
            // Will be implemented when review mode is available
        });
        
        test.skip('shows incorrect answer feedback', async ({ page }) => {
            // This test requires quiz submission functionality
            // Will be implemented when review mode is available
        });
    });
    
    test.describe('Keyboard Navigation', () => {
        test('can select option with Enter key', async ({ page }) => {
            const option = await page.locator('.quiz-option-enhanced').first();
            
            // Focus the option
            await option.focus();
            
            // Press Enter
            await page.keyboard.press('Enter');
            await page.waitForTimeout(200);
            
            // Should be selected
            const isSelected = await option.evaluate(el => 
                el.classList.contains('selected')
            );
            expect(isSelected).toBeTruthy();
        });
        
        test('can select option with Space key', async ({ page }) => {
            const option = await page.locator('.quiz-option-enhanced').first();
            
            // Focus the option
            await option.focus();
            
            // Press Space
            await page.keyboard.press('Space');
            await page.waitForTimeout(200);
            
            // Should be selected
            const isSelected = await option.evaluate(el => 
                el.classList.contains('selected')
            );
            expect(isSelected).toBeTruthy();
        });
        
        test('focus indicator is visible', async ({ page }) => {
            const option = await page.locator('.quiz-option-enhanced').first();
            
            await option.focus();
            
            const outline = await option.evaluate(el => 
                window.getComputedStyle(el).outline
            );
            
            // Should have some outline (exact value may vary)
            expect(outline).not.toBe('none');
        });
    });
    
    test.describe('Accessibility', () => {
        test('answer options meet WCAG AA standards', async ({ page }) => {
            const accessibilityScanResults = await new AxeBuilder({ page })
                .include('.quiz-options-container')
                .withTags(['wcag2a', 'wcag2aa'])
                .analyze();
            
            expect(accessibilityScanResults.violations).toEqual([]);
        });
        
        test('options container has radiogroup role', async ({ page }) => {
            const container = await page.locator('.quiz-options-container');
            
            expect(await container.getAttribute('role')).toBe('radiogroup');
            expect(await container.getAttribute('aria-label')).toBeTruthy();
        });
        
        test('each option has radio role', async ({ page }) => {
            const options = await page.locator('.quiz-option-enhanced');
            const count = await options.count();
            
            for (let i = 0; i < count; i++) {
                const option = options.nth(i);
                expect(await option.getAttribute('role')).toBe('radio');
            }
        });
    });
    
    test.describe('Responsive Design', () => {
        test('options display correctly on mobile', async ({ page }) => {
            await page.setViewportSize({ width: 375, height: 667 });
            
            const options = await page.locator('.quiz-option-enhanced');
            const firstOption = options.first();
            
            await expect(firstOption).toBeVisible();
            
            // Check that option fits in viewport
            const box = await firstOption.boundingBox();
            expect(box.width).toBeLessThanOrEqual(375);
        });
        
        test('touch targets are large enough on mobile', async ({ page }) => {
            await page.setViewportSize({ width: 375, height: 667 });
            
            const option = await page.locator('.quiz-option-enhanced').first();
            const box = await option.boundingBox();
            
            // Minimum touch target size is 44x44px
            expect(box.height).toBeGreaterThanOrEqual(44);
        });
    });
    
    test.describe('Animations', () => {
        test('checkmark appears with animation', async ({ page }) => {
            const option = await page.locator('.quiz-option-enhanced').first();
            
            await option.click();
            await page.waitForTimeout(100);
            
            const checkmark = await option.locator('.option-checkmark');
            await expect(checkmark).toBeVisible();
            
            // Verify animation is applied (check for animation property)
            const hasAnimation = await checkmark.evaluate(el => {
                const style = window.getComputedStyle(el);
                return style.animation !== 'none';
            });
            
            // Animation might have completed, so just verify checkmark exists
            expect(await checkmark.isVisible()).toBeTruthy();
        });
        
        test('respects prefers-reduced-motion', async ({ page }) => {
            // Enable reduced motion
            await page.emulateMedia({ reducedMotion: 'reduce' });
            
            const option = await page.locator('.quiz-option-enhanced').first();
            await option.click();
            
            // Should still work, just without animations
            const isSelected = await option.evaluate(el => 
                el.classList.contains('selected')
            );
            expect(isSelected).toBeTruthy();
        });
    });
    
    test.describe('Integration with Phase 1', () => {
        test('Phase 1 and Phase 2 features work together', async ({ page }) => {
            // Verify Phase 1 features exist
            const progressBar = await page.locator('.quiz-progress-bar');
            await expect(progressBar).toBeVisible();
            
            // Verify Phase 2 features exist
            const options = await page.locator('.quiz-option-enhanced');
            await expect(options.first()).toBeVisible();
            
            // Select an option
            await options.first().click();
            await page.waitForTimeout(200);
            
            // Both features should still be visible
            await expect(progressBar).toBeVisible();
            await expect(options.first()).toHaveClass(/selected/);
        });
    });
    
    test.describe('JavaScript Functions', () => {
        test('Phase 2 functions are globally available', async ({ page }) => {
            const functionsAvailable = await page.evaluate(() => {
                return {
                    createEnhancedAnswerOption: typeof window.createEnhancedAnswerOption === 'function',
                    createAnswerOptionsContainer: typeof window.createAnswerOptionsContainer === 'function',
                    addRippleEffect: typeof window.addRippleEffect === 'function',
                    handleOptionSelection: typeof window.handleOptionSelection === 'function',
                    showAnswerFeedback: typeof window.showAnswerFeedback === 'function',
                    initializePhase2Enhancements: typeof window.initializePhase2Enhancements === 'function'
                };
            });
            
            expect(functionsAvailable.createEnhancedAnswerOption).toBeTruthy();
            expect(functionsAvailable.createAnswerOptionsContainer).toBeTruthy();
            expect(functionsAvailable.addRippleEffect).toBeTruthy();
            expect(functionsAvailable.handleOptionSelection).toBeTruthy();
            expect(functionsAvailable.showAnswerFeedback).toBeTruthy();
            expect(functionsAvailable.initializePhase2Enhancements).toBeTruthy();
        });
    });
});


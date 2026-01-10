/**
 * E2E tests for Criminal Law Part A/B selector functionality
 * 
 * Tests the part selector UI component that allows students to filter
 * weeks by Part A (Substantive), Part B (Procedure), or Mixed mode.
 */

const { test, expect } = require('@playwright/test');

test.describe('Criminal Law Part Selector', () => {
    test.beforeEach(async ({ page }) => {
        // Navigate to the study portal
        await page.goto('/');
        
        // Wait for page to load
        await page.waitForLoadState('networkidle');
        
        // Select Criminal Law course (CRIM-2025-2026)
        // This assumes the course selector is available
        const courseSelector = page.locator('#course-selector');
        if (await courseSelector.isVisible()) {
            await courseSelector.selectOption('CRIM-2025-2026');
            await page.waitForTimeout(1000); // Wait for course to load
        }
        
        // Navigate to Weekly Content section
        const weeklyContentTab = page.locator('button.nav-tab:has-text("Weekly Content")');
        if (await weeklyContentTab.isVisible()) {
            await weeklyContentTab.click();
            await page.waitForTimeout(500);
        }
    });

    test('part selector is visible for Criminal Law course', async ({ page }) => {
        // Part selector should be visible
        const partSelector = page.locator('#part-selector');
        await expect(partSelector).toBeVisible();
        
        // Should have 3 tabs
        const partTabs = page.locator('.part-tab');
        await expect(partTabs).toHaveCount(3);
        
        // Check tab labels
        await expect(partTabs.nth(0)).toContainText('Part A');
        await expect(partTabs.nth(1)).toContainText('Part B');
        await expect(partTabs.nth(2)).toContainText('Mixed');
    });

    test('Part A tab is active by default', async ({ page }) => {
        const partATab = page.locator('.part-tab[data-part="A"]');
        await expect(partATab).toHaveClass(/active/);
    });

    test('clicking Part A shows only Part A weeks', async ({ page }) => {
        // Click Part A tab
        const partATab = page.locator('.part-tab[data-part="A"]');
        await partATab.click();
        await page.waitForTimeout(500);
        
        // Check that only Part A weeks are shown
        const weekCards = page.locator('.week-card');
        const count = await weekCards.count();
        
        // Should have 6 Part A weeks
        expect(count).toBe(6);
        
        // Check that all visible weeks are Part A
        for (let i = 0; i < count; i++) {
            const weekLabel = await weekCards.nth(i).locator('.week-label').textContent();
            expect(weekLabel).toContain('Part A');
        }
    });

    test('clicking Part B shows only Part B weeks', async ({ page }) => {
        // Click Part B tab
        const partBTab = page.locator('.part-tab[data-part="B"]');
        await partBTab.click();
        await page.waitForTimeout(500);
        
        // Check that only Part B weeks are shown
        const weekCards = page.locator('.week-card');
        const count = await weekCards.count();
        
        // Should have 6 Part B weeks
        expect(count).toBe(6);
        
        // Check that all visible weeks are Part B
        for (let i = 0; i < count; i++) {
            const weekLabel = await weekCards.nth(i).locator('.week-label').textContent();
            expect(weekLabel).toContain('Part B');
        }
    });

    test('clicking Mixed shows all weeks', async ({ page }) => {
        // Click Mixed tab
        const mixedTab = page.locator('.part-tab[data-part="mixed"]');
        await mixedTab.click();
        await page.waitForTimeout(500);
        
        // Check that all weeks are shown
        const weekCards = page.locator('.week-card');
        const count = await weekCards.count();
        
        // Should have 12 weeks total (6 Part A + 6 Part B)
        expect(count).toBe(12);
    });

    test('active tab is highlighted correctly', async ({ page }) => {
        const partATab = page.locator('.part-tab[data-part="A"]');
        const partBTab = page.locator('.part-tab[data-part="B"]');
        const mixedTab = page.locator('.part-tab[data-part="mixed"]');
        
        // Part A should be active initially
        await expect(partATab).toHaveClass(/active/);
        await expect(partBTab).not.toHaveClass(/active/);
        await expect(mixedTab).not.toHaveClass(/active/);
        
        // Click Part B
        await partBTab.click();
        await page.waitForTimeout(300);
        
        // Part B should be active
        await expect(partATab).not.toHaveClass(/active/);
        await expect(partBTab).toHaveClass(/active/);
        await expect(mixedTab).not.toHaveClass(/active/);
        
        // Click Mixed
        await mixedTab.click();
        await page.waitForTimeout(300);
        
        // Mixed should be active
        await expect(partATab).not.toHaveClass(/active/);
        await expect(partBTab).not.toHaveClass(/active/);
        await expect(mixedTab).toHaveClass(/active/);
    });

    test('week cards display correct part labels', async ({ page }) => {
        // Check Part A weeks
        const partATab = page.locator('.part-tab[data-part="A"]');
        await partATab.click();
        await page.waitForTimeout(500);
        
        const firstWeekLabel = await page.locator('.week-card').first().locator('.week-label').textContent();
        expect(firstWeekLabel).toMatch(/Week \d+ - Part A/);
        
        // Check Part B weeks
        const partBTab = page.locator('.part-tab[data-part="B"]');
        await partBTab.click();
        await page.waitForTimeout(500);
        
        const firstPartBLabel = await page.locator('.week-card').first().locator('.week-label').textContent();
        expect(firstPartBLabel).toMatch(/Week \d+ - Part B/);
    });

    test('switching between parts preserves week card functionality', async ({ page }) => {
        // Click Part A
        const partATab = page.locator('.part-tab[data-part="A"]');
        await partATab.click();
        await page.waitForTimeout(500);
        
        // Click first week card
        const firstWeek = page.locator('.week-card').first();
        await firstWeek.click();
        
        // Should open week study notes modal (or navigate)
        // This depends on your implementation
        // Add appropriate assertion here
        
        // Close modal if opened
        const closeButton = page.locator('.modal-close, .close-button');
        if (await closeButton.isVisible()) {
            await closeButton.click();
        }
        
        // Switch to Part B
        const partBTab = page.locator('.part-tab[data-part="B"]');
        await partBTab.click();
        await page.waitForTimeout(500);
        
        // Click first Part B week card
        const firstPartBWeek = page.locator('.week-card').first();
        await firstPartBWeek.click();
        
        // Should also work
        // Add appropriate assertion here
    });

    test('part selector is responsive on mobile', async ({ page }) => {
        // Set mobile viewport
        await page.setViewportSize({ width: 375, height: 667 });
        
        // Part selector should still be visible
        const partSelector = page.locator('#part-selector');
        await expect(partSelector).toBeVisible();
        
        // Tabs should be visible and clickable
        const partTabs = page.locator('.part-tab');
        await expect(partTabs).toHaveCount(3);
        
        // Click Part B on mobile
        const partBTab = page.locator('.part-tab[data-part="B"]');
        await partBTab.click();
        await page.waitForTimeout(500);
        
        // Should filter correctly
        const weekCards = page.locator('.week-card');
        const count = await weekCards.count();
        expect(count).toBe(6);
    });

    test('part selector has proper ARIA labels', async ({ page }) => {
        const partATab = page.locator('.part-tab[data-part="A"]');
        const partBTab = page.locator('.part-tab[data-part="B"]');
        const mixedTab = page.locator('.part-tab[data-part="mixed"]');
        
        // Check for accessibility attributes
        // Note: Add these attributes in the implementation
        await expect(partATab).toHaveAttribute('role', 'tab');
        await expect(partBTab).toHaveAttribute('role', 'tab');
        await expect(mixedTab).toHaveAttribute('role', 'tab');
    });

    test('no JavaScript errors when switching parts', async ({ page }) => {
        const errors = [];
        page.on('console', msg => {
            if (msg.type() === 'error') {
                errors.push(msg.text());
            }
        });
        
        // Switch between all parts
        await page.locator('.part-tab[data-part="A"]').click();
        await page.waitForTimeout(300);
        
        await page.locator('.part-tab[data-part="B"]').click();
        await page.waitForTimeout(300);
        
        await page.locator('.part-tab[data-part="mixed"]').click();
        await page.waitForTimeout(300);
        
        // Should have no errors
        expect(errors).toHaveLength(0);
    });

    test('part selector state persists during session', async ({ page }) => {
        // Select Part B
        const partBTab = page.locator('.part-tab[data-part="B"]');
        await partBTab.click();
        await page.waitForTimeout(500);
        
        // Navigate to another tab
        const quizTab = page.locator('button.nav-tab:has-text("Quiz")');
        if (await quizTab.isVisible()) {
            await quizTab.click();
            await page.waitForTimeout(500);
        }
        
        // Navigate back to Weekly Content
        const weeklyContentTab = page.locator('button.nav-tab:has-text("Weekly Content")');
        await weeklyContentTab.click();
        await page.waitForTimeout(500);
        
        // Part B should still be selected
        // Note: This depends on whether you implement state persistence
        // Adjust assertion based on your implementation
        const partBTabAfter = page.locator('.part-tab[data-part="B"]');
        // await expect(partBTabAfter).toHaveClass(/active/);
    });
});

test.describe('Part Selector Edge Cases', () => {
    test('handles course without parts gracefully', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        
        // Select a course without parts (e.g., LLS-2025-2026)
        const courseSelector = page.locator('#course-selector');
        if (await courseSelector.isVisible()) {
            await courseSelector.selectOption('LLS-2025-2026');
            await page.waitForTimeout(1000);
        }
        
        // Navigate to Weekly Content
        const weeklyContentTab = page.locator('button.nav-tab:has-text("Weekly Content")');
        if (await weeklyContentTab.isVisible()) {
            await weeklyContentTab.click();
            await page.waitForTimeout(500);
        }
        
        // Part selector should NOT be visible
        const partSelector = page.locator('#part-selector');
        await expect(partSelector).not.toBeVisible();
    });

    test('handles empty weeks array', async ({ page }) => {
        // This would require mocking the API response
        // Add test if you implement API mocking
    });
});


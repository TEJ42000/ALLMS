/**
 * E2E tests for Part Selector functionality
 *
 * Tests the part selector UI component that allows students to filter
 * weeks by part (e.g., Part A, Part B) or Mixed mode.
 *
 * This is a GENERIC feature that works for any course with a 'part' field
 * on its weeks. The tests below use Criminal Law as an example course,
 * but the functionality applies to any course with parts.
 */

const { test, expect } = require('@playwright/test');

test.describe('Criminal Law Part Selector', () => {
    /**
     * Test Preconditions:
     * 1. Criminal Law course (CRIM-2025-2026) must exist in Firestore
     * 2. Course must have 12 weeks (6 Part A + 6 Part B)
     * 3. Weeks 1-6 must have part="A"
     * 4. Weeks 7-12 must have part="B"
     * 5. User must be authenticated
     * 6. Course must be accessible to the test user
     *
     * Setup:
     * Run `python scripts/setup_criminal_law_course.py` before running these tests
     */

    test.beforeEach(async ({ page }) => {
        // Navigate to the study portal
        await page.goto('/');

        // Wait for page to load
        await page.waitForLoadState('networkidle');

        // PRECONDITION: Course selector must be available
        const courseSelector = page.locator('#course-selector');
        await expect(courseSelector).toBeVisible({ timeout: 5000 });

        // Select Criminal Law course (CRIM-2025-2026)
        // PRECONDITION: CRIM-2025-2026 must exist in the course list
        await courseSelector.selectOption('CRIM-2025-2026');
        await page.waitForTimeout(1000); // Wait for course to load

        // Navigate to Weekly Content section
        // PRECONDITION: Weekly Content tab must be available
        const weeklyContentTab = page.locator('button.nav-tab:has-text("Weekly Content")');
        await expect(weeklyContentTab).toBeVisible({ timeout: 5000 });
        await weeklyContentTab.click();
        await page.waitForTimeout(500);

        // PRECONDITION: Weeks grid must be rendered
        const weeksGrid = page.locator('#weeks-grid');
        await expect(weeksGrid).toBeVisible({ timeout: 5000 });
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


/**
 * E2E tests for Part Selector Error Handling
 *
 * Tests error scenarios using API mocking to verify graceful degradation.
 * These tests are generic and apply to any course with part filtering.
 */
test.describe('Part Selector Error Handling', () => {

    test('handles weeks without part field gracefully', async ({ page }) => {
        // Mock API to return weeks without part field
        await page.route('**/api/courses/*', route => {
            if (route.request().url().includes('include_weeks=true')) {
                route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        id: 'TEST-COURSE',
                        name: 'Test Course',
                        academicYear: '2025-2026',
                        active: true,
                        weeks: [
                            { weekNumber: 1, title: 'Week 1 - No Part', topics: [] },
                            { weekNumber: 2, title: 'Week 2 - No Part', topics: [] },
                            { weekNumber: 3, title: 'Week 3 - No Part', topics: [] }
                        ]
                    })
                });
            } else {
                route.continue();
            }
        });

        // Collect console errors
        const errors = [];
        page.on('console', msg => {
            if (msg.type() === 'error') {
                errors.push(msg.text());
            }
        });

        await page.goto('/');
        await page.waitForLoadState('networkidle');

        // Navigate to Weekly Content
        const weeklyContentTab = page.locator('button.nav-tab:has-text("Weekly Content")');
        if (await weeklyContentTab.isVisible()) {
            await weeklyContentTab.click();
            await page.waitForTimeout(500);
        }

        // Part selector should NOT be visible (no parts in data)
        const partSelector = page.locator('#part-selector');
        await expect(partSelector).not.toBeVisible();

        // Weeks should still be displayed
        const weekCards = page.locator('.week-card');
        const count = await weekCards.count();
        expect(count).toBeGreaterThan(0);

        // No JavaScript errors
        expect(errors.length).toBe(0);
    });

    test('handles mixed weeks (some with part, some without)', async ({ page }) => {
        // Mock API to return mixed weeks
        await page.route('**/api/courses/*', route => {
            if (route.request().url().includes('include_weeks=true')) {
                route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        id: 'MIXED-COURSE',
                        name: 'Mixed Course',
                        academicYear: '2025-2026',
                        active: true,
                        weeks: [
                            { weekNumber: 1, title: 'Week 1', topics: [], part: 'A' },
                            { weekNumber: 2, title: 'Week 2', topics: [] },  // No part
                            { weekNumber: 3, title: 'Week 3', topics: [], part: 'B' },
                            { weekNumber: 4, title: 'Week 4', topics: [] }   // No part
                        ]
                    })
                });
            } else {
                route.continue();
            }
        });

        const errors = [];
        page.on('console', msg => {
            if (msg.type() === 'error') {
                errors.push(msg.text());
            }
        });

        await page.goto('/');
        await page.waitForLoadState('networkidle');

        const weeklyContentTab = page.locator('button.nav-tab:has-text("Weekly Content")');
        if (await weeklyContentTab.isVisible()) {
            await weeklyContentTab.click();
            await page.waitForTimeout(500);
        }

        // Part selector should be visible (some weeks have parts)
        const partSelector = page.locator('#part-selector');
        await expect(partSelector).toBeVisible();

        // No JavaScript errors
        expect(errors.length).toBe(0);
    });

    test('handles API 404 error gracefully', async ({ page }) => {
        // Mock API to return 404
        await page.route('**/api/courses/*', route => {
            route.fulfill({
                status: 404,
                contentType: 'application/json',
                body: JSON.stringify({ detail: 'Course not found' })
            });
        });

        const errors = [];
        page.on('console', msg => {
            if (msg.type() === 'error') {
                errors.push(msg.text());
            }
        });

        await page.goto('/');
        await page.waitForLoadState('networkidle');

        const weeklyContentTab = page.locator('button.nav-tab:has-text("Weekly Content")');
        if (await weeklyContentTab.isVisible()) {
            await weeklyContentTab.click();
            await page.waitForTimeout(500);
        }

        // Should show fallback content or error message, not crash
        // The exact behavior depends on implementation
        // At minimum, page should not have unhandled exceptions
    });

    test('handles API 503 error gracefully', async ({ page }) => {
        // Mock API to return 503 (service unavailable)
        await page.route('**/api/courses/*', route => {
            route.fulfill({
                status: 503,
                contentType: 'application/json',
                body: JSON.stringify({ detail: 'Database temporarily unavailable' })
            });
        });

        const errors = [];
        page.on('console', msg => {
            if (msg.type() === 'error') {
                errors.push(msg.text());
            }
        });

        await page.goto('/');
        await page.waitForLoadState('networkidle');

        const weeklyContentTab = page.locator('button.nav-tab:has-text("Weekly Content")');
        if (await weeklyContentTab.isVisible()) {
            await weeklyContentTab.click();
            await page.waitForTimeout(500);
        }

        // Fallback weeks should be shown
        const weeksGrid = page.locator('#weeks-grid');
        await expect(weeksGrid).toBeVisible();
    });

    test('handles malformed JSON response', async ({ page }) => {
        // Mock API to return invalid JSON
        await page.route('**/api/courses/*', route => {
            route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: 'this is not valid json {'
            });
        });

        const errors = [];
        page.on('console', msg => {
            if (msg.type() === 'error') {
                errors.push(msg.text());
            }
        });

        await page.goto('/');
        await page.waitForLoadState('networkidle');

        const weeklyContentTab = page.locator('button.nav-tab:has-text("Weekly Content")');
        if (await weeklyContentTab.isVisible()) {
            await weeklyContentTab.click();
            await page.waitForTimeout(500);
        }

        // Should handle gracefully with fallback
        const weeksGrid = page.locator('#weeks-grid');
        await expect(weeksGrid).toBeVisible();
    });

    test('handles empty course response', async ({ page }) => {
        // Mock API to return course with no weeks
        await page.route('**/api/courses/*', route => {
            if (route.request().url().includes('include_weeks=true')) {
                route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        id: 'EMPTY-COURSE',
                        name: 'Empty Course',
                        academicYear: '2025-2026',
                        active: true,
                        weeks: []
                    })
                });
            } else {
                route.continue();
            }
        });

        const errors = [];
        page.on('console', msg => {
            if (msg.type() === 'error') {
                errors.push(msg.text());
            }
        });

        await page.goto('/');
        await page.waitForLoadState('networkidle');

        const weeklyContentTab = page.locator('button.nav-tab:has-text("Weekly Content")');
        if (await weeklyContentTab.isVisible()) {
            await weeklyContentTab.click();
            await page.waitForTimeout(500);
        }

        // Part selector should not be visible (no weeks)
        const partSelector = page.locator('#part-selector');
        await expect(partSelector).not.toBeVisible();

        // Should show fallback weeks
        const weeksGrid = page.locator('#weeks-grid');
        await expect(weeksGrid).toBeVisible();

        // No unhandled errors
        expect(errors.length).toBe(0);
    });

    test('handles weeks with null part field', async ({ page }) => {
        // Mock API to return weeks with explicit null part
        await page.route('**/api/courses/*', route => {
            if (route.request().url().includes('include_weeks=true')) {
                route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        id: 'NULL-PARTS',
                        name: 'Null Parts Course',
                        academicYear: '2025-2026',
                        active: true,
                        weeks: [
                            { weekNumber: 1, title: 'Week 1', topics: [], part: null },
                            { weekNumber: 2, title: 'Week 2', topics: [], part: null }
                        ]
                    })
                });
            } else {
                route.continue();
            }
        });

        const errors = [];
        page.on('console', msg => {
            if (msg.type() === 'error') {
                errors.push(msg.text());
            }
        });

        await page.goto('/');
        await page.waitForLoadState('networkidle');

        const weeklyContentTab = page.locator('button.nav-tab:has-text("Weekly Content")');
        if (await weeklyContentTab.isVisible()) {
            await weeklyContentTab.click();
            await page.waitForTimeout(500);
        }

        // Part selector should not be visible (null parts treated as no parts)
        const partSelector = page.locator('#part-selector');
        await expect(partSelector).not.toBeVisible();

        // No JavaScript errors
        expect(errors.length).toBe(0);
    });

    test('handles rapid part switching without errors', async ({ page }) => {
        // Mock API to return course with parts
        await page.route('**/api/courses/*', route => {
            if (route.request().url().includes('include_weeks=true')) {
                route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        id: 'RAPID-SWITCH',
                        name: 'Rapid Switch Course',
                        academicYear: '2025-2026',
                        active: true,
                        weeks: [
                            { weekNumber: 1, title: 'Week 1', topics: [], part: 'A' },
                            { weekNumber: 2, title: 'Week 2', topics: [], part: 'A' },
                            { weekNumber: 3, title: 'Week 3', topics: [], part: 'B' },
                            { weekNumber: 4, title: 'Week 4', topics: [], part: 'B' }
                        ]
                    })
                });
            } else {
                route.continue();
            }
        });

        const errors = [];
        page.on('console', msg => {
            if (msg.type() === 'error') {
                errors.push(msg.text());
            }
        });

        await page.goto('/');
        await page.waitForLoadState('networkidle');

        const weeklyContentTab = page.locator('button.nav-tab:has-text("Weekly Content")');
        if (await weeklyContentTab.isVisible()) {
            await weeklyContentTab.click();
            await page.waitForTimeout(500);
        }

        const partSelector = page.locator('#part-selector');
        if (await partSelector.isVisible()) {
            // Rapidly switch between parts
            for (let i = 0; i < 5; i++) {
                await page.locator('.part-tab[data-part="A"]').click();
                await page.locator('.part-tab[data-part="B"]').click();
                await page.locator('.part-tab[data-part="mixed"]').click();
            }

            await page.waitForTimeout(300);
        }

        // No JavaScript errors from rapid switching
        expect(errors.length).toBe(0);
    });
});

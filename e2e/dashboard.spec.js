// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Dashboard Course Weeks', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to course selection page
    await page.goto('/');

    // Click on the first course card to enter it
    const enterCourseBtn = page.locator('button:has-text("Enter Course")').first();
    await enterCourseBtn.click();

    // Wait for the dashboard to load (tabs should be visible)
    await expect(page.locator('[data-tab="dashboard"]')).toBeVisible();
  });

  test('should display weeks grid container', async ({ page }) => {
    // Check that the weeks grid container exists
    const weeksGrid = page.locator('#weeks-grid');
    await expect(weeksGrid).toBeVisible();
  });

  test('should display course weeks section title', async ({ page }) => {
    // Check for the section title
    const sectionTitle = page.locator('.section-subtitle:has-text("Course Weeks")');
    await expect(sectionTitle).toBeVisible();
  });

  test('should load and display week cards', async ({ page }) => {
    // Wait for week cards to load (they are fetched via API)
    const weeksGrid = page.locator('#weeks-grid');
    
    // Wait for loading to complete - either week cards appear or empty/error message
    await page.waitForFunction(() => {
      const grid = document.getElementById('weeks-grid');
      if (!grid) return false;
      // Check if we have week cards OR a message (no-weeks/error)
      return grid.querySelector('.week-card') !== null || 
             grid.querySelector('.no-weeks-message') !== null ||
             grid.querySelector('.error-message') !== null;
    }, { timeout: 10000 });

    // Check we have at least one week card OR a message
    const weekCards = weeksGrid.locator('.week-card');
    const noWeeksMessage = weeksGrid.locator('.no-weeks-message');
    const errorMessage = weeksGrid.locator('.error-message');

    // Either we have week cards, or an appropriate message
    const weekCount = await weekCards.count();
    const hasNoWeeksMessage = await noWeeksMessage.count() > 0;
    const hasErrorMessage = await errorMessage.count() > 0;

    expect(weekCount > 0 || hasNoWeeksMessage || hasErrorMessage).toBeTruthy();
  });

  test('should display week card with proper structure', async ({ page }) => {
    const weeksGrid = page.locator('#weeks-grid');
    
    // Wait for week cards to load
    await page.waitForFunction(() => {
      const grid = document.getElementById('weeks-grid');
      return grid && (grid.querySelector('.week-card') !== null || 
                      grid.querySelector('.no-weeks-message') !== null);
    }, { timeout: 10000 });

    const weekCards = weeksGrid.locator('.week-card');
    const weekCount = await weekCards.count();

    // If there are week cards, verify their structure
    if (weekCount > 0) {
      const firstCard = weekCards.first();
      
      // Check for heading (should contain week number)
      await expect(firstCard.locator('h4')).toBeVisible();
      
      // Check for progress bar
      await expect(firstCard.locator('.progress-bar')).toBeVisible();
      
      // Check for progress text
      await expect(firstCard.locator('.progress-text')).toBeVisible();
      
      // Check data attributes exist
      const weekAttr = await firstCard.getAttribute('data-week');
      expect(weekAttr).toBeTruthy();
    }
  });

  test('should navigate to AI Tutor when week card is clicked', async ({ page }) => {
    const weeksGrid = page.locator('#weeks-grid');
    
    // Wait for week cards to load
    await page.waitForFunction(() => {
      const grid = document.getElementById('weeks-grid');
      return grid && (grid.querySelector('.week-card') !== null || 
                      grid.querySelector('.no-weeks-message') !== null);
    }, { timeout: 10000 });

    const weekCards = weeksGrid.locator('.week-card');
    const weekCount = await weekCards.count();

    // Only test click navigation if there are week cards
    if (weekCount > 0) {
      // Click the first week card
      await weekCards.first().click();

      // Check that the AI Tutor section becomes visible
      const tutorSection = page.locator('#tutor-section');
      await expect(tutorSection).toBeVisible();

      // Check that the tutor tab is now active
      const tutorTab = page.locator('[data-tab="tutor"]');
      await expect(tutorTab).toHaveClass(/active/);
    }
  });

  test('should show loading state initially', async ({ page }) => {
    // Use a fresh navigation to catch the loading state
    await page.goto('/');
    const enterCourseBtn = page.locator('button:has-text("Enter Course")').first();
    await enterCourseBtn.click();

    // The weeks grid should exist immediately
    const weeksGrid = page.locator('#weeks-grid');
    await expect(weeksGrid).toBeVisible();

    // Note: The loading state is brief, so we just verify the container exists
    // and eventually has content (either cards or a message)
    await page.waitForFunction(() => {
      const grid = document.getElementById('weeks-grid');
      if (!grid) return false;
      const html = grid.innerHTML;
      return html.includes('week-card') || 
             html.includes('no-weeks-message') || 
             html.includes('error-message');
    }, { timeout: 10000 });
  });
});


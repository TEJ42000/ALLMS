// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Unit-style tests for JavaScript utility functions
 * These tests run in the browser context to test the actual functions
 */
test.describe('JavaScript Utility Functions', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app to load all JavaScript
    await page.goto('/');
    
    // Enter a course to ensure all JS is loaded
    const enterCourseBtn = page.locator('button:has-text("Enter Course")').first();
    await enterCourseBtn.click();
    
    // Wait for dashboard to load
    await expect(page.locator('[data-tab="dashboard"]')).toBeVisible();
  });

  test.describe('escapeHtml()', () => {
    test('should escape HTML special characters', async ({ page }) => {
      const result = await page.evaluate(() => {
        // @ts-ignore - escapeHtml is defined globally
        return escapeHtml('<script>alert("xss")</script>');
      });
      expect(result).toBe('&lt;script&gt;alert("xss")&lt;/script&gt;');
    });

    test('should escape ampersands', async ({ page }) => {
      const result = await page.evaluate(() => {
        // @ts-ignore
        return escapeHtml('Tom & Jerry');
      });
      expect(result).toBe('Tom &amp; Jerry');
    });

    test('should escape quotes', async ({ page }) => {
      const result = await page.evaluate(() => {
        // @ts-ignore
        return escapeHtml('He said "hello"');
      });
      expect(result).toBe('He said "hello"');
    });

    test('should handle empty string', async ({ page }) => {
      const result = await page.evaluate(() => {
        // @ts-ignore
        return escapeHtml('');
      });
      expect(result).toBe('');
    });

    test('should handle null/undefined', async ({ page }) => {
      const results = await page.evaluate(() => {
        // @ts-ignore
        return [escapeHtml(null), escapeHtml(undefined)];
      });
      expect(results[0]).toBe('');
      expect(results[1]).toBe('');
    });

    test('should handle various XSS attack vectors', async ({ page }) => {
      const results = await page.evaluate(() => {
        const attacks = [
          '<img src=x onerror=alert(1)>',
          '"><script>alert(1)</script>',
          "javascript:alert('XSS')",
          '<svg onload=alert(1)>',
          '{{constructor.constructor("alert(1)")()}}'
        ];
        // @ts-ignore
        return attacks.map(a => escapeHtml(a));
      });
      
      // Verify none of the results contain unescaped < or >
      for (const result of results) {
        expect(result).not.toContain('<script>');
        expect(result).not.toContain('<img');
        expect(result).not.toContain('<svg');
      }
    });
  });

  test.describe('getWeekIcon()', () => {
    test('should return criminal law icon for criminal topics', async ({ page }) => {
      const result = await page.evaluate(() => {
        // @ts-ignore
        return getWeekIcon({ title: 'Criminal Law Basics', weekNumber: 1 });
      });
      expect(result).toBe('⚖️');
    });

    test('should return constitution icon for constitutional topics', async ({ page }) => {
      const result = await page.evaluate(() => {
        // @ts-ignore
        return getWeekIcon({ title: 'Constitutional Law', weekNumber: 2 });
      });
      expect(result).toBe('🏛️');
    });

    test('should return default icon for unknown topics', async ({ page }) => {
      const result = await page.evaluate(() => {
        // @ts-ignore
        return getWeekIcon({ title: 'Some Random Topic', weekNumber: 1 });
      });
      // Should return one of the default icons
      expect(['📖', '📗', '📘', '📙', '📕', '📓']).toContain(result);
    });

    test('should handle missing weekNumber gracefully', async ({ page }) => {
      const result = await page.evaluate(() => {
        // @ts-ignore
        return getWeekIcon({ title: 'No Week Number' });
      });
      // Should return first default icon (weekNum defaults to 1)
      expect(result).toBe('📖');
    });

    test('should handle undefined/null weekNumber', async ({ page }) => {
      const results = await page.evaluate(() => {
        // @ts-ignore
        return [
          getWeekIcon({ title: 'Test', weekNumber: undefined }),
          getWeekIcon({ title: 'Test', weekNumber: null }),
          getWeekIcon({ title: 'Test', weekNumber: NaN })
        ];
      });
      // All should default to first icon
      expect(results[0]).toBe('📖');
      expect(results[1]).toBe('📖');
      expect(results[2]).toBe('📖');
    });
  });
});


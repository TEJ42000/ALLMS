// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Quiz System', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to course selection page
    await page.goto('/');

    // Click on the first course card to enter it
    const enterCourseBtn = page.locator('button:has-text("Enter Course")').first();
    await enterCourseBtn.click();

    // Wait for the course page to load (tabs should be visible)
    await expect(page.locator('[data-tab="quiz"]')).toBeVisible();

    // Click on the Quiz tab to navigate to quiz section
    await page.click('[data-tab="quiz"]');

    // Wait for the quiz section to be visible
    await expect(page.locator('#quiz-section')).toBeVisible();
  });

  test('should display quiz section after clicking quiz tab', async ({ page }) => {
    // Check that the quiz section exists and is visible
    const quizSection = page.locator('#quiz-section');
    await expect(quizSection).toBeVisible();

    // Check for quiz topic selector
    const topicSelect = page.locator('#quiz-topic-select');
    await expect(topicSelect).toBeVisible();

    // Check for difficulty selector
    const difficultySelect = page.locator('#quiz-difficulty-select');
    await expect(difficultySelect).toBeVisible();

    // Check for start quiz button
    const startBtn = page.locator('#start-quiz-btn');
    await expect(startBtn).toBeVisible();
  });

  test('should have difficulty options', async ({ page }) => {
    const difficultySelect = page.locator('#quiz-difficulty-select');

    // Check all difficulty options exist
    await expect(difficultySelect.locator('option[value="easy"]')).toHaveCount(1);
    await expect(difficultySelect.locator('option[value="medium"]')).toHaveCount(1);
    await expect(difficultySelect.locator('option[value="hard"]')).toHaveCount(1);

    // Check medium is selected by default
    await expect(difficultySelect).toHaveValue('medium');
  });

  test('should have topic options', async ({ page }) => {
    const topicSelect = page.locator('#quiz-topic-select');

    // Check topic options exist
    await expect(topicSelect.locator('option[value="all"]')).toHaveCount(1);
    await expect(topicSelect.locator('option[value="criminal"]')).toHaveCount(1);
    await expect(topicSelect.locator('option[value="private"]')).toHaveCount(1);

    // Check 'all' is selected by default
    await expect(topicSelect).toHaveValue('all');
  });

  test('should allow changing difficulty', async ({ page }) => {
    const difficultySelect = page.locator('#quiz-difficulty-select');

    // Change to easy
    await difficultySelect.selectOption('easy');
    await expect(difficultySelect).toHaveValue('easy');

    // Change to hard
    await difficultySelect.selectOption('hard');
    await expect(difficultySelect).toHaveValue('hard');
  });

  test('should allow changing topic', async ({ page }) => {
    const topicSelect = page.locator('#quiz-topic-select');

    // Change to criminal law
    await topicSelect.selectOption('criminal');
    await expect(topicSelect).toHaveValue('criminal');

    // Change to constitutional law
    await topicSelect.selectOption('constitutional');
    await expect(topicSelect).toHaveValue('constitutional');
  });

  test('quiz content should be hidden initially', async ({ page }) => {
    // The quiz content should be hidden until a quiz is started
    const quizContent = page.locator('#quiz-content');
    await expect(quizContent).toHaveClass(/hidden/);
  });
});

test.describe('Quiz UI Elements', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to course selection page and enter a course
    await page.goto('/');
    const enterCourseBtn = page.locator('button:has-text("Enter Course")').first();
    await enterCourseBtn.click();
    await expect(page.locator('[data-tab="quiz"]')).toBeVisible();
    await page.click('[data-tab="quiz"]');
    await expect(page.locator('#quiz-section')).toBeVisible();
  });

  test('should have proper form structure', async ({ page }) => {
    // Check form group structure
    const quizSection = page.locator('#quiz-section');
    await expect(quizSection).toBeVisible();

    // Verify labels exist
    await expect(page.locator('label[for="quiz-topic-select"]')).toBeVisible();
    await expect(page.locator('label[for="quiz-difficulty-select"]')).toBeVisible();
  });

  test('should have quiz progress elements hidden initially', async ({ page }) => {
    // Progress elements exist but quiz content is hidden
    const quizContent = page.locator('#quiz-content');
    await expect(quizContent).toHaveClass(/hidden/);

    // Elements inside hidden content should exist
    await expect(page.locator('#quiz-current')).toBeAttached();
    await expect(page.locator('#quiz-total')).toBeAttached();
    await expect(page.locator('#quiz-score')).toBeAttached();
  });
});


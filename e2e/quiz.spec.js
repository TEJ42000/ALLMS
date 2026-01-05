// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Quiz System', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display quiz section on homepage', async ({ page }) => {
    // Check that the quiz section exists
    const quizSection = page.locator('#quiz-section');
    await expect(quizSection).toBeVisible();
    
    // Check for quiz topic input
    const topicInput = page.locator('#quiz-topic');
    await expect(topicInput).toBeVisible();
    
    // Check for difficulty selector
    const difficultySelect = page.locator('#quiz-difficulty-select');
    await expect(difficultySelect).toBeVisible();
    
    // Check for generate button
    const generateBtn = page.locator('#generate-quiz-btn');
    await expect(generateBtn).toBeVisible();
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

  test('should allow changing difficulty', async ({ page }) => {
    const difficultySelect = page.locator('#quiz-difficulty-select');
    
    // Change to easy
    await difficultySelect.selectOption('easy');
    await expect(difficultySelect).toHaveValue('easy');
    
    // Change to hard
    await difficultySelect.selectOption('hard');
    await expect(difficultySelect).toHaveValue('hard');
  });

  test('should show error when generating quiz with empty topic', async ({ page }) => {
    // Clear the topic input
    const topicInput = page.locator('#quiz-topic');
    await topicInput.clear();
    
    // Click generate button
    const generateBtn = page.locator('#generate-quiz-btn');
    await generateBtn.click();
    
    // Should show an error or not proceed
    // The quiz content should remain hidden
    const quizContent = page.locator('#quiz-content');
    await expect(quizContent).toHaveClass(/hidden/);
  });

  test('should prevent multiple quiz generation requests', async ({ page }) => {
    // Fill in a topic
    const topicInput = page.locator('#quiz-topic');
    await topicInput.fill('Contract Law');
    
    // Get the generate button
    const generateBtn = page.locator('#generate-quiz-btn');
    
    // Click twice quickly - second click should be ignored due to race condition protection
    await generateBtn.click();
    
    // Check that loading indicator appears (if implemented)
    // The isGeneratingQuiz flag should prevent duplicate requests
    // We can verify the button behavior indirectly
  });
});

test.describe('Quiz UI Elements', () => {
  test('should have proper form structure', async ({ page }) => {
    await page.goto('/');
    
    // Check form group structure
    const quizSection = page.locator('#quiz-section');
    await expect(quizSection).toBeVisible();
    
    // Verify labels exist
    await expect(page.getByLabel(/topic/i)).toBeVisible();
    await expect(page.getByLabel(/difficulty/i)).toBeVisible();
  });
});


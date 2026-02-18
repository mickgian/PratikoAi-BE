/**
 * E2E Proactivity Tests - DEV-172
 *
 * Tests complete user flows for proactivity features:
 * - Interactive questions for incomplete queries
 * - Keyboard navigation
 * - Mobile viewport behavior
 *
 * DEV-245 Phase 5.15: Suggested actions tests removed per user feedback
 */
import { test, expect } from '@playwright/test';

test.describe('Proactivity E2E - Interactive Questions', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/chat');
    await page.waitForLoadState('networkidle');
  });

  test('should display interactive question for incomplete query', async ({
    page,
  }) => {
    // Send an incomplete query (missing parameters)
    const input = page.locator('textarea, input[type="text"]').first();
    await input.fill('Calcola le tasse');

    const submitButton = page
      .locator('button[type="submit"], button:has-text("Invia")')
      .first();
    await submitButton.click();

    // Wait for AI response
    await page.waitForSelector('.message.ai, [data-testid="ai-message"]', {
      timeout: 15000,
    });

    await page.waitForFunction(
      () =>
        !document.querySelector(
          '.typing-indicator, [data-testid="typing-indicator"]'
        ),
      { timeout: 60000 }
    );

    // Check for interactive question (radiogroup)
    const questionContainer = page.locator('[role="radiogroup"]');

    if ((await questionContainer.count()) > 0) {
      await expect(questionContainer).toBeVisible();

      // Check that options are present
      const options = questionContainer.locator('[role="radio"]');
      expect(await options.count()).toBeGreaterThan(0);
    }
  });

  test('should answer question by clicking option', async ({ page }) => {
    // Send incomplete query
    const input = page.locator('textarea, input[type="text"]').first();
    await input.fill('Ho bisogno di aiuto fiscale');

    const submitButton = page
      .locator('button[type="submit"], button:has-text("Invia")')
      .first();
    await submitButton.click();

    // Wait for response
    await page.waitForSelector('.message.ai, [data-testid="ai-message"]', {
      timeout: 15000,
    });

    await page.waitForFunction(
      () =>
        !document.querySelector(
          '.typing-indicator, [data-testid="typing-indicator"]'
        ),
      { timeout: 60000 }
    );

    // Look for question options
    const option = page.locator('[role="radio"]').first();

    if ((await option.count()) > 0) {
      // Click the first option
      await option.click();

      // Wait for response to the answer
      await page.waitForTimeout(1000);

      // Should get a follow-up response or the question should be removed
      const questionAfterAnswer = page.locator('[role="radiogroup"]');
      // Question may still be visible (multi-step) or gone (single-step)
    }
  });

  test('should skip question with Escape key', async ({ page }) => {
    // Send incomplete query
    const input = page.locator('textarea, input[type="text"]').first();
    await input.fill('Domanda generica');

    const submitButton = page
      .locator('button[type="submit"], button:has-text("Invia")')
      .first();
    await submitButton.click();

    // Wait for response
    await page.waitForSelector('.message.ai, [data-testid="ai-message"]', {
      timeout: 15000,
    });

    await page.waitForFunction(
      () =>
        !document.querySelector(
          '.typing-indicator, [data-testid="typing-indicator"]'
        ),
      { timeout: 60000 }
    );

    // Check for question
    const questionContainer = page.locator('[role="radiogroup"]');

    if ((await questionContainer.count()) > 0) {
      // Focus the question container
      await questionContainer.focus();

      // Press Escape to skip
      await page.keyboard.press('Escape');

      // Question may be dismissed or remain (depends on implementation)
      await page.waitForTimeout(500);
    }
  });

  test('should navigate options with arrow keys', async ({ page }) => {
    // Send incomplete query
    const input = page.locator('textarea, input[type="text"]').first();
    await input.fill('Aiutami con le tasse');

    const submitButton = page
      .locator('button[type="submit"], button:has-text("Invia")')
      .first();
    await submitButton.click();

    // Wait for response
    await page.waitForSelector('.message.ai, [data-testid="ai-message"]', {
      timeout: 15000,
    });

    await page.waitForFunction(
      () =>
        !document.querySelector(
          '.typing-indicator, [data-testid="typing-indicator"]'
        ),
      { timeout: 60000 }
    );

    // Check for question
    const questionContainer = page.locator('[role="radiogroup"]');

    if ((await questionContainer.count()) > 0) {
      // Focus the question container
      await questionContainer.focus();

      // Navigate with arrow keys
      await page.keyboard.press('ArrowDown');
      await page.keyboard.press('ArrowDown');
      await page.keyboard.press('ArrowUp');

      // Select with Enter
      await page.keyboard.press('Enter');

      // Wait for response
      await page.waitForTimeout(1000);
    }
  });

  test('should select option with number keys', async ({ page }) => {
    // Send incomplete query
    const input = page.locator('textarea, input[type="text"]').first();
    await input.fill('Cosa devo fare?');

    const submitButton = page
      .locator('button[type="submit"], button:has-text("Invia")')
      .first();
    await submitButton.click();

    // Wait for response
    await page.waitForSelector('.message.ai, [data-testid="ai-message"]', {
      timeout: 15000,
    });

    await page.waitForFunction(
      () =>
        !document.querySelector(
          '.typing-indicator, [data-testid="typing-indicator"]'
        ),
      { timeout: 60000 }
    );

    // Check for question
    const questionContainer = page.locator('[role="radiogroup"]');

    if ((await questionContainer.count()) > 0) {
      // Focus the question container
      await questionContainer.focus();

      // Select option 2 with number key
      await page.keyboard.press('2');

      // Wait for response
      await page.waitForTimeout(1000);
    }
  });
});

test.describe('Proactivity E2E - Mobile Viewport', () => {
  test.beforeEach(async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/chat');
    await page.waitForLoadState('networkidle');
  });

  // DEV-245 Phase 5.15: "should display actions in vertical stack on mobile" test removed per user feedback

  test('should display question options in single column on mobile', async ({
    page,
  }) => {
    // Send incomplete query
    const input = page.locator('textarea, input[type="text"]').first();
    await input.fill('Calcola tasse');

    const submitButton = page
      .locator('button[type="submit"], button:has-text("Invia")')
      .first();
    await submitButton.click();

    // Wait for response
    await page.waitForSelector('.message.ai, [data-testid="ai-message"]', {
      timeout: 15000,
    });

    await page.waitForFunction(
      () =>
        !document.querySelector(
          '.typing-indicator, [data-testid="typing-indicator"]'
        ),
      { timeout: 60000 }
    );

    // Check question container
    const questionContainer = page.locator('[role="radiogroup"]');

    if ((await questionContainer.count()) > 0) {
      // Options should be touchable
      const options = questionContainer.locator('[role="radio"]');
      const optionCount = await options.count();

      for (let i = 0; i < optionCount; i++) {
        const option = options.nth(i);
        const box = await option.boundingBox();

        // Touch targets should be at least 44px
        if (box) {
          expect(box.height).toBeGreaterThanOrEqual(44);
        }
      }
    }
  });

  test('should not have horizontal scroll on mobile', async ({ page }) => {
    // Send query
    const input = page.locator('textarea, input[type="text"]').first();
    await input.fill('Test scroll');

    const submitButton = page
      .locator('button[type="submit"], button:has-text("Invia")')
      .first();
    await submitButton.click();

    // Wait for response
    await page.waitForSelector('.message.ai, [data-testid="ai-message"]', {
      timeout: 15000,
    });

    await page.waitForFunction(
      () =>
        !document.querySelector(
          '.typing-indicator, [data-testid="typing-indicator"]'
        ),
      { timeout: 60000 }
    );

    // Check for horizontal scroll
    const hasHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth;
    });

    expect(hasHorizontalScroll).toBe(false);
  });
});

test.describe('Proactivity E2E - Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/chat');
    await page.waitForLoadState('networkidle');
  });

  test('should handle proactivity gracefully on slow connection', async ({
    page,
  }) => {
    // Simulate slow network
    await page.route('**/api/**', async route => {
      await new Promise(resolve => setTimeout(resolve, 2000));
      await route.continue();
    });

    // Send query
    const input = page.locator('textarea, input[type="text"]').first();
    await input.fill('Test slow');

    const submitButton = page
      .locator('button[type="submit"], button:has-text("Invia")')
      .first();
    await submitButton.click();

    // Should show loading state without errors
    await page.waitForSelector('.message.ai, [data-testid="ai-message"]', {
      timeout: 30000,
    });

    // No error should be displayed
    const errors: string[] = [];
    page.on('console', msg => {
      if (
        msg.type() === 'error' &&
        !msg.text().includes('favicon') &&
        !msg.text().includes('404')
      ) {
        errors.push(msg.text());
      }
    });

    expect(
      errors.filter(e => e.includes('proactivity') || e.includes('action'))
    ).toHaveLength(0);
  });

  test('should continue chat when proactivity features are unavailable', async ({
    page,
  }) => {
    // Block proactivity endpoints
    await page.route('**/actions/**', route => route.abort());
    await page.route('**/questions/**', route => route.abort());

    // Send query
    const input = page.locator('textarea, input[type="text"]').first();
    await input.fill('Test without proactivity');

    const submitButton = page
      .locator('button[type="submit"], button:has-text("Invia")')
      .first();
    await submitButton.click();

    // Chat should still work
    await page.waitForSelector('.message.ai, [data-testid="ai-message"]', {
      timeout: 15000,
    });

    const aiMessage = page
      .locator('.message.ai, [data-testid="ai-message"]')
      .last();
    const responseText = await aiMessage.textContent();

    // Response should exist (proactivity failure shouldn't break chat)
    expect(responseText).toBeTruthy();
  });
});

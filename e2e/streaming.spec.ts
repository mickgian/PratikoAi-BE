/**
 * E2E Streaming Tests
 * Tests complete streaming flow from backend to UI
 */
import { test, expect } from '@playwright/test';

test.describe('SSE Streaming E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to chat page before each test
    await page.goto('/chat');

    // Wait for page to be ready
    await page.waitForLoadState('networkidle');
  });

  test('should stream complete response without refresh', async ({ page }) => {
    // Send message
    const input = page.locator('textarea, input[type="text"]').first();
    await input.fill('Cosa sono le detrazioni fiscali per ottobre 2025?');

    const submitButton = page
      .locator('button[type="submit"], button:has-text("Invia")')
      .first();
    await submitButton.click();

    // Wait for AI message to appear
    await page.waitForSelector('.message.ai, [data-testid="ai-message"]', {
      timeout: 10000,
    });

    // Wait for streaming to complete (typing indicator disappears)
    await page.waitForFunction(
      () =>
        !document.querySelector(
          '.typing-indicator, [data-testid="typing-indicator"]'
        ),
      { timeout: 60000 }
    );

    // Get full response text
    const aiMessage = page
      .locator('.message.ai, [data-testid="ai-message"]')
      .last();
    const responseText = await aiMessage.textContent();

    // Verify response is complete (should mention "Risoluzione" from October 2025)
    expect(responseText).toBeTruthy();
    expect(responseText!.toLowerCase()).toContain('risoluzione');

    // Verify response length is substantial (not truncated)
    expect(responseText!.length).toBeGreaterThan(500);
  });

  test('should display chunks in real-time', async ({ page }) => {
    // Monitor console for chunk logs
    const consoleLogs: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'log' && msg.text().includes('[API]')) {
        consoleLogs.push(msg.text());
      }
    });

    // Send message
    const input = page.locator('textarea, input[type="text"]').first();
    await input.fill('test query');

    const submitButton = page
      .locator('button[type="submit"], button:has-text("Invia")')
      .first();
    await submitButton.click();

    // Wait for response to complete
    await page.waitForSelector('.message.ai, [data-testid="ai-message"]', {
      timeout: 10000,
    });

    await page.waitForFunction(
      () =>
        !document.querySelector(
          '.typing-indicator, [data-testid="typing-indicator"]'
        ),
      { timeout: 60000 }
    );

    // Should have received multiple chunk logs
    const chunkLogs = consoleLogs.filter(log => log.includes('chunk'));
    expect(chunkLogs.length).toBeGreaterThan(0);
  });

  test('should not require page refresh for response', async ({ page }) => {
    const input = page.locator('textarea, input[type="text"]').first();
    await input.fill('quick test');

    const submitButton = page
      .locator('button[type="submit"], button:has-text("Invia")')
      .first();
    await submitButton.click();

    // Response should appear without refresh
    const aiMessage = await page.waitForSelector(
      '.message.ai, [data-testid="ai-message"]',
      { timeout: 15000 }
    );

    expect(aiMessage).toBeTruthy();

    // Verify we didn't navigate away (URL should still be /chat)
    expect(page.url()).toContain('/chat');
  });

  test('should handle long responses without truncation', async ({ page }) => {
    const input = page.locator('textarea, input[type="text"]').first();
    await input.fill(
      'Explain all Italian tax deductions in detail for October and November 2025'
    );

    const submitButton = page
      .locator('button[type="submit"], button:has-text("Invia")')
      .first();
    await submitButton.click();

    await page.waitForSelector('.message.ai, [data-testid="ai-message"]', {
      timeout: 10000,
    });

    // Wait for completion
    await page.waitForFunction(
      () =>
        !document.querySelector(
          '.typing-indicator, [data-testid="typing-indicator"]'
        ),
      { timeout: 90000 } // Longer timeout for detailed response
    );

    const aiMessage = page
      .locator('.message.ai, [data-testid="ai-message"]')
      .last();
    const responseText = await aiMessage.textContent();

    // Long response should be > 1000 characters
    expect(responseText!.length).toBeGreaterThan(1000);
  });

  test('should display links properly (not raw markdown)', async ({ page }) => {
    const input = page.locator('textarea, input[type="text"]').first();
    await input.fill('Show me documents about taxes');

    const submitButton = page
      .locator('button[type="submit"], button:has-text("Invia")')
      .first();
    await submitButton.click();

    await page.waitForSelector('.message.ai, [data-testid="ai-message"]', {
      timeout: 10000,
    });

    await page.waitForFunction(
      () =>
        !document.querySelector(
          '.typing-indicator, [data-testid="typing-indicator"]'
        ),
      { timeout: 60000 }
    );

    const aiMessage = page
      .locator('.message.ai, [data-testid="ai-message"]')
      .last();
    const content = await aiMessage.innerHTML();

    // Should NOT contain raw markdown link syntax [text](url)
    // If links are present, they should be rendered as <a> tags
    if (content.includes('http')) {
      expect(content).not.toMatch(/\[.*?]\(https?:\/\/.*?\)/);
    }
  });

  test('should show no console errors during streaming', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    const input = page.locator('textarea, input[type="text"]').first();
    await input.fill('test');

    const submitButton = page
      .locator('button[type="submit"], button:has-text("Invia")')
      .first();
    await submitButton.click();

    await page.waitForSelector('.message.ai, [data-testid="ai-message"]', {
      timeout: 10000,
    });

    await page.waitForFunction(
      () =>
        !document.querySelector(
          '.typing-indicator, [data-testid="typing-indicator"]'
        ),
      { timeout: 60000 }
    );

    // Filter out non-critical errors
    const criticalErrors = errors.filter(
      err =>
        !err.includes('favicon') &&
        !err.includes('404') &&
        (err.includes('TypeError') ||
          err.includes('ReferenceError') ||
          err.includes('Invalid SSE'))
    );

    expect(criticalErrors).toHaveLength(0);
  });
});

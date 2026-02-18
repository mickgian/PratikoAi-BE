import { test, expect } from '@playwright/test';

/**
 * E2E Test: DEV-003 - Chat History Creation Behavior
 *
 * Tests the complete user flow:
 * 1. Sign in → empty chat panel (no auto-create)
 * 2. Click "Nuova chat" → no history entry created
 * 3. Send first message → session created + history entry appears
 */

test.describe('Chat History Creation Behavior (DEV-003)', () => {
  test.beforeEach(async ({ page }) => {
    // Clear localStorage and cookies before each test
    await page.context().clearCookies();
    await page.goto('/');
  });

  test('should show empty chat panel after sign-in (no auto-create)', async ({
    page,
  }) => {
    // Navigate to chat page (assumes user is authenticated or auto-login in dev)
    await page.goto('/chat');

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Should see empty chat panel with Italian placeholder
    const emptyState = page.locator(
      'text=/Inizia una nuova conversazione|Fai una domanda per iniziare/i'
    );
    await expect(emptyState).toBeVisible({ timeout: 5000 });

    // Sidebar should NOT have any chat history entries (or only old ones)
    const chatHistoryList = page.locator('[data-testid="chat-history-list"]');

    // Check if history list exists
    const historyExists = await chatHistoryList.count();

    if (historyExists > 0) {
      // If history exists, verify no "loading" state or spinner
      const loadingSpinner = page.locator('[data-testid="loading-spinner"]');
      await expect(loadingSpinner).not.toBeVisible();
    }

    // Verify no session creation API call was made during page load
    // This is a behavioral check - we'll verify by checking localStorage
    const currentSession = await page.evaluate(() => {
      return localStorage.getItem('currentSession');
    });

    // Current session should be null or empty
    expect(currentSession).toBeFalsy();
  });

  test('should NOT create history entry when clicking "Nuova chat" button', async ({
    page,
  }) => {
    await page.goto('/chat');
    await page.waitForLoadState('networkidle');

    // Get initial history count
    const initialHistoryItems = await page
      .locator('[data-testid="chat-history-item"]')
      .count();

    // Click "Nuova chat" button
    const newChatButton = page.locator('button:has-text("Nuova chat")');
    await expect(newChatButton).toBeVisible();
    await newChatButton.click();

    // Wait a moment for any potential API calls
    await page.waitForTimeout(1000);

    // Verify history count did NOT increase
    const finalHistoryItems = await page
      .locator('[data-testid="chat-history-item"]')
      .count();
    expect(finalHistoryItems).toBe(initialHistoryItems);

    // Should still see empty chat panel
    const emptyState = page.locator(
      'text=/Inizia una nuova conversazione|Fai una domanda per iniziare/i'
    );
    await expect(emptyState).toBeVisible();

    // Verify no session in localStorage
    const currentSession = await page.evaluate(() => {
      return localStorage.getItem('currentSession');
    });
    expect(currentSession).toBeFalsy();
  });

  test('should create session and history entry ONLY when sending first message', async ({
    page,
  }) => {
    await page.goto('/chat');
    await page.waitForLoadState('networkidle');

    // Get initial history count
    const initialHistoryItems = await page
      .locator('[data-testid="chat-history-item"]')
      .count();

    // Type a message in the input area
    const messageInput = page.locator(
      'textarea[placeholder*="Scrivi un messaggio"]'
    );
    await expect(messageInput).toBeVisible();
    await messageInput.fill('Ciao, questa è la mia prima domanda');

    // Click send button
    const sendButton = page.locator('button[type="submit"]:has-text("Invia")');
    await sendButton.click();

    // Wait for session creation API call
    await page.waitForResponse(
      response =>
        response.url().includes('/api/v1/chat/sessions') &&
        response.status() === 201,
      { timeout: 5000 }
    );

    // Wait for message to appear in chat
    await expect(
      page.locator('text=Ciao, questa è la mia prima domanda')
    ).toBeVisible({ timeout: 5000 });

    // Verify session was created in localStorage
    const currentSession = await page.evaluate(() => {
      return localStorage.getItem('currentSession');
    });
    expect(currentSession).toBeTruthy();

    // Verify history count increased by 1
    const finalHistoryItems = await page
      .locator('[data-testid="chat-history-item"]')
      .count();
    expect(finalHistoryItems).toBe(initialHistoryItems + 1);

    // Verify the new history entry has a title (auto-generated or default)
    const newHistoryEntry = page
      .locator('[data-testid="chat-history-item"]')
      .first();
    await expect(newHistoryEntry).toBeVisible();
  });

  test('should NOT create multiple sessions when sending messages rapidly', async ({
    page,
  }) => {
    await page.goto('/chat');
    await page.waitForLoadState('networkidle');

    const messageInput = page.locator(
      'textarea[placeholder*="Scrivi un messaggio"]'
    );
    const sendButton = page.locator('button[type="submit"]:has-text("Invia")');

    // Send multiple messages rapidly
    await messageInput.fill('Message 1');
    await sendButton.click();

    await messageInput.fill('Message 2');
    await sendButton.click();

    await messageInput.fill('Message 3');
    await sendButton.click();

    // Wait for responses
    await page.waitForTimeout(2000);

    // Verify only ONE session was created
    const historyItems = await page
      .locator('[data-testid="chat-history-item"]')
      .count();

    // Should have exactly 1 new session (all messages in same session)
    expect(historyItems).toBeLessThanOrEqual(1);
  });

  test('full user flow: empty state → new chat → send message → history created', async ({
    page,
  }) => {
    await page.goto('/chat');
    await page.waitForLoadState('networkidle');

    // Step 1: Verify empty state
    const emptyState = page.locator(
      'text=/Inizia una nuova conversazione|Fai una domanda per iniziare/i'
    );
    await expect(emptyState).toBeVisible();

    // Step 2: Click "Nuova chat" (should do nothing)
    const newChatButton = page.locator('button:has-text("Nuova chat")');
    await newChatButton.click();
    await page.waitForTimeout(500);

    // Still empty
    await expect(emptyState).toBeVisible();

    // Step 3: Send first message
    const messageInput = page.locator(
      'textarea[placeholder*="Scrivi un messaggio"]'
    );
    await messageInput.fill('Qual è lo scopo di PratikoAI?');

    const sendButton = page.locator('button[type="submit"]:has-text("Invia")');
    await sendButton.click();

    // Step 4: Verify session created
    await page.waitForResponse(
      response => response.url().includes('/api/v1/chat/sessions'),
      { timeout: 5000 }
    );

    // Step 5: Verify message appears
    await expect(
      page.locator('text=Qual è lo scopo di PratikoAI?')
    ).toBeVisible();

    // Step 6: Verify history entry appears
    const historyItems = await page.locator(
      '[data-testid="chat-history-item"]'
    );
    await expect(historyItems.first()).toBeVisible();

    // Step 7: Verify session persists in localStorage
    const currentSession = await page.evaluate(() => {
      return localStorage.getItem('currentSession');
    });
    expect(currentSession).toBeTruthy();
  });
});

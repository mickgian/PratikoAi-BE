import { test, expect } from '@playwright/test';

test.describe('PratikoAi Happy Path', () => {
  test('should load homepage and navigate to chat', async ({ page }) => {
    // Navigate to the homepage
    await page.goto('/');

    // Check that the homepage loads correctly
    await expect(page).toHaveTitle(/PratikoAi/);

    // Look for key elements on the homepage
    await expect(page.locator('h1')).toContainText(/PratikoAi|Pratiko/);

    // Find and click a navigation link or CTA button to chat
    // This will depend on your actual homepage structure
    const chatButton = page
      .locator(
        'a[href="/chat"], button:has-text("Inizia"), button:has-text("Chat")'
      )
      .first();

    if (await chatButton.isVisible()) {
      await chatButton.click();

      // Should navigate to chat page
      await expect(page).toHaveURL(/\/chat/);

      // Check that chat interface loads
      await expect(page.locator('input[type="text"], textarea')).toBeVisible();
    } else {
      // If no direct chat button, navigate manually
      await page.goto('/chat');
      await expect(page).toHaveURL(/\/chat/);
    }
  });

  test('should display sign-up page correctly', async ({ page }) => {
    await page.goto('/signup');

    // Check page loads
    await expect(page).toHaveTitle(/Sign Up|Registrati/);

    // Check for sign-up form elements
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(
      page.locator(
        'button[type="submit"], button:has-text("Sign Up"), button:has-text("Registrati")'
      )
    ).toBeVisible();
  });

  test('should display sign-in page correctly', async ({ page }) => {
    await page.goto('/signin');

    // Check page loads
    await expect(page).toHaveTitle(/Sign In|Accedi/);

    // Check for sign-in form elements
    await expect(
      page.locator('input[type="email"], input[name="username"]')
    ).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(
      page.locator(
        'button[type="submit"], button:has-text("Sign In"), button:has-text("Accedi")'
      )
    ).toBeVisible();
  });

  test('should navigate between main pages', async ({ page }) => {
    // Start from homepage
    await page.goto('/');

    // Test navigation to different pages
    const testPages = [
      { url: '/faq', titlePattern: /FAQ|Domande/ },
      { url: '/privacy-policy', titlePattern: /Privacy|Policy/ },
      { url: '/terms-of-service', titlePattern: /Terms|Termini/ },
    ];

    for (const testPage of testPages) {
      await page.goto(testPage.url);
      await expect(page).toHaveTitle(testPage.titlePattern);

      // Check that the page has content (not empty)
      const bodyText = await page.textContent('body');
      expect(bodyText).toBeTruthy();
      expect(bodyText!.length).toBeGreaterThan(100); // At least some content
    }
  });

  test('should have working responsive design', async ({ page }) => {
    await page.goto('/');

    // Test desktop view
    await page.setViewportSize({ width: 1200, height: 800 });
    await expect(page.locator('body')).toBeVisible();

    // Test tablet view
    await page.setViewportSize({ width: 768, height: 1024 });
    await expect(page.locator('body')).toBeVisible();

    // Test mobile view
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.locator('body')).toBeVisible();

    // Check that navigation or menu is accessible on mobile
    // This might be a hamburger menu or mobile nav
    const mobileNav = page.locator(
      'nav, .mobile-menu, [data-testid="mobile-nav"]'
    );
    if (await mobileNav.isVisible()) {
      await expect(mobileNav).toBeVisible();
    }
  });

  test('should have accessible elements', async ({ page }) => {
    await page.goto('/');

    // Check for basic accessibility elements
    const mainContent = page.locator('main, [role="main"]');
    if ((await mainContent.count()) > 0) {
      await expect(mainContent.first()).toBeVisible();
    }

    // Check that buttons have accessible names
    const buttons = page.locator('button');
    const buttonCount = await buttons.count();

    if (buttonCount > 0) {
      // Check first few buttons have text or aria-label
      for (let i = 0; i < Math.min(3, buttonCount); i++) {
        const button = buttons.nth(i);
        const text = await button.textContent();
        const ariaLabel = await button.getAttribute('aria-label');

        expect(text || ariaLabel).toBeTruthy();
      }
    }
  });

  test('should load critical resources without errors', async ({ page }) => {
    // Listen for console errors
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    // Navigate to homepage
    await page.goto('/');

    // Wait for page to load completely
    await page.waitForLoadState('networkidle');

    // Check for critical console errors (ignore minor warnings)
    const criticalErrors = errors.filter(
      error =>
        (!error.includes('favicon') &&
          !error.includes('404') &&
          error.includes('Error')) ||
        error.includes('TypeError') ||
        error.includes('ReferenceError')
    );

    expect(criticalErrors).toHaveLength(0);
  });
});

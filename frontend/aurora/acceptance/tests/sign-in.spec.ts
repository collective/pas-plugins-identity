import { expect, test } from '@playwright/test';

/**
 * Dex's static user: `DEX_USER` in `backend/tests/conftest.py`, whose
 * password hash is in `backend/tests/_resources/dex/config.yaml`. A fixture
 * of an in-memory Dex that exists only for tests.
 */
const DEX_USER = { email: 'erico@plone.org', password: 'plone-test-password' };

test.describe('Signing in to Aurora with an identity provider', () => {
  test('the login page offers the provider, and Dex signs the user in', async ({
    page,
    context,
  }) => {
    await page.goto('/login?choose=1');
    await page.getByRole('button', { name: 'Dex' }).click();

    // Dex's own login form, on Dex's own origin.
    await page.waitForURL(/\/dex\/auth/);
    await page.locator('input[name="login"]').fill(DEX_USER.email);
    await page.locator('input[name="password"]').fill(DEX_USER.password);
    await page.locator('button[type="submit"]').click();

    // Back through `/login-identity`, home, and signed in.
    await page.waitForURL((url) => url.pathname === '/');
    const cookies = await context.cookies();
    expect(cookies.map((cookie) => cookie.name)).toContain('auth_seven');
  });

  test('a sole provider is started without a click', async ({ page }) => {
    await page.goto('/login');

    await page.waitForURL(/\/dex\/auth/);
  });

  test('a refused sign-in explains itself and offers the options', async ({
    page,
  }) => {
    await page.goto('/login-identity?error=access_denied');

    await expect(page.getByRole('alert')).toContainText(
      'The provider refused the sign-in.',
    );
    await page.getByRole('link', { name: 'Back to sign-in options' }).click();
    await expect(page).toHaveURL(/\/login\?choose=1$/);
    await expect(page.getByRole('button', { name: 'Dex' })).toBeVisible();
  });

  test('a forged callback is refused', async ({ page }) => {
    await page.goto('/login-identity?code=forged&state=forged');

    await expect(page.getByRole('alert')).toContainText(
      'That sign-in link is no longer valid.',
    );
  });
});

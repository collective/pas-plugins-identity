import { expect, test } from '@playwright/test';

import { logInAtDex } from '../dex';

test.describe('Signing in to Aurora with an identity provider', () => {
  test('the login page offers the provider, and Dex signs the user in', async ({
    page,
    context,
  }) => {
    await page.goto('/login?choose=1');
    await page.getByRole('button', { name: 'Dex' }).click();

    // Dex's own login form, on Dex's own origin.
    await logInAtDex(page);

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

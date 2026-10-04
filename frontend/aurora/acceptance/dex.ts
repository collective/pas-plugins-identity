/**
 * Signing in at Dex, as a person would.
 */
import type { Page } from '@playwright/test';

/**
 * Dex's static user: `DEX_USER` in `backend/tests/conftest.py`, whose
 * password hash is in `backend/tests/_resources/dex/config.yaml`. A fixture
 * of an in-memory Dex that exists only for tests.
 */
export const DEX_USER = {
  email: 'erico@plone.org',
  password: 'plone-test-password',
};

/**
 * Fill in Dex's own login form, once the browser is on it.
 *
 * @param page The page, on its way to Dex.
 */
export async function logInAtDex(page: Page): Promise<void> {
  await page.waitForURL(/\/dex\/auth/);
  await page.locator('input[name="login"]').fill(DEX_USER.email);
  await page.locator('input[name="password"]').fill(DEX_USER.password);
  await page.locator('button[type="submit"]').click();
}

/**
 * Sign in to Aurora with Dex, from the login page.
 *
 * @param page The page.
 */
export async function signInWithDex(page: Page): Promise<void> {
  await page.goto('/login?choose=1');
  await page.getByRole('button', { name: 'Dex', exact: true }).click();
  await logInAtDex(page);
  await page.waitForURL((url) => url.pathname === '/');
}

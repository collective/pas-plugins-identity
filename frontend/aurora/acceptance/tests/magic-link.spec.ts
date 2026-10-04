import { expect, test } from '@playwright/test';

import {
  addProvider,
  EMAIL_PROVIDER,
  lastMagicLink,
  removeProvider,
} from '../backend';

// With the email provider beside Dex there are two ways in, which would
// stop `/login` going straight to Dex in the other tests.
test.beforeAll(() => addProvider(EMAIL_PROVIDER));
test.afterAll(() => removeProvider(EMAIL_PROVIDER.id));

test.describe('Signing in to Aurora with a magic link', () => {
  test('the link in the email signs the user in, once', async ({
    page,
    context,
  }) => {
    // An address nobody has used, so the only link sent to it is this run's.
    const address = `magic-${Date.now()}@example.com`;

    await page.goto('/login');
    await page.getByRole('button', { name: 'Email' }).click();
    await page.getByLabel('Email address').fill(address);
    await page.getByRole('button', { name: 'Email me a link' }).click();
    await expect(
      page.getByText('If that address can sign in here'),
    ).toBeVisible();

    const link = await lastMagicLink(address);
    expect(link).not.toBeNull();
    // The backend builds it from Aurora's address: the visitor comes back
    // to Aurora, not to the backend.
    const target = new URL(link!);
    expect(target.origin).toBe(new URL(page.url()).origin);
    expect(target.pathname).toBe('/login-identity');

    await page.goto(link!);
    await page.waitForURL((url) => url.pathname === '/');
    const cookies = await context.cookies();
    expect(cookies.map((cookie) => cookie.name)).toContain('auth_seven');

    // A link works once.
    await context.clearCookies();
    await page.goto(link!);
    await expect(page.getByRole('alert')).toContainText(
      'That sign-in link is no longer valid.',
    );
  });
});

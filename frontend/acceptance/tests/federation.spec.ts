/**
 * Federated sign-in, through a real OpenID Connect provider.
 *
 * Dex runs beside the acceptance backend (`make acceptance-dex-start`), with
 * the backend flow tests' own configuration: one person, two static clients.
 */
import type { BrowserContext, Page } from '@playwright/test';

import {
  addDexProviders,
  addEmailProvider,
  addProfileAddress,
  DEX_ISSUER,
  DEX_PROVIDERS,
  DEX_USER,
  lastSentMail,
  linkIn,
  requireProfileFields,
  sentMailCount,
  signIn,
} from '../backend';
import { expect, test } from '../fixtures';

test.beforeEach(async () => {
  await addDexProviders();
});

/**
 * Sign in on Dex's own login form, as the person does.
 *
 * @param page The page, already on its way to Dex.
 */
async function signInOnDex(page: Page): Promise<void> {
  await expect(page).toHaveURL(/127\.0\.0\.1:5556\/dex/);
  await page.locator('#login').fill(DEX_USER.email);
  await page.locator('#password').fill(DEX_USER.password);
  await page.locator('#submit-login').click();
}

/**
 * Sign in from `/login` through the provider with the given title.
 *
 * @param page The page.
 * @param title The provider's title on the login screen.
 */
async function signInThrough(page: Page, title = 'Dex'): Promise<void> {
  await page.goto('/login');
  await page
    .locator('.identity-providers')
    .getByText(title, { exact: true })
    .click();
  await signInOnDex(page);
  await expect(page.locator('#toolbar')).toBeVisible();
}

/**
 * The userid of whoever the browser is signed in as.
 *
 * @param context The browser context holding Volto's `auth_token` cookie.
 * @returns The `sub` of the session token.
 */
async function signedInAs(context: BrowserContext): Promise<string> {
  const cookie = (await context.cookies()).find((c) => c.name === 'auth_token');
  if (!cookie) {
    throw new Error('The browser holds no session');
  }
  return JSON.parse(
    Buffer.from(cookie.value.split('.')[1], 'base64url').toString('utf-8'),
  ).sub;
}

test.describe('Signing in through Dex', () => {
  test('goes to Dex and comes back with a session', async ({ page }) => {
    await signInThrough(page);

    await expect(page).not.toHaveURL(/\/login/);
  });

  test('holds a first sign-in on the profile until it is complete', async ({
    page,
  }) => {
    // Dex sends a name and an address, never a location.
    await requireProfileFields(['location']);

    await signInThrough(page);

    await expect(page).toHaveURL(/\/identity-profiles\/[^/]+\/edit$/);
    await expect(page.getByText('Complete your profile')).toBeVisible();
    // The profile's own form, not the schema of the page the user came
    // from: a second redirect while the first loaded once gave the latter.
    const location = page.locator('#field-location');
    await expect(location).toBeVisible();

    await page.goto('/');
    await expect(page).toHaveURL(/\/identity-profiles\/[^/]+\/edit$/);

    await location.fill('Brasília');
    await page
      .getByRole('navigation', { name: 'Toolbar' })
      .getByRole('button', { name: 'Save' })
      .click();

    await expect(page).not.toHaveURL(/\/edit$/);
    await page.goto('/');
    await expect(page).toHaveURL(/localhost:3000\/$/);
  });
});

test.describe('Sign-in methods', () => {
  test('links a second method, and removes it again', async ({ page }) => {
    await signInThrough(page);
    await page.goto('/identities');

    const panel = page.getByRole('tabpanel', { name: 'Sign-in methods' });
    const methods = panel.getByRole('list').first().getByRole('listitem');
    await expect(methods).toHaveCount(1);
    // The only way in cannot be taken away.
    await expect(
      methods.first().getByRole('button', { name: 'Remove' }),
    ).toBeDisabled();

    await panel.getByRole('button', { name: 'Dex second' }).click();
    // Dex keeps no session of its own, so it asks again.
    await signInOnDex(page);

    await expect(page).toHaveURL(/\/identities/);
    await expect(methods).toHaveCount(2);
    const second = methods.filter({ hasText: 'Dex second' });
    await expect(second.getByRole('button', { name: 'Remove' })).toBeEnabled();

    await second.getByRole('button', { name: 'Remove' }).click();

    await expect(methods).toHaveCount(1);
    await expect(methods.first()).toContainText('Dex');
    await expect(
      methods.first().getByRole('button', { name: 'Remove' }),
    ).toBeDisabled();
  });

  test('verifies an added address through the link it mails', async ({
    page,
    context,
  }) => {
    const address = 'erico.second@plone.org';
    await addEmailProvider();
    await signInThrough(page);
    await addProfileAddress(await signedInAs(context), address);
    const before = await sentMailCount();

    await page.goto('/identities');
    await page.getByRole('tab', { name: 'Email addresses' }).click();
    const row = page
      .getByRole('tabpanel', { name: 'Email addresses' })
      .getByRole('listitem')
      .filter({ hasText: address });
    await row.getByRole('button', { name: 'Verify' }).click();

    await expect.poll(sentMailCount).toBe(before + 1);
    const message = await lastSentMail();
    expect(message).toContain(address);

    await page.goto(linkIn(message));
    await expect(page.locator('#toolbar')).toBeVisible();

    await page.goto('/identities');
    await page.getByRole('tab', { name: 'Email addresses' }).click();
    await expect(row.getByText('Verified', { exact: true })).toBeVisible();
  });
});

test.describe('Testing a provider', () => {
  test('reaches Dex, and says why a wrong issuer fails', async ({
    page,
    context,
  }) => {
    await addDexProviders(`${DEX_ISSUER}/nowhere`, [
      { ...DEX_PROVIDERS[0], id: 'dex-wrong', title: 'Dex wrong' },
    ]);
    await signIn(context);
    await page.goto('/controlpanel/identity-providers');

    await page
      .getByRole('button', { name: 'Test connection to Dex', exact: true })
      .click();
    await expect(
      page.getByText(`Reached ${DEX_ISSUER}/token`, { exact: true }),
    ).toBeVisible();

    await page
      .getByRole('button', { name: 'Test connection to Dex wrong', exact: true })
      .click();
    await expect(page.locator('.Toastify__toast--error')).toContainText(
      'nowhere',
    );
  });
});

test.describe('The user menu after a federated sign-in', () => {
  test('shows the avatar, and its entries reach their pages', async ({
    page,
  }) => {
    await signInThrough(page);

    const button = page.locator('#toolbar-personal');
    // Dex sends no picture, so the avatar is the person's initials.
    await expect(
      button.locator('.identity-avatar--initials'),
    ).toBeVisible();

    for (const [entry, path] of [
      ['Profile', /\/identity-profiles\/[^/]+$/],
      ['Sign-in methods', /\/identities$/],
      ['Applications', /\/applications$/],
    ] as const) {
      await page.goto('/');
      await button.click();
      await page
        .locator('.personal-tools')
        .getByRole('link', { name: entry, exact: true })
        .click();
      await expect(page).toHaveURL(path);
    }
  });
});

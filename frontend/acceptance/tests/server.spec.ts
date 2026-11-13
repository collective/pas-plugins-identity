/**
 * The authorization server's screens: client registration, consent, and the
 * applications a member has authorized.
 *
 * The acceptance layer installs the server, names its issuer, and sends the
 * consent question to the add-on's `/oauth-consent` route.
 */
import { createHash, randomBytes } from 'node:crypto';

import type { Page } from '@playwright/test';

import { addClient, addMember, CLIENT, MEMBER, signIn } from '../backend';
import { expect, test } from '../fixtures';

const ISSUER =
  process.env.ACCEPTANCE_BACKEND_URL ?? 'http://localhost:55001/plone';

/**
 * Send the browser to the authorization endpoint, as a relying party does.
 *
 * @param page The page.
 * @returns The `state` the request carried.
 */
async function authorize(page: Page): Promise<string> {
  const verifier = randomBytes(32).toString('base64url');
  const state = randomBytes(8).toString('hex');
  const query = new URLSearchParams({
    response_type: 'code',
    client_id: CLIENT.id,
    redirect_uri: CLIENT.redirect_uri,
    scope: 'openid profile',
    state,
    code_challenge: createHash('sha256').update(verifier).digest('base64url'),
    code_challenge_method: 'S256',
  });
  await page.goto(`${ISSUER}/@@oauth-authorize?${query}`);
  return state;
}

/**
 * The query of the address the client was sent back to.
 *
 * @param page The page, on its way to the client.
 * @returns The parameters the authorization server added.
 */
async function backAtTheClient(page: Page): Promise<URLSearchParams> {
  // The address is all the test reads, and the client's page is Volto's
  // not-found page, which need not finish loading for that.
  await page.waitForURL((url) => url.href.startsWith(CLIENT.redirect_uri), {
    waitUntil: 'commit',
  });
  return new URL(page.url()).searchParams;
}

test.describe('The clients control panel', () => {
  test('shows a new client its secret once', async ({ page, context }) => {
    await signIn(context);
    await page.goto('/controlpanel/identity-clients');

    await page.getByRole('button', { name: 'Register a client' }).click();
    await page.getByRole('textbox', { name: 'Client ID' }).fill('registered');
    await page.getByRole('textbox', { name: 'Title' }).fill('Registered app');
    await page.getByRole('button', { name: 'Flow' }).click();
    // A creatable select: what is typed becomes an entry on Enter.
    const uris = page.getByRole('textbox', { name: 'Redirect URIs' });
    await page
      .locator('.react-select__control')
      .filter({ has: uris })
      .click();
    await uris.fill('https://app.example.org/callback');
    await uris.press('Enter');
    await page
      .getByRole('navigation', { name: 'Toolbar' })
      .getByRole('button', { name: 'Save' })
      .click();

    const reveal = page.getByRole('alertdialog', {
      name: 'Secret for registered',
    });
    await expect(
      reveal.getByRole('textbox', { name: 'Client secret for registered' }),
    ).toHaveValue(/\S{20,}/);
    await expect(
      page.getByRole('row').filter({ hasText: 'Registered app' }),
    ).toBeVisible();

    await page.reload();
    await expect(
      page.getByRole('row').filter({ hasText: 'Registered app' }),
    ).toBeVisible();
    await expect(reveal).toHaveCount(0);
  });
});

test.describe('The consent screen', () => {
  test.beforeEach(async ({ context }) => {
    await addClient();
    await addMember();
    await signIn(context, `${MEMBER.id}:${MEMBER.password}`);
  });

  test('sends a code back when the member allows', async ({ page }) => {
    const state = await authorize(page);

    await expect(page).toHaveURL(/\/oauth-consent/);
    await expect(
      page.getByText(`Allow ${CLIENT.title} to use your account?`),
    ).toBeVisible();
    await page.getByRole('button', { name: 'Allow' }).click();

    const answer = await backAtTheClient(page);
    expect(answer.get('code')).toBeTruthy();
    expect(answer.get('state')).toBe(state);
  });

  test('sends an error back when the member denies', async ({ page }) => {
    const state = await authorize(page);

    await page.getByRole('button', { name: 'Deny' }).click();

    const answer = await backAtTheClient(page);
    expect(answer.get('error')).toBe('access_denied');
    expect(answer.get('code')).toBeNull();
    expect(answer.get('state')).toBe(state);
  });

  test('lists an allowed application, and withdraws it', async ({ page }) => {
    await authorize(page);
    await page.getByRole('button', { name: 'Allow' }).click();
    await backAtTheClient(page);

    await page.goto('/applications');
    const row = page.getByRole('row').filter({ hasText: CLIENT.title });
    await expect(row).toBeVisible();

    await row.getByRole('button', { name: 'Withdraw access' }).click();
    const confirm = page.locator('.ui.modal');
    if (await confirm.isVisible()) {
      await confirm.getByRole('button', { name: 'Withdraw access' }).click();
    }

    await expect(row).toHaveCount(0);
    await page.reload();
    await expect(
      page.getByRole('row').filter({ hasText: CLIENT.title }),
    ).toHaveCount(0);
  });
});

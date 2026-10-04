import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';

import {
  serveAuthorization,
  stopServingAuthorization,
  TEST_APP,
} from '../backend';
import { logInAtDex, signInWithDex } from '../dex';

const AURORA = process.env.BASE_URL ?? 'http://localhost:3000';
const CALLBACK = TEST_APP.redirect_uris[0];

let secret = '';

test.beforeAll(async () => {
  secret = await serveAuthorization(AURORA);
});
test.afterAll(stopServingAuthorization);

/**
 * The authorization request an application sends a browser with.
 *
 * @param state What the application will recognise the answer by.
 * @returns The path, at Aurora's address.
 */
function authorizeRequest(state: string): string {
  const params = new URLSearchParams({
    response_type: 'code',
    client_id: TEST_APP.client_id,
    redirect_uri: CALLBACK,
    scope: 'openid profile email',
    state,
  });
  return `/@@oauth-authorize?${params}`;
}

/**
 * Catch the browser on its way back to the application.
 *
 * Nothing listens at the application's address, and nothing has to: the
 * answer is in the URL the authorization endpoint redirects the browser to.
 * Watched as a request rather than intercepted as a route, because
 * Playwright does not route the later hops of a redirect.
 *
 * @param page The page.
 * @returns The answer's query parameters, once the browser is sent there.
 */
async function arrivingAtTheApplication(page: Page) {
  const request = page.waitForRequest((each) =>
    each.url().startsWith(CALLBACK),
  );
  return new URL((await request).url()).searchParams;
}

test.describe('Authorizing an application through Aurora', () => {
  test('asked, agreed, listed, and withdrawn', async ({ page }) => {
    await signInWithDex(page);
    await page.goto(authorizeRequest('agreed'));

    // The question, in the site's own look, naming who would agree.
    await expect(page).toHaveURL(/\/oauth-consent\?/);
    await expect(
      page.getByRole('heading', {
        name: `Allow ${TEST_APP.title} to use your account?`,
      }),
    ).toBeVisible();
    await expect(page.getByText(/You are signed in as/)).toBeVisible();

    const arrived = arrivingAtTheApplication(page);
    await page.getByRole('button', { name: 'Allow' }).click();
    const params = await arrived;
    expect(params.get('state')).toBe('agreed');
    expect(params.get('code')).toBeTruthy();

    // The application's half, from its own server, at Aurora's address too:
    // the discovery document names Aurora, and the code buys tokens there.
    const discovery = await (
      await page.request.get(`${AURORA}/.well-known/openid-configuration`)
    ).json();
    expect(discovery.issuer).toBe(AURORA);
    expect(discovery.token_endpoint).toBe(`${AURORA}/@@oauth-token`);
    // The client authenticates the way it was registered to,
    // `client_secret_post`.
    const tokens = await page.request.post(discovery.token_endpoint, {
      form: {
        grant_type: 'authorization_code',
        code: params.get('code')!,
        redirect_uri: CALLBACK,
        client_id: TEST_APP.client_id,
        client_secret: secret,
      },
    });
    expect(tokens.status()).toBe(200);
    expect(await tokens.json()).toMatchObject({
      token_type: expect.stringMatching(/bearer/i),
      access_token: expect.any(String),
      id_token: expect.any(String),
    });

    // The agreement, on the user's applications page, until withdrawn.
    await page.goto('/applications');
    const row = page.locator(`[data-client="${TEST_APP.client_id}"]`);
    await expect(row).toContainText(TEST_APP.title);
    await row.getByRole('button', { name: 'Withdraw access' }).click();
    await page
      .getByRole('alertdialog')
      .getByRole('button', { name: 'Withdraw access' })
      .click();
    await expect(page.getByRole('status').first()).toContainText(
      'Access withdrawn',
    );
    await expect(row).toHaveCount(0);
  });

  test('refused, and the application told so', async ({ page }) => {
    await signInWithDex(page);
    await page.goto(authorizeRequest('refused'));
    const arrived = arrivingAtTheApplication(page);
    await page.getByRole('button', { name: 'Deny' }).click();

    const params = await arrived;
    expect(params.get('state')).toBe('refused');
    expect(params.get('error')).toBe('access_denied');
  });

  test('a signed-out visitor signs in first, then is asked', async ({
    page,
  }) => {
    await page.goto(authorizeRequest('later'));

    // Plone's challenge, answered with Aurora's login page, which sends the
    // only provider straight to Dex with the request kept.
    await logInAtDex(page);

    await expect(page).toHaveURL(/\/oauth-consent\?/);
    await expect(
      page.getByRole('heading', {
        name: `Allow ${TEST_APP.title} to use your account?`,
      }),
    ).toBeVisible();
  });
});

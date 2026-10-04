import { expect, test } from '@playwright/test';

import { addProvider, removeProvider, SECOND_DEX } from '../backend';
import { logInAtDex, signInWithDex } from '../dex';

// A second provider to link. Beside Dex it would stop `/login` going straight
// to Dex in the other tests, so it is only there for these.
test.beforeAll(() => addProvider(SECOND_DEX));
test.afterAll(() => removeProvider(SECOND_DEX.id));

test.describe('Managing sign-in methods in Aurora', () => {
  test('a signed-out visitor is sent to sign in', async ({ page }) => {
    await page.goto('/identities');

    await expect(page).toHaveURL(/\/login/);
  });

  test('the user menu leads to the sign-in methods', async ({ page }) => {
    await signInWithDex(page);

    await page.getByRole('link', { name: 'Sign-in methods' }).click();

    await expect(page).toHaveURL(/\/identities$/);
    await expect(
      page.getByRole('heading', { name: 'Sign-in methods' }),
    ).toBeVisible();
    // The site's frame is around it: the way back out is still there.
    await expect(page.getByRole('link', { name: 'Log out' })).toBeVisible();
  });

  test('another provider is linked, and removed again', async ({ page }) => {
    await signInWithDex(page);
    await page.goto('/identities');

    // The linked identities; the buttons that add one carry `data-provider`
    // too.
    const linked = page.locator('.identity-identities__list > li');
    const second = linked.and(
      page.locator(`[data-provider="${SECOND_DEX.id}"]`),
    );
    // A run that stopped half way leaves the second identity linked, and
    // the acceptance server keeps it until it restarts.
    await expect(linked.first()).toBeVisible();
    if (await second.count()) {
      await second.getByRole('button', { name: 'Remove' }).click();
    }

    await expect(linked).toHaveCount(1);
    // The only way in cannot be removed.
    await expect(linked.getByRole('button', { name: 'Remove' })).toBeDisabled();

    await page.getByRole('button', { name: 'Dex (second)' }).click();
    // Linking is signing in with the other provider: Dex asks again, since
    // it keeps no session of its own.
    await logInAtDex(page);

    // Back on the page, through the callback, with both identities.
    await page.waitForURL((url) => url.pathname === '/identities');
    await expect(linked).toHaveCount(2);

    await second.getByRole('button', { name: 'Remove' }).click();
    await expect(linked).toHaveCount(1);
  });
});

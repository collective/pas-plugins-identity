import { expect, test } from '@playwright/test';

import { authorizationServer } from '../backend';
import { signInWithDex } from '../dex';

// The other tests run against a site without the authorization server, as
// most sites are; this file installs it for itself and takes it out again.
test.afterAll(() => authorizationServer(false));

test.describe('The applications a user has authorized, in Aurora', () => {
  test('is not offered where there is no authorization server', async ({
    page,
  }) => {
    await authorizationServer(false);
    await signInWithDex(page);

    await expect(
      page.getByRole('link', { name: 'Sign-in methods' }),
    ).toBeVisible();
    await expect(page.getByRole('link', { name: 'Applications' })).toHaveCount(
      0,
    );
  });

  test('is offered, and lists nothing yet, where there is one', async ({
    page,
  }) => {
    await authorizationServer(true);
    await signInWithDex(page);

    await page.getByRole('link', { name: 'Applications' }).click();

    await expect(page).toHaveURL(/\/applications$/);
    await expect(
      page.getByRole('heading', { name: 'Applications' }),
    ).toBeVisible();
    await expect(
      page.getByText('You have not authorized any application.', {
        exact: false,
      }),
    ).toBeVisible();
  });
});

import { expect, test } from '@playwright/test';

import { editProfile, profileOf, requireProfileFields } from '../backend';
import { DEX_USER, signInWithDex } from '../dex';

// A field the Dex user's profile has no value for after a sign-in. Required
// only for these tests: the others sign the same user in, and must not be
// held.
test.beforeAll(async () => {
  await requireProfileFields(['description']);
  // A run before this one may have filled it in.
  const path = await profileOf(DEX_USER.email);
  if (path) {
    await editProfile(path, { description: '' });
  }
});
test.afterAll(() => requireProfileFields([]));

test.describe("Aurora's profile gate", () => {
  test('holds an incomplete profile, and lets it go once complete', async ({
    page,
  }) => {
    await signInWithDex(page);

    // Held, and told why, by the label the form gives the field.
    await expect(page).toHaveURL(/\/complete-profile$/);
    await expect(page.getByRole('status')).toContainText(
      /Please fill in .+ before you can continue\./,
    );
    await expect(
      page.getByRole('link', { name: 'Edit your profile' }),
    ).toHaveAttribute('href', /^\/@@edit\//);

    // Wherever they go, they are held, and the gate remembers where.
    await page.goto('/search');
    await expect(page).toHaveURL(/\/complete-profile$/);

    // Completed -- here by an administrator, where a person would use the
    // form -- the next page lets them through, on to where they were going.
    const path = await profileOf(DEX_USER.email);
    expect(path).not.toBeNull();
    await editProfile(path!, { description: 'Filled in by the tests.' });
    await page.goto('/');
    await expect(page).toHaveURL(/\/search$/);
  });
});

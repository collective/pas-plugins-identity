import {
  addMember,
  addProviders,
  MEMBER,
  signIn,
  signInByMagicLink,
} from '../backend';
import { expect, test } from '../fixtures';

let profile = '';

test.beforeEach(async () => {
  profile = await addMember();
});

test.describe("A user's account panel", () => {
  test("shows the user's addresses on its own tab", async ({
    page,
    context,
  }) => {
    await signIn(context);
    await page.goto(`/controlpanel/users/${MEMBER.id}/account`);

    await page.getByRole('tab', { name: 'Email addresses' }).click();

    await expect(page.getByRole('tabpanel')).toContainText(MEMBER.emails[0]);
  });

  test('shows how somebody signs in, and that they did', async ({
    page,
    context,
  }) => {
    await addProviders();
    const userid = await signInByMagicLink('newcomer@example.org');
    await signIn(context);
    await page.goto(`/controlpanel/users/${userid}/account`);

    await expect(
      page.getByRole('tabpanel', { name: 'Sign-in methods' }),
    ).toContainText('Email');

    await page.getByRole('tab', { name: 'Recent activity' }).click();
    await expect(
      page
        .getByRole('tabpanel', { name: 'Recent activity' })
        .getByRole('listitem')
        .filter({ hasText: /^authenticated\s*email/ }),
    ).toHaveCount(1);
  });
});

test.describe("A member's own sign-in methods", () => {
  test('show their addresses on their own tab', async ({ page, context }) => {
    await signIn(context, `${MEMBER.id}:${MEMBER.password}`);
    await page.goto('/identities');

    await page.getByRole('tab', { name: 'Email addresses' }).click();

    await expect(page.getByRole('tabpanel')).toContainText(MEMBER.emails[0]);
  });
});

test.describe('A Profile', () => {
  test('renders its page', async ({ page, context }) => {
    await signIn(context);
    await page.goto(profile);

    await expect(
      page.getByRole('heading', { name: MEMBER.fullname, level: 1 }),
    ).toBeVisible();
  });
});

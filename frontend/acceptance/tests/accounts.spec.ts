import { addMember, MEMBER, removeMember, signIn } from '../backend';
import { expect, test } from '../fixtures';

test.beforeAll(async () => {
  await addMember();
});
test.afterAll(removeMember);

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
});

test.describe("A member's own sign-in methods", () => {
  test('show their addresses on their own tab', async ({ page, context }) => {
    await signIn(context, `${MEMBER.id}:${MEMBER.password}`);
    await page.goto('/identities');

    await page.getByRole('tab', { name: 'Email addresses' }).click();

    await expect(page.getByRole('tabpanel')).toContainText(MEMBER.emails[0]);
  });
});

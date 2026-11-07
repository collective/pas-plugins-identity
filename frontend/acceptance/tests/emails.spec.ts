import { addMember, MEMBER, removeMember, signIn } from '../backend';
import { expect, moveRowAfter, test } from '../fixtures';

let profile: string;

test.beforeAll(async () => {
  profile = await addMember();
});
test.afterAll(removeMember);

test.describe("A Profile's email addresses", () => {
  test('are listed on the Email tab', async ({ page, context }) => {
    await signIn(context);
    await page.goto(`${profile}/edit`);
    await page.getByText('Email', { exact: true }).click();

    const rows = page.getByRole('row');
    for (const address of MEMBER.emails) {
      await expect(rows.filter({ hasText: address })).toHaveCount(1);
    }
  });

  test('reorder from the keyboard', async ({ page, context }) => {
    await signIn(context);
    await page.goto(`${profile}/edit`);
    await page.getByText('Email', { exact: true }).click();

    const [first, second] = MEMBER.emails;
    await moveRowAfter(
      page,
      page.getByRole('row').filter({ hasText: first }),
      second,
    );

    const order = page.getByRole('row').filter({ hasText: '@example.org' });
    await expect(order.nth(0)).toContainText(second);
    await expect(order.nth(1)).toContainText(first);
  });
});

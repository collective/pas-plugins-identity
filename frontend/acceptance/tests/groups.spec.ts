import { addGroup, addUsers, signIn } from '../backend';
import { expect, test } from '../fixtures';

/** Twelve direct members: more than one page of ten. */
const MEMBERS = Array.from(
  { length: 12 },
  (_, index) => `member${String(index + 1).padStart(2, '0')}`,
);

let team = '';

test.beforeEach(async ({ context }) => {
  await addUsers([...MEMBERS, 'nested', 'newcomer']);
  // `nested` is in `team` only through `inner`.
  await addGroup('inner', ['nested']);
  await addGroup('others');
  team = await addGroup('team', [...MEMBERS, 'inner']);
  await signIn(context);
});

test.describe("A group's page", () => {
  test('lists its members ten at a time', async ({ page }) => {
    await page.goto(team);
    const members = page.getByRole('main').getByRole('link', {
      name: /^User /,
    });

    await expect(members).toHaveCount(10);
    await page
      .getByRole('navigation', { name: 'Pages of members' })
      .getByText('2', { exact: true })
      .click();

    // Twelve direct members and one through `inner`.
    await expect(members).toHaveCount(3);
    await expect(page).toHaveURL(/[?&]page=2\b|[?&]b_start=10\b/);
  });

  test('keeps the page and the search in the URL', async ({ page }) => {
    await page.goto(team);
    await page
      .getByRole('searchbox', { name: 'Search members' })
      .fill('member03');
    await expect(page).toHaveURL(/[?&]q=member03\b/);

    await page.reload();

    await expect(
      page.getByRole('searchbox', { name: 'Search members' }),
    ).toHaveValue('member03');
    await expect(
      page.getByRole('main').getByRole('link', { name: /^User / }),
    ).toHaveCount(1);
  });
});

test.describe("Managing a group's members", () => {
  test('adds a user and a group', async ({ page }) => {
    await page.goto(`${team}/manage-members`);
    const finder = page.getByRole('searchbox', {
      name: 'Find people or groups',
    });
    const members = page.getByRole('searchbox', { name: 'Search members' });
    // Results are ticked, then added together.
    await finder.fill('newcomer');
    await page.getByRole('checkbox', { name: /newcomer/ }).check();
    await page.getByRole('button', { name: 'Add 1 member' }).click();
    // The direct members are paged too: filter them to find the new one.
    await members.fill('newcomer');
    await expect(
      page.getByRole('button', { name: 'Remove User newcomer from this group' }),
    ).toBeVisible();

    await finder.fill('others');
    await page.getByRole('checkbox', { name: /others/ }).check();
    await page.getByRole('button', { name: 'Add 1 member' }).click();
    await members.fill('others');
    await expect(
      page.getByRole('button', { name: 'Remove others from this group' }),
    ).toBeVisible();
  });

  test('removes a direct member', async ({ page }) => {
    await page.goto(`${team}/manage-members`);

    await page
      .getByRole('button', { name: 'Remove User member03 from this group' })
      .click();

    await expect(
      page.getByRole('button', { name: 'Remove User member03 from this group' }),
    ).toHaveCount(0);
    await page.goto(team);
    await expect(
      page.getByRole('main').getByRole('link', { name: 'User member03' }),
    ).toHaveCount(0);
  });

  test('offers no way to remove a member who is only there through a nested group', async ({
    page,
  }) => {
    await page.goto(`${team}/manage-members`);
    await expect(
      page.getByRole('button', { name: 'Remove inner from this group' }),
    ).toBeVisible();

    await page.getByRole('searchbox', { name: 'Search members' }).fill('nested');

    await expect(
      page.getByRole('button', { name: /Remove .*nested.* from this group/ }),
    ).toHaveCount(0);
    // Not because the search found nobody: the group's page lists them.
    await page.goto(`${team}?q=nested`);
    await expect(
      page.getByRole('main').getByRole('link', { name: 'User nested' }),
    ).toBeVisible();
  });
});

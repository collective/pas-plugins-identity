import type { Page } from '@playwright/test';

import { addMember, MEMBER, signIn } from '../backend';
import { expect, test } from '../fixtures';

let profilePath: string;

test.beforeEach(async () => {
  profilePath = await addMember();
});

/**
 * Open the personal tools menu and read its entries.
 *
 * @param page The page, already showing the toolbar.
 * @returns The entries' labels, in menu order.
 */
async function openMenu(page: Page): Promise<string[]> {
  await page.locator('#toolbar-personal').click();
  const entries = page.locator('.personal-tools .pastanaga-menu-list li');
  await expect(entries.first()).toBeVisible();
  return (await entries.allTextContents()).map((text) => text.trim());
}

test.describe('The personal tools menu', () => {
  test("lists the backend's actions on a control panel", async ({
    page,
    context,
  }) => {
    // Volto loads `@actions` with the content of the page's base URL, which
    // for a control panel is the site root. Without the actions the menu
    // falls back to Volto's built-in entries, which have no Sign-in methods.
    await signIn(context);
    await page.goto('/controlpanel/identity-providers');

    const entries = await openMenu(page);

    expect(entries).toContain('Sign-in methods');
    expect(entries.at(-1)).toBe('Site Setup');
  });

  test('offers a member their own Profile', async ({ page, context }) => {
    await signIn(context, `${MEMBER.id}:${MEMBER.password}`);
    await page.goto('/');

    const entries = await openMenu(page);

    expect(entries.slice(0, 3)).toEqual([
      'Profile',
      'Preferences',
      'Sign-in methods',
    ]);
    expect(entries).not.toContain('Site Setup');
    await expect(
      page.locator('.personal-tools').getByRole('link', { name: 'Profile' }),
    ).toHaveAttribute('href', profilePath);
  });
});

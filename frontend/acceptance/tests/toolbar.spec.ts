import { signIn } from '../backend';
import { expect, test } from '../fixtures';

test.describe("The toolbar's user button", () => {
  test('is offered on a control panel', async ({ page, context }) => {
    await signIn(context);
    await page.goto('/controlpanel/identity-providers');

    // Control panels hide the toolbar's default view buttons. Since Volto
    // 19.7 the user button stays, so site setup still leads to the user's
    // own menu.
    const button = page.locator('#toolbar-personal');
    await expect(button).toBeVisible();
    await button.click();
    await expect(page.locator('.personal-tools')).toBeVisible();
  });
});

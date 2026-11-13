import { addPage, addProviders, signIn } from '../backend';
import { expect, test } from '../fixtures';

// The block is `restricted`: no block chooser offers it until a project says
// so, so it reaches a page the way a project's content would, stored with it.
test.beforeEach(async () => {
  await addProviders();
  await addPage('welcome', [{ '@type': 'identitySignIn' }]);
});

test.describe('The Sign-in block', () => {
  test("offers an anonymous visitor the site's ways in", async ({ page }) => {
    await page.goto('/welcome');

    const providers = page.locator('.identity-providers');
    await expect(providers.getByText('Acme', { exact: true })).toBeVisible();
    await expect(providers.getByText('Email', { exact: true })).toBeVisible();
  });

  test('opens in the page editor', async ({ page, context }) => {
    await signIn(context);
    await page.goto('/welcome/edit');

    await expect(page.locator('#toolbar-save')).toBeVisible();
    // Volto's block wrapper and the block's own element both carry the class.
    await expect(page.locator('.block.identitySignIn').first()).toBeVisible();
  });
});

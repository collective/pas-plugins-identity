import { addProviders, signIn } from '../backend';
import { expect, test } from '../fixtures';
import type { Page } from '@playwright/test';

const CONTROLPANEL = '/controlpanel/identity-providers';

test.beforeEach(async ({ context }) => {
  await addProviders();
  await signIn(context);
});

/**
 * Save the form on screen with the toolbar's Save button.
 *
 * @param page The page.
 */
async function save(page: Page): Promise<void> {
  await page
    .getByRole('navigation', { name: 'Toolbar' })
    .getByRole('button', { name: 'Save' })
    .click();
}

/**
 * Pick an option in one of Volto's select widgets.
 *
 * @param page The page.
 * @param label The field's label.
 * @param option The option's text.
 */
async function choose(page: Page, label: string, option: string) {
  // react-select's input is zero-width until something is typed, so it
  // never counts as visible: focus it and open the menu as a keyboard does.
  // react-select's own input is zero-width, so it never counts as visible:
  // open the menu by clicking its control, as a person does. A widget whose
  // vocabulary is still loading re-renders when it arrives and closes a menu
  // opened before that, so the menu is opened until the option shows.
  const control = page
    .locator('.react-select__control')
    .filter({ has: page.getByRole('textbox', { name: label }) });
  // Volto renders its own option component, which carries no option role.
  const choice = page
    .locator('.react-select__option')
    .filter({ hasText: new RegExp(`^${option}$`, 'i') });
  await expect(async () => {
    if (!(await choice.isVisible())) {
      await control.click();
    }
    await expect(choice).toBeVisible({ timeout: 1_000 });
  }).toPass();
  await choice.click();
}

test.describe('Adding a provider', () => {
  test("refuses one without its driver's required settings", async ({
    page,
  }) => {
    await page.goto(`${CONTROLPANEL}/add`);
    await choose(page, 'Driver', 'OpenID Connect');
    await page.getByRole('textbox', { name: 'Title' }).fill('Corp');

    await save(page);

    // The backend's schema refuses it, and the form says so on the field.
    await expect(page).toHaveURL(`${CONTROLPANEL}/add`);
    await page.getByRole('button', { name: 'Settings', exact: true }).click();
    await expect(
      page.locator('.field.error').filter({ hasText: 'Issuer URL' }),
    ).toBeVisible();
  });

  test('adds one once its settings are filled in', async ({ page }) => {
    await page.goto(`${CONTROLPANEL}/add`);
    await choose(page, 'Driver', 'OpenID Connect');
    await page.getByRole('textbox', { name: 'Title' }).fill('Corp');
    await page.getByRole('button', { name: 'Settings', exact: true }).click();
    await page
      .getByRole('textbox', { name: 'Issuer URL' })
      .fill('https://corp.example.org');
    await page.getByRole('textbox', { name: 'Client ID' }).fill('acceptance');
    await page
      .getByRole('textbox', { name: 'Client secret' })
      .fill('acceptance');

    await save(page);

    await expect(page).toHaveURL(CONTROLPANEL);
    await expect(page.getByRole('row', { name: 'Corp' })).toBeVisible();
  });
});

test.describe('Changing a provider', () => {
  test('saves an edited title', async ({ page }) => {
    await page.goto(`${CONTROLPANEL}/acme/edit`);
    await page.getByRole('textbox', { name: 'Title' }).fill('Acme Corp');

    await save(page);

    await expect(page).toHaveURL(CONTROLPANEL);
    await expect(page.getByRole('row', { name: 'Acme Corp' })).toBeVisible();
  });

  test('deletes one only once the deletion is confirmed', async ({ page }) => {
    await page.goto(CONTROLPANEL);
    const modal = page.locator('.ui.modal');

    await page.getByRole('button', { name: 'Delete Acme' }).click();
    await modal.getByRole('button', { name: 'Cancel' }).click();
    await expect(page.getByRole('row', { name: 'Acme' })).toBeVisible();

    await page.getByRole('button', { name: 'Delete Acme' }).click();
    await modal.getByRole('button', { name: 'Delete' }).click();
    await expect(page.getByRole('row', { name: 'Acme' })).toHaveCount(0);
    await expect(page.getByRole('row', { name: 'Email' })).toBeVisible();
  });

  test('maps a claim to a profile field', async ({ page }) => {
    await page.goto(`${CONTROLPANEL}/acme/edit`);
    await page.getByRole('button', { name: 'Mapping', exact: true }).click();
    await page.getByRole('button', { name: 'Add Claim' }).click();
    await page.getByRole('textbox', { name: 'Claim path' }).fill('nickname');
    await choose(page, 'Profile field', 'Full name');

    await save(page);
    await expect(page).toHaveURL(CONTROLPANEL);

    await page.goto(`${CONTROLPANEL}/acme/edit`);
    await page.getByRole('button', { name: 'Mapping', exact: true }).click();
    await expect(
      page.getByRole('textbox', { name: 'Claim path' }),
    ).toHaveValue('nickname');
  });
});

test.describe('What the login page offers', () => {
  test('leaves out a provider hidden from the login screen', async ({
    page,
  }) => {
    await page.goto(`${CONTROLPANEL}/acme/edit`);
    await page.getByText('Show on the login screen', { exact: true }).click();
    await save(page);
    await expect(page).toHaveURL(CONTROLPANEL);

    await page.goto('/login');
    const providers = page.locator('.identity-providers');
    await expect(providers.getByText('Email', { exact: true })).toBeVisible();
    await expect(providers.getByText('Acme', { exact: true })).toHaveCount(0);
  });

  test('leaves out a disabled provider', async ({ page }) => {
    await page.goto(`${CONTROLPANEL}/acme/edit`);
    await page.getByText('Enabled', { exact: true }).click();
    await save(page);
    await expect(page).toHaveURL(CONTROLPANEL);

    await page.goto('/login');
    const providers = page.locator('.identity-providers');
    await expect(providers.getByText('Email', { exact: true })).toBeVisible();
    await expect(providers.getByText('Acme', { exact: true })).toHaveCount(0);
  });
});

test.describe('The providers settings', () => {
  test('save', async ({ page }) => {
    await page.goto(`${CONTROLPANEL}/settings`);
    const timeout = page.getByRole('spinbutton', {
      name: 'Provider discovery timeout in seconds',
    });
    await timeout.fill('7');

    await save(page);

    await page.goto(`${CONTROLPANEL}/settings`);
    await expect(timeout).toHaveValue('7');
  });
});

test.describe('Exporting providers', () => {
  test('downloads every provider as one file', async ({ page }) => {
    await page.goto(CONTROLPANEL);

    const download = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Export every provider' }).click();

    // A GenericSetup registry file, ready to drop into a profile.
    const file = await download;
    const body = (await (await file.createReadStream()).toArray()).join('');
    expect(body).toMatch(/^<registry>/);
    expect(body).toContain('acme');
    expect(body).toContain('email');
  });

  test('downloads a single provider', async ({ page }) => {
    await page.goto(CONTROLPANEL);

    const download = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Export Acme' }).click();

    expect((await download).suggestedFilename()).toMatch(/acme/);
  });
});

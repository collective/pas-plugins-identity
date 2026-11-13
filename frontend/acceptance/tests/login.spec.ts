import {
  addMember,
  addProviders,
  lastSentMail,
  linkIn,
  MEMBER,
} from '../backend';
import { expect, test } from '../fixtures';

test.beforeEach(async () => {
  await addProviders();
  await addMember();
});

test.describe('The login page', () => {
  test('lists the enabled providers and the password option', async ({
    page,
  }) => {
    await page.goto('/login');

    const providers = page.locator('.identity-providers');
    await expect(providers.getByText('Acme', { exact: true })).toBeVisible();
    await expect(providers.getByText('Email', { exact: true })).toBeVisible();
    await expect(
      providers.getByText('Sign in with a password', { exact: true }),
    ).toBeVisible();
  });

  test('signs a member in with a password', async ({ page }) => {
    await page.goto('/login');
    await page.getByText('Sign in with a password', { exact: true }).click();

    await page.getByLabel('Login name').fill(MEMBER.id);
    await page.getByLabel('Password', { exact: true }).fill(MEMBER.password);
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();

    await expect(page.locator('#toolbar-personal')).toBeVisible();
  });

  test('refuses a wrong password with one message', async ({ page }) => {
    await page.goto('/login');
    await page.getByText('Sign in with a password', { exact: true }).click();

    await page.getByLabel('Login name').fill(MEMBER.id);
    await page.getByLabel('Password', { exact: true }).fill('not-the-password');
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();

    await expect(
      page.getByText('That login name and password did not match.'),
    ).toBeVisible();
    await expect(page.locator('#toolbar-personal')).toHaveCount(0);
  });

  test('opens the fallback login form from its own route', async ({ page }) => {
    await page.goto('/fallback_login');

    await expect(page.locator('input[type="password"]')).toBeVisible();
  });
});

test.describe('A magic link', () => {
  test('signs a newcomer in once, and refuses a second use', async ({
    page,
    context,
  }) => {
    // An address nobody has yet: the link creates the account. Linking an
    // address to an existing account is a separate, opt-in setting.
    await page.goto('/login');
    await page.getByText('Email', { exact: true }).click();

    await page.getByLabel('Email address').fill('newcomer@example.org');
    await page.getByRole('button', { name: 'Email me a link' }).click();
    await expect(
      page.getByText('If that address can sign in here'),
    ).toBeVisible();

    const link = linkIn(await lastSentMail());
    await page.goto(link);
    // Signed in, and held on the new Profile until it has a name.
    await expect(
      page.getByRole('heading', { name: 'Complete your profile' }),
    ).toBeVisible();
    await expect(page).toHaveURL(/\/edit$/);

    await context.clearCookies();
    await page.goto(link);
    await expect(
      page.getByText('That sign-in link is no longer valid.'),
    ).toBeVisible();
  });
});

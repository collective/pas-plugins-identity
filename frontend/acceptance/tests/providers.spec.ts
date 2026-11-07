import { addProviders, PROVIDERS, removeProviders, signIn } from '../backend';
import { expect, moveRowAfter, test } from '../fixtures';

const CONTROLPANEL = '/controlpanel/identity-providers';

/** A minimal SVG, which the icon widget accepts. */
const ICON = Buffer.from(
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">' +
    '<circle cx="5" cy="5" r="4"/></svg>',
);

test.beforeAll(addProviders);
test.afterAll(removeProviders);

test.describe('The identity providers control panel', () => {
  test('lists the providers', async ({ page, context }) => {
    await signIn(context);
    await page.goto(CONTROLPANEL);

    for (const provider of PROVIDERS) {
      await expect(
        page.getByRole('row').filter({ hasText: provider.title }),
      ).toHaveCount(1);
    }
  });

  test('reorders the providers from the keyboard', async ({
    page,
    context,
  }) => {
    await signIn(context);
    await page.goto(CONTROLPANEL);

    const [first, second] = PROVIDERS.map((provider) => provider.title);
    const rows = page
      .getByRole('row')
      .filter({ hasText: new RegExp(`${first}|${second}`) });
    await expect(rows.nth(0)).toContainText(first);

    await moveRowAfter(page, rows.nth(0), second);

    await expect(rows.nth(0)).toContainText(second);
    await expect(rows.nth(1)).toContainText(first);

    // The panel saves the order as soon as the row is dropped.
    await page.reload();
    await expect(rows.nth(0)).toContainText(second);
  });
});

test.describe("A provider's icon", () => {
  test('is chosen with the file picker and previewed', async ({
    page,
    context,
  }) => {
    await signIn(context);
    await page.goto(`${CONTROLPANEL}/${PROVIDERS[0].id}/edit`);
    await page.getByText('Style', { exact: true }).click();

    const chooser = page.waitForEvent('filechooser');
    await page.getByRole('button', { name: 'Choose a file' }).click();
    await (
      await chooser
    ).setFiles({
      name: 'acme.svg',
      mimeType: 'image/svg+xml',
      buffer: ICON,
    });

    await expect(
      page.getByTestId('provider-icon-preview').getByRole('img'),
    ).toBeVisible();
  });
});

/**
 * The `test` every spec imports: Playwright's, failing on any page error.
 *
 * A component that throws while rendering does not always break what a test
 * looks at next. Volto replaces the page with its error view, and a widget
 * whose press handler never connects throws nothing at all. So a test fails
 * on any uncaught error the page reports, whatever its own assertions say.
 */
import { expect, test as base } from '@playwright/test';
import type { Locator, Page } from '@playwright/test';

export const test = base.extend({
  page: async ({ page }, use) => {
    const errors: string[] = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await use(page);
    expect(errors, 'Uncaught errors on the page').toEqual([]);
  },
});

/**
 * Move a table row below another, the way a keyboard user does.
 *
 * Focusing the drag handle directly does not work in a browser: react-aria's
 * grid moves the focus to the row as soon as anything in it is focused. So
 * the row takes the focus, the right arrow reaches its handle and Enter
 * picks the row up. Where the drop indicator starts is react-aria's choice,
 * so the down arrow is pressed until the indicator after `after` has the
 * focus, and Enter drops the row there.
 *
 * @param page The page.
 * @param row The row to move.
 * @param after The name of the row to drop it after, as react-aria
 *   announces it.
 */
export async function moveRowAfter(
  page: Page,
  row: Locator,
  after: string,
): Promise<void> {
  const focused = page.locator(':focus');
  await row.focus();
  await page.keyboard.press('ArrowRight');
  await expect(focused).toHaveAttribute('slot', 'drag');
  await page.keyboard.press('Enter');
  const target = `Insert after ${after}`;
  for (let step = 0; step < 10; step += 1) {
    if ((await focused.getAttribute('aria-label')) === target) {
      break;
    }
    await page.keyboard.press('ArrowDown');
  }
  await expect(focused).toHaveAttribute('aria-label', target);
  await page.keyboard.press('Enter');
}

export { expect };

/**
 * Every route the add-on adds, checked the same three ways.
 *
 * An accessibility scan, scoped to `#main` so it judges what this add-on
 * draws rather than Volto's header and footer. A direct load, as a bookmark
 * or a reload makes it, watched for React's hydration errors: the server
 * rendered one thing and the browser another. And two screens in pt_BR.
 */
import AxeBuilder from '@axe-core/playwright';
import type { BrowserContext, Page } from '@playwright/test';

import {
  addGroup,
  addMember,
  addProviders,
  MEMBER,
  setSiteLanguage,
  signIn,
} from '../backend';
import { expect, test } from '../fixtures';

interface Route {
  /** What the route is, for the test's title. */
  name: string;
  /** The path, below the site. */
  path: string;
  /** Who opens it: the Manager, the member, or nobody. */
  as: 'manager' | 'member' | 'anonymous';
}

let profile = '';
let group = '';

test.beforeEach(async () => {
  await addProviders();
  profile = await addMember();
  group = await addGroup('team', [MEMBER.id]);
});

/** The routes, built once the site has a Profile and a group to point at. */
function routes(): Route[] {
  return [
    { name: 'the login page', path: '/login', as: 'anonymous' },
    { name: 'the fallback login', path: '/fallback_login', as: 'anonymous' },
    { name: 'a sign-in methods page', path: '/identities', as: 'member' },
    { name: 'the applications page', path: '/applications', as: 'member' },
    {
      name: 'the providers control panel',
      path: '/controlpanel/identity-providers',
      as: 'manager',
    },
    {
      name: 'the providers settings',
      path: '/controlpanel/identity-providers/settings',
      as: 'manager',
    },
    {
      name: 'the add-provider form',
      path: '/controlpanel/identity-providers/add',
      as: 'manager',
    },
    {
      name: 'a provider edit form',
      path: '/controlpanel/identity-providers/acme/edit',
      as: 'manager',
    },
    {
      name: 'the OAuth clients control panel',
      path: '/controlpanel/identity-clients',
      as: 'manager',
    },
    {
      name: "a user's account panel",
      path: `/controlpanel/users/${MEMBER.id}/account`,
      as: 'manager',
    },
    { name: 'a Profile', path: profile, as: 'manager' },
    { name: "a group's page", path: group, as: 'manager' },
    {
      name: "a group's member management",
      path: `${group}/manage-members`,
      as: 'manager',
    },
  ];
}

/**
 * Give the browser the session a route is opened with.
 *
 * @param context The browser context.
 * @param as Who opens the route.
 */
async function sessionFor(
  context: BrowserContext,
  as: Route['as'],
): Promise<void> {
  if (as === 'manager') {
    await signIn(context);
  } else if (as === 'member') {
    await signIn(context, `${MEMBER.id}:${MEMBER.password}`);
  }
}

/**
 * Wait until the route has drawn its own content, not just Volto's frame.
 *
 * @param page The page.
 */
async function settled(page: Page): Promise<void> {
  await page.waitForLoadState('networkidle');
  await expect(page.locator('#main')).toBeVisible();
}

// The table is built from paths only known once the site is seeded, so the
// tests are generated per index and read their route inside the test.
const COUNT = 13;

for (let index = 0; index < COUNT; index += 1) {
  test(`route ${index + 1} passes an accessibility scan`, async ({
    page,
    context,
  }) => {
    const route = routes()[index];
    test.info().annotations.push({ type: 'route', description: route.name });
    await sessionFor(context, route.as);
    await page.goto(route.path);
    await settled(page);

    const results = await new AxeBuilder({ page })
      .include('#main')
      // Volto's own select widget draws its placeholder in a grey that fails
      // the contrast check. That is Volto's to fix, not this add-on's.
      .exclude('.react-select__placeholder')
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();

    expect(
      results.violations.map(
        (violation) =>
          `${violation.id}: ${violation.nodes.map((node) => node.target.join(' ')).join(', ')}`,
      ),
      `Accessibility violations on ${route.name}`,
    ).toEqual([]);
  });

  test(`route ${index + 1} hydrates without errors when loaded directly`, async ({
    page,
    context,
  }) => {
    const route = routes()[index];
    test.info().annotations.push({ type: 'route', description: route.name });
    const errors: string[] = [];
    page.on('console', (message) => {
      // A production build reports a hydration mismatch as a minified
      // React error (#418, #423, #425); a development build in words.
      if (
        message.type() === 'error' &&
        /Minified React error #(418|419|421|422|423|425)|[Hh]ydrat|did not match/.test(
          message.text(),
        )
      ) {
        errors.push(message.text());
      }
    });
    await sessionFor(context, route.as);

    await page.goto(route.path);
    await settled(page);

    expect(errors, `Hydration errors on ${route.name}`).toEqual([]);
  });
}

test('the route table and COUNT agree', () => {
  expect(routes()).toHaveLength(COUNT);
});

test.describe('In Brazilian Portuguese', () => {
  test.beforeEach(async () => {
    await setSiteLanguage('pt-br');
  });

  test('the login page', async ({ page }) => {
    await page.goto('/login');

    await expect(
      page.getByText('Escolha como gostaria de entrar.'),
    ).toBeVisible();
    await expect(page.getByText('Entrar com uma senha')).toBeVisible();
  });

  test('the providers control panel', async ({ page, context }) => {
    await signIn(context);
    await page.goto('/controlpanel/identity-providers');

    await expect(page.getByText('Provedores de identidade')).toBeVisible();
    await expect(
      page.getByRole('link', { name: 'Adicionar provedor' }),
    ).toBeVisible();
  });
});

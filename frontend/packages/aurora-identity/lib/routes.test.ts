import { describe, expect, it } from 'vitest';
import type { ReactRouterRouteEntry } from '@plone/types';

import {
  addRouteUnder,
  AURORA_LOGIN_FILE,
  PUBLIC_LAYOUT_FILE,
  replaceRouteFile,
} from './routes';

const OURS = '@plone-collective/aurora-identity/routes/login.tsx';

/**
 * The routes as `@plone/cmsui` registers them: the login page two levels
 * down, under the layout and a prefix.
 *
 * @returns A fresh copy.
 */
function cmsuiRoutes(): ReactRouterRouteEntry[] {
  return [
    {
      type: 'layout',
      file: '@plone/cmsui/routes/layout.tsx',
      children: [
        {
          type: 'prefix',
          path: 'login',
          children: [{ type: 'route', path: '*', file: AURORA_LOGIN_FILE }],
        },
        {
          type: 'prefix',
          path: 'logout',
          children: [
            {
              type: 'route',
              path: '*',
              file: '@plone/cmsui/routes/auth/logout.tsx',
            },
          ],
        },
      ],
    },
  ];
}

describe('replaceRouteFile', () => {
  it('replaces the login page wherever it is nested', () => {
    const routes = cmsuiRoutes();

    expect(replaceRouteFile(routes, AURORA_LOGIN_FILE, OURS)).toBe(1);
    expect(JSON.stringify(routes)).toContain(OURS);
    expect(JSON.stringify(routes)).not.toContain(AURORA_LOGIN_FILE);
  });

  it('leaves the path, the layout and every other route alone', () => {
    const routes = cmsuiRoutes();
    const expected = JSON.parse(
      JSON.stringify(routes).replace(AURORA_LOGIN_FILE, OURS),
    );

    replaceRouteFile(routes, AURORA_LOGIN_FILE, OURS);

    expect(routes).toEqual(expected);
  });

  it('says so when there is nothing to replace', () => {
    const routes = cmsuiRoutes();

    expect(replaceRouteFile(routes, '@plone/cmsui/routes/gone.tsx', OURS)).toBe(
      0,
    );
    expect(routes).toEqual(cmsuiRoutes());
  });
});

/**
 * The routes as `@plone/publicui` registers them, beside cmsui's.
 *
 * @returns A fresh copy.
 */
function siteRoutes(): ReactRouterRouteEntry[] {
  return [
    ...cmsuiRoutes(),
    {
      type: 'layout',
      file: PUBLIC_LAYOUT_FILE,
      children: [
        {
          type: 'route',
          path: 'search',
          file: '@plone/publicui/routes/search.tsx',
        },
        {
          type: 'route',
          path: '*',
          file: '@plone/publicui/routes/content.tsx',
        },
      ],
    },
  ];
}

const PAGE: ReactRouterRouteEntry = {
  type: 'route',
  path: 'identities',
  file: '@plone-collective/aurora-identity/routes/identities.tsx',
};

describe('addRouteUnder', () => {
  it("adds the page to the site's layout, beside its own pages", () => {
    const routes = siteRoutes();

    expect(addRouteUnder(routes, PUBLIC_LAYOUT_FILE, PAGE)).toBe(true);
    const layout = routes[1] as { children: ReactRouterRouteEntry[] };
    expect(layout.children).toContainEqual(PAGE);
    expect(layout.children).toHaveLength(3);
  });

  it('leaves every other route alone', () => {
    const routes = siteRoutes();

    addRouteUnder(routes, PUBLIC_LAYOUT_FILE, PAGE);

    expect(routes[0]).toEqual(cmsuiRoutes()[0]);
  });

  it('says so when the layout is not there', () => {
    const routes = cmsuiRoutes();

    expect(addRouteUnder(routes, PUBLIC_LAYOUT_FILE, PAGE)).toBe(false);
    expect(routes).toEqual(cmsuiRoutes());
  });
});

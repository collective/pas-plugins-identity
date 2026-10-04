import { describe, expect, it } from 'vitest';
import type { ReactRouterRouteEntry } from '@plone/types';

import { AURORA_LOGIN_FILE, replaceRouteFile } from './routes';

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

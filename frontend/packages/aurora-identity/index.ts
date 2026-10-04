/**
 * The Aurora add-on for `pas.plugins.identity`.
 *
 * Sign-in with external identity providers: a login page offering them, the
 * route that starts a sign-in with one of them, and the route they send the
 * browser back to. And for a signed-in user, the page that manages their
 * sign-in methods, with its entry among their tools.
 * @module aurora-identity
 */
import type { ConfigType } from '@plone/registry';

import IdentityTools from './slots/IdentityTools';
import { CALLBACK_PATH, IDENTITIES_PATH, START_PATH } from './lib/paths';
import {
  addRouteUnder,
  AURORA_LOGIN_FILE,
  PUBLIC_LAYOUT_FILE,
  replaceRouteFile,
} from './lib/routes';
import { DEFAULT_SETTINGS } from './lib/settings';
import type { IdentitySettings } from './lib/settings';

/** The add-on's login page, rendered at Aurora's `/login`. */
const LOGIN_FILE = '@plone-collective/aurora-identity/routes/login.tsx';

/** The sign-in methods page. */
const IDENTITIES_ROUTE = {
  type: 'route' as const,
  path: IDENTITIES_PATH.slice(1),
  file: '@plone-collective/aurora-identity/routes/identities.tsx',
  options: { id: 'identity-identities' },
};

export default function install(config: ConfigType) {
  // Merged under whatever is already there: these are defaults, and an
  // add-on configured before this one may have set either.
  const settings = config.settings as { identity?: Partial<IdentitySettings> };
  settings.identity = { ...DEFAULT_SETTINGS, ...settings.identity };

  // `@plone/cmsui` registers `/login` before this add-on is configured, so
  // its route is there to be given this add-on's page. Should Aurora move or
  // rename that file, the site keeps Aurora's page, without the providers,
  // rather than failing to start -- and says so while it is being built.
  if (!replaceRouteFile(config.routes ?? [], AURORA_LOGIN_FILE, LOGIN_FILE)) {
    // eslint-disable-next-line no-console
    console.warn(
      `@plone-collective/aurora-identity: no route renders ${AURORA_LOGIN_FILE}, so /login is left as it is, without the identity providers.`,
    );
  }

  // Inside the site's frame, with its header, so the user menu that leads
  // here also leads back. Without publicui, at the top of the tree.
  if (
    !addRouteUnder(config.routes ?? [], PUBLIC_LAYOUT_FILE, IDENTITIES_ROUTE)
  ) {
    config.registerRoute(IDENTITIES_ROUTE);
  }
  config.registerSlotComponent({
    name: 'IdentityTools',
    slot: 'authenticatedTools',
    component: IdentityTools,
  });

  // Path segments without their leading slash, the way Aurora's own routes
  // are registered.
  config.registerRoute({
    type: 'route',
    path: `${START_PATH.slice(1)}/:provider`,
    file: '@plone-collective/aurora-identity/routes/start.ts',
    options: { id: 'identity-start' },
  });
  config.registerRoute({
    type: 'route',
    path: CALLBACK_PATH.slice(1),
    file: '@plone-collective/aurora-identity/routes/callback.tsx',
    options: { id: 'identity-callback' },
  });

  return config;
}

/**
 * The Aurora add-on for `pas.plugins.identity`.
 *
 * Sign-in with external identity providers: a login page offering them, the
 * route that starts a sign-in with one of them, and the route they send the
 * browser back to. And for a signed-in user: the page that manages their
 * sign-in methods, with its entry among their tools, and the profile gate,
 * which holds them until their profile is complete.
 * @module aurora-identity
 */
import type { ConfigType } from '@plone/registry';

import IdentityTools from './slots/IdentityTools';
import ProfileGate from './slots/ProfileGate';
import { COMPLETE_PROFILE_PATH } from './lib/gate';
import {
  APPLICATIONS_PATH,
  CALLBACK_PATH,
  CONFIRM_EMAIL_PATH,
  IDENTITIES_PATH,
  START_PATH,
} from './lib/paths';
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

/** The signed-in user's pages, inside the site's frame. */
const USER_ROUTES = [
  {
    type: 'route' as const,
    path: IDENTITIES_PATH.slice(1),
    file: '@plone-collective/aurora-identity/routes/identities.tsx',
    options: { id: 'identity-identities' },
  },
  {
    type: 'route' as const,
    path: CONFIRM_EMAIL_PATH.slice(1),
    file: '@plone-collective/aurora-identity/routes/confirm-email.tsx',
    options: { id: 'identity-confirm-email' },
  },
  {
    type: 'route' as const,
    path: APPLICATIONS_PATH.slice(1),
    file: '@plone-collective/aurora-identity/routes/applications.tsx',
    options: { id: 'identity-applications' },
  },
  {
    type: 'route' as const,
    path: COMPLETE_PROFILE_PATH.slice(1),
    file: '@plone-collective/aurora-identity/routes/complete-profile.tsx',
    options: { id: 'identity-complete-profile' },
  },
];

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
  for (const route of USER_ROUTES) {
    if (!addRouteUnder(config.routes ?? [], PUBLIC_LAYOUT_FILE, route)) {
      config.registerRoute(route);
    }
  }
  config.registerSlotComponent({
    name: 'IdentityTools',
    slot: 'authenticatedTools',
    component: IdentityTools,
  });
  // The profile gate, on every page with the site's header. It draws
  // nothing; the slot is only where every signed-in page mounts it.
  config.registerSlotComponent({
    name: 'IdentityProfileGate',
    slot: 'authenticatedTools',
    component: ProfileGate,
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

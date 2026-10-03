/**
 * The Aurora add-on for `pas.plugins.identity`.
 *
 * Sign-in with external identity providers: their buttons on the login page,
 * the route that starts a sign-in with one of them, and the route they send
 * the browser back to.
 * @module aurora-identity
 */
import type { ConfigType } from '@plone/registry';

import LoginProviders from './slots/LoginProviders';
import { CALLBACK_PATH, START_PATH } from './lib/paths';

export default function install(config: ConfigType) {
  config.registerSlotComponent({
    name: 'IdentityLoginProviders',
    slot: 'loginActions',
    component: LoginProviders,
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

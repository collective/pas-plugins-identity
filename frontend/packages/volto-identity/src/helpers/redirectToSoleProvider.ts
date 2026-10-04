/**
 * Whether the login page signs a visitor in straight away when there is only
 * one way to.
 * @module helpers/redirectToSoleProvider
 */
import { runtimeConfig } from '@plone/volto/runtime_config';
import config from '@plone/volto/registry';

import { asBoolean } from '@plone-collective/identity-core';

/**
 * The environment variable a deployment answers this with.
 *
 * Read the way `RAZZLE_IDENTITY_SHOW_PLONE_LOGIN` is, and for the same
 * reason: see `showPloneLogin`.
 */
export const REDIRECT_TO_SOLE_PROVIDER_ENV =
  'RAZZLE_IDENTITY_REDIRECT_TO_SOLE_PROVIDER';

// The `?choose` parameter is identity-core's, shared with the Aurora add-on.
export {
  asksToChoose,
  CHOOSE_LOGIN_PATH,
  CHOOSE_PARAM,
} from '@plone-collective/identity-core';

/**
 * Decide whether a sole provider is started without asking.
 *
 * `config.settings.identity.redirectToSoleProvider` is the fallback and the
 * environment wins over it. With neither saying anything the answer is yes,
 * which is what the login page did before this was a setting.
 *
 * This is the site's answer only. The login page also declines for a
 * visitor who arrived signed in and for one who asked to choose.
 *
 * @returns Whether to redirect to a sole provider.
 */
export function redirectToSoleProvider(): boolean {
  return asBoolean(
    (runtimeConfig as Record<string, string | undefined>)?.[
      REDIRECT_TO_SOLE_PROVIDER_ENV
    ],
    config.settings.identity?.redirectToSoleProvider ?? true,
  );
}

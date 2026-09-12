/**
 * Whether the login page signs a visitor in straight away when there is only
 * one way to.
 * @module helpers/redirectToSoleProvider
 */
import { runtimeConfig } from '@plone/volto/runtime_config';
import config from '@plone/volto/registry';

import { asBoolean } from '../config/settings';

/**
 * The environment variable a deployment answers this with.
 *
 * Read the way `RAZZLE_IDENTITY_SHOW_PLONE_LOGIN` is, and for the same
 * reason: see `showPloneLogin`.
 */
export const REDIRECT_TO_SOLE_PROVIDER_ENV =
  'RAZZLE_IDENTITY_REDIRECT_TO_SOLE_PROVIDER';

/**
 * The query parameter that asks `/login` to show its options anyway.
 *
 * Its presence is the request, whatever its value.
 */
export const CHOOSE_PARAM = 'choose';

/**
 * The login page with its options on screen, whatever the setting says.
 *
 * Where the callback page sends a visitor whose sign-in failed. Plain
 * `/login` would start the same provider again, and a provider that refuses
 * somebody refuses them every time.
 */
export const CHOOSE_LOGIN_PATH = `/login?${CHOOSE_PARAM}=1`;

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

/**
 * Whether a query string asks for the options rather than the redirect.
 *
 * @param search The location's query string.
 * @returns Whether `choose` is on it.
 */
export function asksToChoose(search: string): boolean {
  return new URLSearchParams(search).has(CHOOSE_PARAM);
}

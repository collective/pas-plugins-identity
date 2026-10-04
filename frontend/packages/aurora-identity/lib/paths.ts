/**
 * The add-on's own routes, and where a sign-in returns to.
 * @module lib/paths
 */
import { returnUrl } from '@plone-collective/identity-core';

/**
 * The route a provider redirects back to.
 *
 * `DEFAULT_CALLBACK_PATH` in `pas.plugins.identity.core.controlpanel`, and
 * `CALLBACK_PATH` in the Volto add-on: the redirect URI registered with each
 * provider, so it has to be the same whichever frontend serves the site.
 */
export const CALLBACK_PATH = '/login-identity';

/**
 * Where a signed-in user manages their own sign-in methods.
 *
 * `IDENTITIES_PATH` in the Volto add-on, so a link to it works on either.
 */
export const IDENTITIES_PATH = '/identities';

/**
 * Where a user is asked which of their verified addresses stands for them.
 *
 * `CONFIRM_EMAIL_PATH` in `identity-core`, which the profile gate sends to.
 */
export { CONFIRM_EMAIL_PATH } from '@plone-collective/identity-core';

/** The route a provider button sends the browser to, to start a sign-in. */
export const START_PATH = `${CALLBACK_PATH}/start`;

/**
 * Provider ids the backend accepts.
 *
 * `PROVIDER_ID_PATTERN` in `pas.plugins.identity.core.controlpanel`. Checked
 * here as well because `endpoints.loginProvider` puts the id into a path
 * unencoded.
 */
export const PROVIDER_ID = /^[A-Za-z0-9_-]+$/;

/**
 * The path a provider button starts a sign-in at.
 *
 * @param providerId The provider.
 * @param cameFrom Where to return to afterwards; nowhere in particular when
 *   empty.
 * @returns The path.
 */
export function startPath(providerId: string, cameFrom = ''): string {
  const query = cameFrom ? `?came_from=${encodeURIComponent(cameFrom)}` : '';
  return `${START_PATH}/${providerId}${query}`;
}

/**
 * Where to send somebody once they are signed in.
 *
 * Only a path on this site: `came_from` round-trips through the provider and
 * the backend, and an absolute URL there would make the callback an open
 * redirect.
 *
 * @param cameFrom The `came_from` the backend answered with.
 * @returns A site-relative path.
 */
export function afterSignIn(cameFrom: string | undefined | null): string {
  return returnUrl(
    `?came_from=${encodeURIComponent(cameFrom ?? '')}`,
    '/login',
  );
}

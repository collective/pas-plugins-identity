/**
 * Deciding where a just-signed-in user lands when the site has Profiles.
 *
 * Pure, and separate from the container, for the same reason `returnUrl` is:
 * the decision is small, it is easy to get subtly wrong, and every branch of
 * it deserves a test that does not need a store.
 * @module helpers/firstLogin
 */

import type { MyProfile } from '../types';

/**
 * Turn an absolute backend URL into a path this Volto app can route to.
 *
 * The backend answers with the URL it is served under, which in a split
 * deployment is not the URL the browser is on. Passing that straight to
 * `history.push` would navigate off the frontend and land the user on the
 * backend's own rendering of the Profile.
 *
 * @param url Absolute or relative URL from the backend.
 * @param apiPath The backend's base URL, when it differs from the frontend's.
 * @returns A site-relative path, always beginning with a slash.
 */
export function toAppPath(url: string, apiPath = ''): string {
  if (!url) {
    return '/';
  }
  let path = url;
  if (apiPath && path.startsWith(apiPath)) {
    path = path.slice(apiPath.length);
  } else {
    // No configured base, or the answer came from somewhere else: fall back to
    // stripping the origin, which is all a path needs.
    const match = /^https?:\/\/[^/]+(\/.*)?$/.exec(path);
    if (match) {
      path = match[1] ?? '/';
    }
  }
  return path.startsWith('/') ? path : `/${path}`;
}

/**
 * Work out where to send a user who has just signed in.
 *
 * Only an `incomplete` Profile diverts them. Every other answer — no Profile,
 * a `complete` one, a `deactivated` one, a site without the extra installed —
 * means "carry on where you were going". Diverting on anything else would
 * trap a user with a deliberately sparse profile in a loop they cannot leave.
 *
 * @param profile The `@my-profile` answer, or null before it has loaded.
 * @param fallback Where the user was heading.
 * @param apiPath The backend's base URL, when it differs from the frontend's.
 * @returns The path to navigate to.
 */
export function afterLogin(
  profile: MyProfile | null | undefined,
  fallback: string,
  apiPath = '',
): string {
  if (!profile?.profile || profile.review_state !== 'incomplete') {
    return fallback;
  }
  return toAppPath(profile.profile, apiPath);
}

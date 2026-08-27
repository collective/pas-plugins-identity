/**
 * Deciding whether a user may go where they are going.
 *
 * The backend holds a user with an incomplete profile on its edit form, and
 * deliberately lets `plone.restapi` requests through: Volto fetches the edit
 * form itself over the API, so gating those would break the page the user is
 * being sent to. Everything this app navigates to is an API request, which
 * means the backend gate never fires for a Volto site and this is where the
 * same rule lives.
 *
 * Pure and separate from the component for the reason `firstLogin` is: the
 * decision is small, every branch of it is a way to trap somebody in a
 * redirect loop, and each one deserves a test that needs no store.
 * @module helpers/profileGate
 */

import { toAppPath } from './firstLogin';

import type { MyProfile } from '../types';

/**
 * Routes never gated, whatever state the profile is in.
 *
 * Signing in has to be able to finish, and signing out has to be possible for
 * somebody who would rather leave than fill the form in. `/first-login` is
 * here because it is the route that decides where to send them: gating it
 * would replace its answer with this one before it had a chance to give it.
 */
export const EXEMPT_PATHS = [
  '/login',
  '/login-identity',
  '/logout',
  '/first-login',
  '/oauth-consent',
];

/**
 * Where the pending destination is kept while the user fills the form in.
 *
 * `sessionStorage` rather than the URL, because the URL does not survive the
 * step that matters: saving the form navigates to the profile's own view and
 * drops the query string with it. Rather than the redux store, because a
 * reload mid-detour would lose that too, and a user who reloads a form they
 * were sent to should still be returned afterwards.
 */
export const RETURN_KEY = 'volto-identity:profile-return';

/**
 * Remember where the user was going before the gate interrupted them.
 *
 * Every access is guarded: `sessionStorage` throws outright in a private
 * window in some browsers, and does not exist at all during server-side
 * rendering. Losing the return is a worse journey; throwing here would be a
 * blank page.
 *
 * @param path Site-relative path to come back to.
 */
export function rememberReturn(path: string): void {
  if (typeof window === 'undefined' || !path) {
    return;
  }
  try {
    window.sessionStorage.setItem(RETURN_KEY, path);
  } catch {
    // No storage. The user completes their profile and stays there, which is
    // where they would have stayed before any of this existed.
  }
}

/**
 * Take the remembered destination, clearing it.
 *
 * Reading and clearing together, so a return can never fire twice: the second
 * navigation would send somebody back to a page they had already left.
 *
 * @returns The remembered path, or null.
 */
export function takeReturn(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    const value = window.sessionStorage.getItem(RETURN_KEY);
    if (value) {
      window.sessionStorage.removeItem(RETURN_KEY);
    }
    return value || null;
  } catch {
    return null;
  }
}

/**
 * The path of a profile's edit form.
 *
 * @param profileUrl The absolute URL the backend reported.
 * @param apiPath The backend's base URL, when it differs from the frontend's.
 * @returns A site-relative path.
 */
export function editPath(profileUrl: string, apiPath = ''): string {
  return `${toAppPath(profileUrl, apiPath)}/edit`;
}

/**
 * Work out where a user must be sent, if anywhere.
 *
 * Returns `null` for every reason not to gate, which is most of them: no
 * profile, a complete one, a site without the `[content]` extra, an answer
 * that has not arrived, an exempt route, and — the one that matters — being
 * already on the profile the redirect would send them to.
 *
 * That last check covers the whole profile rather than its edit form alone.
 * The form loads widgets and vocabularies against paths beneath it, and a
 * user who saves is bounced to the profile's view; gating either would be a
 * loop that no amount of correct configuration escapes.
 *
 * @param profile The `@my-profile` answer, or null before it has loaded.
 * @param pathname The path the app is on.
 * @param apiPath The backend's base URL, when it differs from the frontend's.
 * @returns The path to redirect to, or null to let the user through.
 */
export function gateTarget(
  profile: MyProfile | null | undefined,
  pathname: string,
  apiPath = '',
): string | null {
  if (!profile?.profile || profile.review_state !== 'incomplete') {
    return null;
  }
  const current = pathname || '/';
  if (
    EXEMPT_PATHS.some(
      (path) => current === path || current.startsWith(`${path}/`),
    )
  ) {
    return null;
  }
  const profilePath = toAppPath(profile.profile, apiPath);
  if (current === profilePath || current.startsWith(`${profilePath}/`)) {
    return null;
  }
  return editPath(profile.profile, apiPath);
}

/**
 * Where Aurora's profile gate sends a signed-in user, if anywhere.
 *
 * The rule is `identity-core`'s `gateTarget`, the one the Volto add-on
 * follows, with one difference: a held user is sent to
 * `COMPLETE_PROFILE_PATH`, which says what is missing and links to the edit
 * form, rather than to the edit form itself. Volto says why in a toast as it
 * redirects; Aurora has no toast that every page shows, and its edit form is
 * `@plone/cmsui`'s, where the add-on cannot say anything.
 * @module lib/gate
 */
import {
  awaitingConfirmation,
  CONFIRM_EMAIL_PATH,
  EXEMPT_PATHS,
  onProfile,
  toAppPath,
} from '@plone-collective/identity-core';
import type { MyProfile } from '@plone-collective/identity-core';

/** The page a held user is sent to, explaining why. */
export const COMPLETE_PROFILE_PATH = '/complete-profile';

/**
 * The key the root loader carries the user's `@my-profile` answer under.
 *
 * Namespaced, since every add-on's root loader data is merged into one
 * object.
 */
export const PROFILE_KEY = 'identityProfile';

/**
 * Aurora's edit form for a profile.
 *
 * @param profileUrl The profile's URL, as the backend answered it.
 * @returns The form's path: `/@@edit` and the profile's path.
 */
export function profileEditPath(profileUrl: string): string {
  return `/@@edit${toAppPath(profileUrl)}`;
}

/**
 * Whether a profile is being held until it is complete.
 *
 * @param profile The `@my-profile` answer.
 * @returns Whether its owner is held.
 */
export function isHeld(profile: MyProfile | null | undefined): boolean {
  return !!profile?.profile && profile.review_state === 'incomplete';
}

/**
 * Work out where a user must be sent, if anywhere.
 *
 * @param profile The `@my-profile` answer, or null without one.
 * @param pathname The path the user is on.
 * @returns The path to send them to, or null to let them through.
 */
export function gateTarget(
  profile: MyProfile | null | undefined,
  pathname: string,
): string | null {
  if (!isHeld(profile)) {
    return null;
  }
  const current = pathname || '/';
  const under = (path: string) =>
    current === path || current.startsWith(`${path}/`);
  if (EXEMPT_PATHS.some(under)) {
    return null;
  }
  // Ahead of every other exemption: the profile and its form are exactly
  // where this answer cannot be given.
  if (awaitingConfirmation(profile)) {
    return current === CONFIRM_EMAIL_PATH ? null : CONFIRM_EMAIL_PATH;
  }
  if (
    under(COMPLETE_PROFILE_PATH) ||
    onProfile(profile, current) ||
    under(profileEditPath(profile!.profile!))
  ) {
    return null;
  }
  return COMPLETE_PROFILE_PATH;
}

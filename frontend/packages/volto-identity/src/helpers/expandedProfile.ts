/**
 * The profile state a Volto content response carried along, if any.
 *
 * Lives in the Volto add-on rather than in `identity-core`, because it reads
 * Volto's Redux `content` slice and flattens URLs with Volto's own helper.
 * @module helpers/expandedProfile
 */

import { flattenToAppURL } from '@plone/volto/helpers/Url/Url';

/**
 * Read the `my-profile` component off a content response, if it belongs here.
 *
 * The backend offers the profile state as an expandable component, so a
 * signed-in user's navigation to a content route brings it along and the gate
 * needs no request of its own.
 *
 * **Why the path is checked.** Volto keeps the last content it loaded in the
 * store, and a route that fetches no content -- `/login`, `/identities`, a
 * control panel -- leaves the previous page's answer sitting there. Using it
 * would be reading a stale answer for a question whose whole point is
 * freshness: finishing the profile form is a navigation, and a gate acting on
 * the answer from before the save holds a user on a profile they have already
 * completed.
 *
 * Unexpanded the component is just an `@id`, which is not an answer. `userid`
 * is what tells the two apart.
 *
 * `flattenToAppURL` rather than this module's own `toAppPath`, and that is the
 * one judgement call here. Volto's content reducer stores `@id` exactly as the
 * backend sent it -- it flattens `items[].url` and nothing else -- so this
 * compares a backend URL against a router path, and only the configured
 * `apiPath` knows where one ends and the other begins. `toAppPath` falls back
 * to stripping the origin, which leaves the `/Plone` of a site served under a
 * sub-path and quietly answers "different page" on every page.
 *
 * @param content The `content` slice of the store.
 * @param pathname The path the app is on.
 * @returns The profile state, or null when this navigation did not bring one.
 */
export function expandedProfile(content: any, pathname: string): any | null {
  const component = content?.data?.['@components']?.['my-profile'];
  if (!component?.userid) {
    return null;
  }
  const at = flattenToAppURL(content?.data?.['@id'] ?? '');
  // The site root flattens to the empty string while the router calls it `/`.
  return (at || '/') === (pathname || '/') ? component : null;
}

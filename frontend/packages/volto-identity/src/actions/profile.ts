/**
 * Actions for reading a user and editing the caller's own profile.
 * @module actions/profile
 */

import {
  GET_MY_PROFILE,
  GET_USER_PROFILE,
  SET_PREFERRED_EMAIL,
} from '../constants/ActionTypes';

/**
 * Read a user, with what this add-on knows about them.
 *
 * `@users/<userid>` is Plone's own endpoint; this package's serializer adds
 * `identities`, `source` and `profile_url` to it, which is what the toolbar
 * and the profile links read. Held separately from Volto's `state.users.user`
 * on purpose: that one is fetched when the user menu opens and cleared
 * around it, and the avatar has to survive a page the menu was never opened
 * on.
 *
 * @param userid The user to read.
 */
export function getUserProfile(userid: string) {
  return {
    type: GET_USER_PROFILE,
    request: { op: 'get', path: `/@users/${userid}` },
  };
}

/**
 * Ask where the signed-in user's own Profile is, and how far along it is.
 *
 * Used for first-login routing: a user whose Profile is still `incomplete`
 * should be asked to fill it in before being sent on their way. Answers
 * usably for a user who has no Profile, so the caller does not have to know
 * whether there is one.
 */
export function getMyProfile() {
  return {
    type: GET_MY_PROFILE,
    request: { op: 'get', path: '/@my-profile' },
  };
}

/**
 * Move one of your addresses to the front of your profile's list.
 *
 * Which address stands for you is the order of that list -- the backend
 * derives `email` from it, preferring the first verified one -- so choosing is
 * a reorder rather than a field of its own. A `PATCH` on the profile is what
 * saving the edit form does, and the same permission covers both.
 *
 * The whole list is sent, not just the address, because that is what the field
 * is: sending one entry would replace the list with it.
 *
 * @param profilePath App-relative path of the profile.
 * @param addresses The addresses in their new order.
 */
export function setPreferredEmail(profilePath: string, addresses: string[]) {
  return {
    type: SET_PREFERRED_EMAIL,
    request: {
      op: 'patch',
      path: profilePath,
      data: { emails: addresses },
    },
  };
}

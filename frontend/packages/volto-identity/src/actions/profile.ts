/**
 * Actions for reading a user and editing the caller's own profile.
 * @module actions/profile
 */

import {
  CONFIRM_EMAIL,
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

/**
 * Answer the question `@my-profile` reports as `confirm_email`.
 *
 * Not a reorder by another name, which is why it is not `setPreferredEmail`:
 * the backend refuses it for a Profile nobody is asking, and for an address
 * that is not one of that Profile's verified ones. It answers with
 * `@my-profile` as it is afterwards, and the `myProfile` slice takes that in,
 * so the gate sees the Profile released without asking again.
 *
 * @param address The verified address that stands for the caller.
 */
export function confirmEmail(address: string) {
  return {
    type: CONFIRM_EMAIL,
    request: {
      op: 'post',
      path: '/@confirm-email',
      data: { email: address },
    },
  };
}

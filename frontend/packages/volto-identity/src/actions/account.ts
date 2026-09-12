/**
 * Actions for the view of one account: an administrator's, or the user's own.
 * @module actions/account
 */

import { GET_USER_ACCOUNT } from '../constants/ActionTypes';

/**
 * Read how one account gets in, and when it last did.
 *
 * `Manage users`, except when a caller asks about themselves.
 *
 * @param userid The account to read.
 * @param events How many recent audit events to include. Left out, the
 *   backend's default; it caps the number either way.
 */
export function getUserAccount(userid: string, events?: number) {
  const query = events === undefined ? '' : `?events=${events}`;
  return {
    type: GET_USER_ACCOUNT,
    request: {
      op: 'get',
      path: `/@user-account/${encodeURIComponent(userid)}${query}`,
    },
  };
}

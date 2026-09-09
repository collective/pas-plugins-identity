/**
 * Actions for the administrator's view of one account.
 * @module actions/account
 */

import { GET_USER_ACCOUNT } from '../constants/ActionTypes';

/**
 * Read how one account gets in, and when it last did.
 *
 * `Manage users`, except when a caller asks about themselves.
 *
 * @param userid The account to read.
 */
export function getUserAccount(userid: string) {
  return {
    type: GET_USER_ACCOUNT,
    request: {
      op: 'get',
      path: `/@user-account/${encodeURIComponent(userid)}`,
    },
  };
}

/**
 * Actions for the view of one account: an administrator's, or the user's own.
 * @module actions/account
 */

import { GET_USER_ACCOUNT } from '../constants/ActionTypes';
import { endpoints } from '@plone-collective/identity-core';

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
  return {
    type: GET_USER_ACCOUNT,
    request: {
      op: 'get',
      path: endpoints.userAccount(userid, events),
    },
  };
}

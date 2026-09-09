/**
 * Reducers for the administrator's view of one account.
 * @module reducers/account
 */

import { GET_USER_ACCOUNT } from '../constants/ActionTypes';
import type { UserAccount } from '../types';
import { requestReducer } from './factory';

export const userAccount = requestReducer<UserAccount | null>(
  GET_USER_ACCOUNT,
  (result) => result ?? null,
  null,
);

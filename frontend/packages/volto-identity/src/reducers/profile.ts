/**
 * Reducers for reading a user and editing the caller's own profile.
 * @module reducers/profile
 */

import {
  GET_MY_PROFILE,
  GET_USER_PROFILE,
  SET_PREFERRED_EMAIL,
} from '../constants/ActionTypes';
import type { MyProfile, UserProfile } from '../types';
import { requestReducer } from './factory';

export const userProfile = requestReducer<UserProfile | null>(
  GET_USER_PROFILE,
  (result) => result ?? null,
  null,
);

export const myProfile = requestReducer<MyProfile | null>(
  GET_MY_PROFILE,
  (result) => result ?? null,
  null,
);

// A `PATCH` on content answers 204 with no body, so there is nothing to keep:
// this reducer exists for `loading` and `error`, and the new order is read back
// through `@my-profile` once the write lands.
export const preferredEmail = requestReducer<null>(
  SET_PREFERRED_EMAIL,
  () => null,
  null,
);

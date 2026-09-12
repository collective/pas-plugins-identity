/**
 * Reducers for reading a user and editing the caller's own profile.
 * @module reducers/profile
 */

import {
  CONFIRM_EMAIL,
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
  // Confirming an address answers with `@my-profile` as it is afterwards.
  // Taken in here so the gate sees the Profile released on that answer,
  // rather than holding somebody on the confirmation page until it next asks.
  { actionType: CONFIRM_EMAIL, extract: (result) => result ?? undefined },
);

// A `PATCH` on content answers 204 with no body, so there is nothing to keep:
// this reducer exists for `loading` and `error`, and the new order is read back
// through `@my-profile` once the write lands.
export const preferredEmail = requestReducer<null>(
  SET_PREFERRED_EMAIL,
  () => null,
  null,
);

// Its own slice for `loading` and `error`. The answer is kept here as well, so
// the confirmation page can say which address it recorded after `myProfile`
// has moved on.
export const emailConfirmation = requestReducer<MyProfile | null>(
  CONFIRM_EMAIL,
  (result) => result ?? null,
  null,
);

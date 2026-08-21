/**
 * Reducers for the identity login flows.
 *
 * One factory rather than five near-identical reducers: they all track the
 * same request lifecycle and differ only in what they keep from the answer.
 * @module reducers
 */

import {
  COMPLETE_CALLBACK,
  CONFIRM_MAGIC_LINK,
  CREATE_PROVIDER,
  DELETE_PROVIDER,
  GET_MY_PROFILE,
  LIST_DRIVERS,
  LIST_IDENTITIES,
  LIST_LOGIN_PROVIDERS,
  LIST_PROVIDERS,
  SEND_MAGIC_LINK,
  START_LINKING,
  START_PROVIDER_LOGIN,
  TEST_PROVIDER,
  UNLINK_IDENTITY,
  UPDATE_PROVIDER,
} from '../constants/ActionTypes';
import type {
  AuthorizeRedirect,
  ConfiguredProvider,
  ConnectionCheck,
  Driver,
  Identity,
  LoginProvider,
  MyProfile,
  RequestState,
  TokenResponse,
} from '../types';

type Action = { type: string; result?: unknown; error?: unknown };

const initial: RequestState = { loading: false, loaded: false, error: null };

/**
 * Build a reducer tracking one request.
 *
 * @param actionType The base action type.
 * @param extract What to keep out of a successful result.
 * @param empty The value of that key before anything has loaded.
 */
function requestReducer<T>(
  actionType: string,
  extract: (result: any) => T,
  empty: T,
) {
  const initialState = { ...initial, data: empty };
  return function reducer(state = initialState, action: Action = { type: '' }) {
    switch (action.type) {
      case `${actionType}_PENDING`:
        // The previous answer is cleared here as well as on success: leaving
        // it in place makes a second attempt look like it has already
        // succeeded, which for a redirect action means navigating away with
        // last time's URL.
        return { ...initialState, loading: true };
      case `${actionType}_SUCCESS`:
        return {
          ...state,
          loading: false,
          loaded: true,
          error: null,
          data: extract(action.result),
        };
      case `${actionType}_FAIL`:
        return { ...initialState, error: action.error ?? true };
      default:
        return state;
    }
  };
}

export const loginProviders = requestReducer<LoginProvider[]>(
  LIST_LOGIN_PROVIDERS,
  (result) => result?.items ?? [],
  [],
);

export const providerLogin = requestReducer<AuthorizeRedirect | null>(
  START_PROVIDER_LOGIN,
  (result) => result ?? null,
  null,
);

export const identityCallback = requestReducer<TokenResponse | null>(
  COMPLETE_CALLBACK,
  (result) => result ?? null,
  null,
);

export const magicLinkSend = requestReducer<boolean>(
  SEND_MAGIC_LINK,
  (result) => Boolean(result?.sent),
  false,
);

export const magicLinkConfirm = requestReducer<TokenResponse | null>(
  CONFIRM_MAGIC_LINK,
  (result) => result ?? null,
  null,
);

export const identities = requestReducer<Identity[]>(
  LIST_IDENTITIES,
  (result) => result?.items ?? [],
  [],
);

export const identityLinking = requestReducer<AuthorizeRedirect | null>(
  START_LINKING,
  (result) => result ?? null,
  null,
);

export const identityUnlink = requestReducer<boolean>(
  UNLINK_IDENTITY,
  () => true,
  false,
);

export const identityDrivers = requestReducer<Driver[]>(
  LIST_DRIVERS,
  (result) => result?.items ?? [],
  [],
);

export const configuredProviders = requestReducer<ConfiguredProvider[]>(
  LIST_PROVIDERS,
  (result) => result?.items ?? [],
  [],
);

export const providerCreate = requestReducer<ConfiguredProvider | null>(
  CREATE_PROVIDER,
  (result) => result ?? null,
  null,
);

export const providerUpdate = requestReducer<boolean>(
  UPDATE_PROVIDER,
  () => true,
  false,
);

export const providerDelete = requestReducer<boolean>(
  DELETE_PROVIDER,
  () => true,
  false,
);

export const providerTest = requestReducer<ConnectionCheck | null>(
  TEST_PROVIDER,
  (result) => result ?? null,
  null,
);

export const myProfile = requestReducer<MyProfile | null>(
  GET_MY_PROFILE,
  (result) => result ?? null,
  null,
);

const reducers = {
  loginProviders,
  providerLogin,
  identityCallback,
  magicLinkSend,
  magicLinkConfirm,
  identities,
  identityLinking,
  identityUnlink,
  identityDrivers,
  configuredProviders,
  providerCreate,
  providerUpdate,
  providerDelete,
  providerTest,
  myProfile,
};

export default reducers;

/**
 * Reducers for signing in with an external provider.
 * @module reducers/login
 */

import {
  COMPLETE_CALLBACK,
  LIST_IDENTITIES,
  LIST_LOGIN_PROVIDERS,
  START_PROVIDER_LOGIN,
} from '../constants/ActionTypes';
import type { AuthorizeRedirect, LoginProvider, TokenResponse } from '../types';
import { requestReducer } from './factory';

export const loginProviders = requestReducer<LoginProvider[]>(
  LIST_LOGIN_PROVIDERS,
  (result) => result?.items ?? [],
  [],
  {
    // The identities listing can carry the same providers as an expanded
    // component, which is how the identities page loads in one request.
    actionType: LIST_IDENTITIES,
    extract: (result) => result?.['@components']?.['login-providers']?.items,
  },
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

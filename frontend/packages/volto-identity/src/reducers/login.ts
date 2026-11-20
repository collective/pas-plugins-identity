/**
 * Reducers for signing in with an external provider.
 * @module reducers/login
 */

import {
  COMPLETE_CALLBACK,
  LIST_IDENTITIES,
  LIST_LOGIN_OPTIONS,
  LIST_LOGIN_PROVIDERS,
  START_PROVIDER_LOGIN,
} from '../constants/ActionTypes';
import type {
  AuthorizeRedirect,
  LoginOption,
  LoginProvider,
  TokenResponse,
} from '../types';
import { requestReducer } from './factory';

/**
 * This add-on's options in `GET @login`.
 *
 * `@login` answers every login plugin's options, and only ours can be started
 * by this add-on: another plugin's `url` belongs to another flow. Kept here
 * rather than in each component, so nothing downstream sees a foreign entry.
 */
export const loginOptions = requestReducer<LoginOption[]>(
  LIST_LOGIN_OPTIONS,
  (result) =>
    (result?.options ?? []).filter(
      (option: { plugin?: string }) => option?.plugin === 'identity',
    ),
  [],
);

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

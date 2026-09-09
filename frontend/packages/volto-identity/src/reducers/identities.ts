/**
 * Reducers for the sign-in methods attached to the caller's account.
 * @module reducers/identities
 */

import {
  LIST_IDENTITIES,
  START_LINKING,
  UNLINK_IDENTITY,
} from '../constants/ActionTypes';
import type { AuthorizeRedirect, Identity, LoginProvider } from '../types';
import { requestReducer } from './factory';

export const identities = requestReducer<Identity[]>(
  LIST_IDENTITIES,
  (result) => result?.items ?? [],
  [],
);

/**
 * What the caller could still attach to their account.
 *
 * The backend's own answer rather than a filter applied here, and a different
 * question from `loginProviders`: that one is what the login screen offers,
 * this one is every *enabled* provider the caller has not linked. A provider
 * an operator has taken off the login page is still one an existing user may
 * attach, which is exactly what the two settings exist to distinguish.
 */
export const linkableProviders = requestReducer<LoginProvider[]>(
  LIST_IDENTITIES,
  (result) => result?.available ?? [],
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

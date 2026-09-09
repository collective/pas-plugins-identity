/**
 * Reducers for the consent screen and the caller's own grants.
 * @module reducers/consent
 */

import {
  GET_CONSENT_REQUEST,
  LIST_GRANTS,
  WITHDRAW_GRANT,
} from '../constants/ActionTypes';
import type { ConsentRequest, OAuthGrants } from '../types';
import { requestReducer } from './factory';

export const consentRequest = requestReducer<ConsentRequest | null>(
  GET_CONSENT_REQUEST,
  (result) => result ?? null,
  null,
);

export const oauthGrants = requestReducer<OAuthGrants | null>(
  LIST_GRANTS,
  (result) => result ?? null,
  null,
);

export const grantWithdraw = requestReducer<Record<string, unknown> | null>(
  WITHDRAW_GRANT,
  (result) => result ?? null,
  null,
);

/**
 * Reducers for the emailed single-use sign-in link.
 * @module reducers/magiclink
 */

import { CONFIRM_MAGIC_LINK, SEND_MAGIC_LINK } from '../constants/ActionTypes';
import type { TokenResponse } from '../types';
import { requestReducer } from './factory';

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

/**
 * Reducers for the signing key ring.
 * @module reducers/keys
 */

import { LIST_KEYS, ROTATE_KEY } from '../constants/ActionTypes';
import type { SigningKeyRing } from '../types';
import { requestReducer } from './factory';

export const signingKeys = requestReducer<SigningKeyRing | null>(
  LIST_KEYS,
  (result) => result ?? null,
  null,
);

export const keyRotate = requestReducer<SigningKeyRing | null>(
  ROTATE_KEY,
  (result) => result ?? null,
  null,
);

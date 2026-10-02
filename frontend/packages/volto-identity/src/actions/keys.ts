/**
 * Actions for the signing key ring.
 * @module actions/keys
 */

import { LIST_KEYS, ROTATE_KEY } from '../constants/ActionTypes';
import { endpoints } from '@plone-collective/identity-core';

/** Describe the signing key ring. Metadata only; never key material. */
export function listKeys() {
  return {
    type: LIST_KEYS,
    request: { op: 'get', path: endpoints.keys() },
  };
}

/**
 * Rotate the signing key.
 *
 * Previous keys stay in the ring so tokens already issued keep verifying by
 * `kid`. The ring is bounded, so rotating past that bound inside one
 * access-token lifetime does invalidate tokens still in flight.
 */
export function rotateKey() {
  return {
    type: ROTATE_KEY,
    request: { op: 'post', path: endpoints.keyRotation(), data: {} },
  };
}

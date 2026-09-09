/**
 * Actions for the providers this site lets people sign in with.
 * @module actions/providers
 */

import {
  CREATE_PROVIDER,
  DELETE_PROVIDER,
  LIST_PROVIDERS,
  TEST_PROVIDER,
  UPDATE_PROVIDER,
} from '../constants/ActionTypes';

/**
 * List the configured providers.
 */
export function listProviders() {
  return {
    type: LIST_PROVIDERS,
    request: { op: 'get', path: '/@identity-providers' },
  };
}

/**
 * Create a provider.
 *
 * @param data The provider record.
 */
export function createProvider(data: Record<string, unknown>) {
  return {
    type: CREATE_PROVIDER,
    request: { op: 'post', path: '/@identity-providers', data },
  };
}

/**
 * Update a provider in place.
 *
 * @param providerId Provider to update.
 * @param data The fields to change.
 */
export function updateProvider(
  providerId: string,
  data: Record<string, unknown>,
) {
  return {
    type: UPDATE_PROVIDER,
    request: {
      op: 'patch',
      path: `/@identity-providers/${encodeURIComponent(providerId)}`,
      data,
    },
  };
}

/**
 * Remove a provider.
 *
 * @param providerId Provider to remove.
 */
export function deleteProvider(providerId: string) {
  return {
    type: DELETE_PROVIDER,
    request: {
      op: 'del',
      path: `/@identity-providers/${encodeURIComponent(providerId)}`,
    },
  };
}

/**
 * Check that a provider can actually be reached.
 *
 * @param providerId Provider to check.
 */
export function testProvider(providerId: string) {
  return {
    type: TEST_PROVIDER,
    request: {
      op: 'post',
      path: `/@identity-providers/${encodeURIComponent(providerId)}/test-connection`,
      data: {},
    },
  };
}

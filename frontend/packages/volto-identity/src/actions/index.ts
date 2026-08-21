/**
 * Actions for the identity login flows.
 *
 * Every one of them is a plain Volto API action: the `request` key is picked
 * up by Volto's api middleware, which does the fetch and dispatches the
 * `_PENDING` / `_SUCCESS` / `_FAIL` triple.
 * @module actions
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

/**
 * List the providers this site offers.
 */
export function listLoginProviders() {
  return {
    type: LIST_LOGIN_PROVIDERS,
    request: { op: 'get', path: '/@login-providers' },
  };
}

/**
 * Start an authorization-code flow against one provider.
 *
 * Separate from the listing on purpose: this mints the state, PKCE verifier
 * and nonce, so calling it for every provider on page load would leave a pile
 * of unused attempts behind.
 *
 * @param providerId Provider to log in with.
 * @param cameFrom Where to send the user afterwards.
 */
export function startProviderLogin(providerId: string, cameFrom = '') {
  const query = cameFrom ? `?came_from=${encodeURIComponent(cameFrom)}` : '';
  return {
    type: START_PROVIDER_LOGIN,
    request: { op: 'get', path: `/@login-providers/${providerId}${query}` },
  };
}

/**
 * Hand the provider's answer back to the backend.
 *
 * @param provider Provider the code came from.
 * @param code The authorization code.
 * @param state The state the provider echoed back.
 */
export function completeCallback(
  provider: string,
  code: string,
  state: string,
) {
  return {
    type: COMPLETE_CALLBACK,
    request: {
      op: 'post',
      path: '/@identity-callback',
      data: { provider, code, state },
    },
  };
}

/**
 * Ask for a magic link.
 *
 * @param email Address to send it to.
 */
export function sendMagicLink(email: string) {
  return {
    type: SEND_MAGIC_LINK,
    request: { op: 'post', path: '/@magic-link', data: { email } },
  };
}

/**
 * Redeem a magic link.
 *
 * @param token The token from the emailed link.
 */
export function confirmMagicLink(token: string) {
  return {
    type: CONFIRM_MAGIC_LINK,
    request: {
      op: 'post',
      path: '/@magic-link-confirm',
      data: { token },
    },
  };
}

/**
 * List the identities the signed-in user owns.
 */
export function listIdentities() {
  return {
    type: LIST_IDENTITIES,
    request: { op: 'get', path: '/@identities' },
  };
}

/**
 * Start a flow that attaches another provider to the caller's account.
 *
 * @param providerId Provider to link.
 * @param cameFrom Where to send the user afterwards.
 */
export function startLinking(providerId: string, cameFrom = '') {
  return {
    type: START_LINKING,
    request: {
      op: 'post',
      path: '/@identities',
      data: { provider: providerId, came_from: cameFrom },
    },
  };
}

/**
 * Detach one identity.
 *
 * @param provider Provider id.
 * @param subject Provider-side subject.
 */
export function unlinkIdentity(provider: string, subject: string) {
  return {
    type: UNLINK_IDENTITY,
    request: {
      op: 'del',
      path: `/@identities/${encodeURIComponent(provider)}/${encodeURIComponent(subject)}`,
    },
  };
}

/**
 * List the drivers, with the schema the control-panel form renders from.
 */
export function listDrivers() {
  return {
    type: LIST_DRIVERS,
    request: { op: 'get', path: '/@identity-drivers' },
  };
}

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

/**
 * Ask where the signed-in user's own Profile is, and how far along it is.
 *
 * Used for first-login routing: a user whose Profile is still `incomplete`
 * should be asked to fill it in before being sent on their way. Answers
 * usably in a site without the `[profile]` extra, so the caller does not have
 * to know whether it is installed.
 */
export function getMyProfile() {
  return {
    type: GET_MY_PROFILE,
    request: { op: 'get', path: '/@my-profile' },
  };
}

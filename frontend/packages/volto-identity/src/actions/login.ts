/**
 * Actions for signing in with an external provider.
 * @module actions/login
 */

import {
  COMPLETE_CALLBACK,
  LIST_LOGIN_PROVIDERS,
  START_PROVIDER_LOGIN,
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

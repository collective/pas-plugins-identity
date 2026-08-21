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
  LIST_LOGIN_PROVIDERS,
  SEND_MAGIC_LINK,
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

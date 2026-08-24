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
  CREATE_CLIENT,
  CREATE_PROVIDER,
  DELETE_CLIENT,
  DELETE_PROVIDER,
  GET_MY_PROFILE,
  LIST_CLIENTS,
  LIST_DRIVERS,
  LIST_KEYS,
  LIST_IDENTITIES,
  LIST_LOGIN_PROVIDERS,
  LIST_PROVIDERS,
  ROTATE_CLIENT_SECRET,
  ROTATE_KEY,
  SEND_MAGIC_LINK,
  START_LINKING,
  START_PROVIDER_LOGIN,
  TEST_PROVIDER,
  UNLINK_IDENTITY,
  UPDATE_CLIENT,
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
 *
 * The page showing them also offers what is *not* linked yet, which is the
 * same listing `@login-providers` serves. Asking for it as a component here
 * answers the whole screen in one request instead of two.
 *
 * @param withProviders Whether to expand the login providers alongside.
 */
export function listIdentities(withProviders = false) {
  const query = withProviders ? '?expand=login-providers' : '';
  return {
    type: LIST_IDENTITIES,
    request: { op: 'get', path: `/@identities${query}` },
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

/** Base path of the OAuth client registry. */
const CLIENTS = '/@identity-clients';

/** Base path of the signing key ring. */
const KEYS = '/@identity-keys';

/**
 * List the OAuth clients registered against this site.
 *
 * The other direction from `listProviders`: those are who this site lets
 * people log in *with*, these are who may log in *to* it.
 */
export function listClients() {
  return {
    type: LIST_CLIENTS,
    request: { op: 'get', path: CLIENTS },
  };
}

/**
 * Register an OAuth client.
 *
 * The answer carries the client secret, and it is the only time it exists:
 * the server stores a hash and cannot read it back. Whatever handles this
 * result has to put it in front of the operator immediately.
 *
 * @param data The registration.
 */
export function createClient(data: Record<string, unknown>) {
  return {
    type: CREATE_CLIENT,
    request: { op: 'post', path: CLIENTS, data },
  };
}

/**
 * Amend a client registration.
 *
 * `client_id` and `auth_method` are not editable and the backend refuses
 * them, along with any field it does not know: silently dropping one is how
 * somebody comes to believe they changed something they did not.
 *
 * @param clientId The client to amend.
 * @param data The fields to change.
 */
export function updateClient(clientId: string, data: Record<string, unknown>) {
  return {
    type: UPDATE_CLIENT,
    request: {
      op: 'patch',
      path: `${CLIENTS}/${encodeURIComponent(clientId)}`,
      data,
    },
  };
}

/**
 * Unregister a client.
 *
 * Also a revocation: access tokens carry the client id as their audience and
 * it is checked against the registry on every request, so this stops its
 * tokens working at once.
 *
 * @param clientId The client to remove.
 */
export function deleteClient(clientId: string) {
  return {
    type: DELETE_CLIENT,
    request: { op: 'del', path: `${CLIENTS}/${encodeURIComponent(clientId)}` },
  };
}

/**
 * Mint a client a fresh secret, discarding the old one.
 *
 * As with registration the answer carries the only copy.
 *
 * @param clientId The client to rotate.
 */
export function rotateClientSecret(clientId: string) {
  return {
    type: ROTATE_CLIENT_SECRET,
    request: {
      op: 'post',
      path: `${CLIENTS}/${encodeURIComponent(clientId)}/rotate-secret`,
      data: {},
    },
  };
}

/** Describe the signing key ring. Metadata only; never key material. */
export function listKeys() {
  return {
    type: LIST_KEYS,
    request: { op: 'get', path: KEYS },
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
    request: { op: 'post', path: `${KEYS}/rotate`, data: {} },
  };
}

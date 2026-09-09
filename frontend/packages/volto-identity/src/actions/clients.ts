/**
 * Actions for the OAuth clients registered against this site.
 *
 * The other direction from `actions/providers`: those are who this site lets
 * people log in *with*, these are who may log in *to* it.
 * @module actions/clients
 */

import {
  CREATE_CLIENT,
  DELETE_CLIENT,
  LIST_CLIENTS,
  ROTATE_CLIENT_SECRET,
  UPDATE_CLIENT,
} from '../constants/ActionTypes';

/** Base path of the OAuth client registry. */
const CLIENTS = '/@identity-clients';

/**
 * List the OAuth clients registered against this site.
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

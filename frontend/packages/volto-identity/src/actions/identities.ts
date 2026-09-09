/**
 * Actions for the sign-in methods attached to the caller's account.
 * @module actions/identities
 */

import {
  LIST_IDENTITIES,
  START_LINKING,
  UNLINK_IDENTITY,
} from '../constants/ActionTypes';

/**
 * List the identities the signed-in user owns.
 *
 * The answer also carries `available`: every *enabled* provider the caller
 * has not linked yet. That is a different question from what the login screen
 * offers -- a provider taken off the login page is still one an existing user
 * may attach -- so it is the endpoint's own answer rather than the expanded
 * `login-providers` listing, which remains available for a caller that wants
 * the login screen's view of things.
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
 * Answers one of two shapes. A redirect provider gives back an
 * `authorize_url` to follow; the email provider gives back `sent`, because
 * its flow continues in a mailbox rather than in this tab.
 *
 * @param providerId Provider to link.
 * @param cameFrom Where to send the user afterwards.
 * @param email Address to confirm, for the email provider only.
 */
export function startLinking(providerId: string, cameFrom = '', email = '') {
  return {
    type: START_LINKING,
    request: {
      op: 'post',
      path: '/@identities',
      // Sent only when there is one: the backend requires an address for the
      // email provider and takes none for any other.
      data: email
        ? { provider: providerId, came_from: cameFrom, email }
        : { provider: providerId, came_from: cameFrom },
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

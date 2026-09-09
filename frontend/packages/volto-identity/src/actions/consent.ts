/**
 * Actions for the consent screen and the caller's own grants.
 * @module actions/consent
 */

import {
  GET_CONSENT_REQUEST,
  LIST_GRANTS,
  WITHDRAW_GRANT,
} from '../constants/ActionTypes';

/** Base path of the caller's own OAuth grants. */
const GRANTS = '/@oauth-grants';

/**
 * Describe the authorization request the browser arrived with.
 *
 * Read-only, and deliberately so: this records no consent and issues no
 * code. The answer goes back to the authorization endpoint, which decides
 * again from scratch -- a client disabled between the question and the
 * answer is refused on the way out as surely as on the way in.
 *
 * @param search The query string the consent route was reached with,
 *   including its leading `?`. Passed straight through rather than rebuilt
 *   from parsed parameters: an authorization request is compared byte for
 *   byte further down the flow, and a round trip through a parser is a
 *   chance to change it.
 */
export function getConsentRequest(search: string) {
  return {
    type: GET_CONSENT_REQUEST,
    request: { op: 'get', path: `/@oauth-consent${search}` },
  };
}

/**
 * List the applications the caller has authorized.
 *
 * The counterpart of `listIdentities`: that answers which providers they
 * sign in with, this which applications they signed in to.
 */
export function listGrants() {
  return {
    type: LIST_GRANTS,
    request: { op: 'get', path: GRANTS },
  };
}

/**
 * Withdraw the caller's agreement with one client.
 *
 * The backend forgets the agreement *and* revokes that client's refresh
 * tokens for this user, because forgetting alone would only decide the next
 * authorization. It answers with how many sessions ended and how long an
 * access token already minted may still work, neither of which this can
 * know on its own.
 *
 * @param clientId The client to withdraw from.
 */
export function withdrawGrant(clientId: string) {
  return {
    type: WITHDRAW_GRANT,
    request: {
      op: 'del',
      path: `${GRANTS}/${encodeURIComponent(clientId)}`,
    },
  };
}

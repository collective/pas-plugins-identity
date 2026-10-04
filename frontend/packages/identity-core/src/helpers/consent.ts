/**
 * Answering an authorization request.
 *
 * The consent screen does not answer over the API. `@@oauth-authorize`
 * answers a decision with a redirect to the relying party, and it is the
 * browser that has to arrive there, so the answer is a navigation back to
 * the authorization endpoint carrying it.
 * @module helpers/consent
 */
import type { ConsentRequest } from '../types';

/**
 * Build the URL that carries an answer back to the authorization endpoint.
 *
 * The request travels back exactly as it arrived. `consent=allow` is the only
 * value that means yes -- anything else is a refusal, because consent is the
 * thing that has to be given explicitly.
 *
 * @param request What the server said about this authorization request.
 * @param allow Whether the user agreed.
 * @returns The absolute URL to send the browser to.
 */
export function answerUrl(request: ConsentRequest, allow: boolean): string {
  const params = new URLSearchParams(request.params);
  params.set('consent', allow ? 'allow' : 'deny');
  // plone.protect's token. The endpoint refuses an answer without a valid
  // one: a forged consent request is an attempt to authorize a client on
  // somebody else's behalf.
  params.set('_authenticator', request.authenticator);
  return `${request.authorize_url}?${params.toString()}`;
}

/**
 * The authorization server's endpoints, served at Aurora's address.
 *
 * `@@oauth-authorize` and its siblings are browser views on the backend,
 * not REST services. In front of Volto, a reverse proxy sends them to the
 * backend by a rule written for them (see `concepts/federation`). Aurora
 * serves them itself instead, by passing each request on, for two reasons:
 *
 * - **The issuer is the site's public address**, which is Aurora's, so a
 *   relying party asks Aurora for the discovery document, the keys, the
 *   token and the user's claims. Passing them on works without that rule.
 * - **The authorization endpoint needs to know who the browser is.** The
 *   backend recognises a signed-in user there by a bearer token, or Volto's
 *   `auth_token` cookie. Aurora keeps its session in a cookie of its own the
 *   backend cannot read, so Aurora sends the session's token as a bearer
 *   token -- on that endpoint alone, because it is the only one the user's
 *   browser reaches with a session that matters.
 *
 * Everything else about a request is passed on as it came, and the answer
 * comes back as the backend gave it: a redirect to the relying party, to the
 * consent screen or to the login page, which name Aurora's address because
 * the backend is asked through the virtual-host URL.
 * @module lib/oauth
 */
import config from '@plone/registry';
import { getAuthFromRequest } from '@plone/react-router';

import { backendUrl } from './backend';
import { AUTHORIZE_PATH } from './paths';

/** Request headers worth passing on; the browser's cookies are Aurora's. */
const REQUEST_HEADERS = ['accept', 'authorization', 'content-type', 'dpop'];

/** Answer headers worth passing back. */
const ANSWER_HEADERS = [
  'cache-control',
  'content-type',
  'location',
  'pragma',
  'www-authenticate',
];

/**
 * Pass a request to one of the authorization server's endpoints.
 *
 * @param request The request Aurora received.
 * @returns The backend's answer, as the browser or relying party gets it.
 */
export async function passOn(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const headers = new Headers();
  for (const name of REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value) {
      headers.set(name, value);
    }
  }
  if (url.pathname === AUTHORIZE_PATH) {
    // The user, as the session knows them, and nothing the browser sent: a
    // cached Basic credential for this host must not stand in for them.
    headers.delete('authorization');
    const token = await getAuthFromRequest(request);
    if (token) {
      headers.set('authorization', `Bearer ${token}`);
    }
  }
  const body =
    request.method === 'GET' || request.method === 'HEAD'
      ? undefined
      : await request.arrayBuffer();

  let answer: Response;
  try {
    answer = await fetch(
      backendUrl(
        config.settings.apiPath,
        request.url,
        `${url.pathname}${url.search}`,
        { api: false },
      ),
      { method: request.method, headers, body, redirect: 'manual' },
    );
  } catch {
    return new Response('The authorization server could not be reached.', {
      status: 502,
    });
  }

  const passed = new Headers();
  for (const name of ANSWER_HEADERS) {
    const value = answer.headers.get(name);
    if (value) {
      passed.set(name, value);
    }
  }
  return new Response(answer.body, {
    status: answer.status,
    statusText: answer.statusText,
    headers: passed,
  });
}

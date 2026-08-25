import { describe, expect, it } from 'vitest';

import { answerUrl } from './Consent';
import type { ConsentRequest } from '../../types';

const REQUEST: ConsentRequest = {
  '@id': 'http://id.example.org/@oauth-consent',
  client: { id: 'app', title: 'Example App' },
  user: { id: 'alice', label: 'Alice Liddell' },
  scopes: [{ id: 'openid', claims: [] }],
  authorize_url: 'http://id.example.org/@@oauth-authorize',
  params: {
    response_type: 'code',
    client_id: 'app',
    redirect_uri: 'https://app.example.org/cb',
    scope: 'openid profile',
    state: 'xyz',
  },
  authenticator: 'tok3n',
};

/**
 * The answer's parameters.
 *
 * @param allow Whether the user agreed.
 * @returns The query parameters of the URL the browser would be sent to.
 */
function answer(allow: boolean) {
  const url = new URL(answerUrl(REQUEST, allow));
  return { url, params: Object.fromEntries(url.searchParams.entries()) };
}

describe('answerUrl', () => {
  it('sends the answer to the endpoint that decides', () => {
    // Not to the relying party. Every check runs again there, so a client
    // disabled between the question and the answer is refused on the way out.
    expect(answer(true).url.origin + answer(true).url.pathname).toBe(
      'http://id.example.org/@@oauth-authorize',
    );
  });

  it('hands the request back unchanged', () => {
    const { params } = answer(true);

    for (const [name, value] of Object.entries(REQUEST.params)) {
      expect(params[name]).toBe(value);
    }
  });

  it('spells agreement out', () => {
    // `allow` is the only value that means yes, because consent is the thing
    // that has to be given explicitly.
    expect(answer(true).params.consent).toBe('allow');
  });

  it('sends a refusal rather than nothing', () => {
    // Silence would leave the relying party waiting for a browser that is
    // never coming back.
    expect(answer(false).params.consent).toBe('deny');
  });

  it('carries the token the answer is checked against', () => {
    // A forged consent request is an attempt to authorize a client on
    // somebody else's behalf.
    expect(answer(true).params._authenticator).toBe('tok3n');
  });

  it('adds nothing the request did not carry', () => {
    const { params } = answer(true);

    expect(Object.keys(params).sort()).toEqual(
      [...Object.keys(REQUEST.params), 'consent', '_authenticator'].sort(),
    );
  });
});

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import config from '@plone/registry';
import { setAuthOnResponse } from '@plone/react-router';

import { passOn } from './oauth';

/**
 * The cookie Aurora keeps a session in, for a token.
 *
 * @param token The session's token.
 * @returns A `Cookie` header carrying it.
 */
async function sessionCookie(token: string): Promise<string> {
  const answer = await setAuthOnResponse(new Response(), token);
  return (answer.headers.get('Set-Cookie') ?? '').split(';')[0];
}

/**
 * Stand in for the backend, answering every request with one response.
 *
 * @param answer What the backend answers.
 * @returns The stand-in, to read the requests off.
 */
function backend(answer: Response) {
  const fetch = vi.fn(async (..._args: unknown[]) => answer);
  vi.stubGlobal('fetch', fetch);
  return fetch;
}

/**
 * What the backend was asked.
 *
 * @param fetch The stand-in.
 * @returns The URL and the request's options.
 */
function asked(fetch: ReturnType<typeof backend>) {
  const [url, init] = fetch.mock.calls[0] as [string, RequestInit];
  return { url, headers: new Headers(init.headers), init };
}

describe('passOn', () => {
  beforeEach(() => {
    config.settings.apiPath = 'http://localhost:8080/Plone';
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('asks the browser view, as the public site, without the REST traverser', async () => {
    const fetch = backend(new Response('{}'));

    await passOn(
      new Request('http://localhost:3000/.well-known/openid-configuration'),
    );

    expect(asked(fetch).url).toBe(
      'http://localhost:8080/VirtualHostBase/http/localhost:3000/Plone/VirtualHostRoot/.well-known/openid-configuration',
    );
  });

  it('sends the session to the authorization endpoint as a bearer token', async () => {
    const fetch = backend(new Response(null, { status: 302 }));

    await passOn(
      new Request('http://localhost:3000/@@oauth-authorize?client_id=app', {
        headers: {
          Cookie: await sessionCookie('the-token'),
          Authorization: 'Basic c29tZW9uZTplbHNl',
        },
      }),
    );

    const { headers } = asked(fetch);
    expect(headers.get('authorization')).toBe('Bearer the-token');
    // Aurora's cookies are not the backend's.
    expect(headers.get('cookie')).toBeNull();
  });

  it("passes a relying party's own credentials to the token endpoint", async () => {
    const fetch = backend(new Response('{}'));

    await passOn(
      new Request('http://localhost:3000/@@oauth-token', {
        method: 'POST',
        headers: {
          Authorization: 'Basic YXBwOnNlY3JldA==',
          Cookie: await sessionCookie('the-token'),
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: 'grant_type=authorization_code&code=c',
      }),
    );

    const { headers, init } = asked(fetch);
    expect(headers.get('authorization')).toBe('Basic YXBwOnNlY3JldA==');
    expect(init.method).toBe('POST');
    expect(new TextDecoder().decode(init.body as ArrayBuffer)).toBe(
      'grant_type=authorization_code&code=c',
    );
  });

  it("hands back the backend's redirect, and nothing it should not", async () => {
    backend(
      new Response(null, {
        status: 302,
        headers: {
          Location: 'http://localhost:3000/oauth-consent?client_id=app',
          'Set-Cookie': '__ac=secret; Path=/',
        },
      }),
    );

    const answer = await passOn(
      new Request('http://localhost:3000/@@oauth-authorize?client_id=app'),
    );

    expect(answer.status).toBe(302);
    expect(answer.headers.get('location')).toBe(
      'http://localhost:3000/oauth-consent?client_id=app',
    );
    expect(answer.headers.get('set-cookie')).toBeNull();
  });
});

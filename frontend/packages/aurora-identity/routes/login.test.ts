import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import config from '@plone/registry';

import { action } from './login';

/**
 * Sign in with a password, wanting to go on somewhere.
 *
 * @param cameFrom Where the visitor was going.
 * @returns The action's answer.
 */
async function signIn(cameFrom: string): Promise<Response> {
  const body = new URLSearchParams({
    intent: 'password',
    login: 'alice',
    password: 'secret',
    came_from: cameFrom,
  });
  return (await action({
    request: new Request('http://localhost:3000/login', {
      method: 'POST',
      body,
    }),
    params: {},
    context: {},
  } as unknown as Parameters<typeof action>[0])) as Response;
}

describe('signing in with a password', () => {
  beforeEach(() => {
    config.settings.apiPath = 'http://localhost:8080/Plone';
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => Response.json({ token: 'not.a.jwt' })),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('goes on to a page of this application through the router', async () => {
    const answer = await signIn('/news');

    expect(answer.headers.get('Location')).toBe('/news');
    expect(answer.headers.get('X-Remix-Reload-Document')).toBeNull();
  });

  it('loads a backend view the sign-in was for, rather than routing to it', async () => {
    const answer = await signIn('/@@oauth-authorize?client_id=app');

    expect(answer.headers.get('Location')).toBe(
      '/@@oauth-authorize?client_id=app',
    );
    expect(answer.headers.get('X-Remix-Reload-Document')).toBe('true');
  });
});

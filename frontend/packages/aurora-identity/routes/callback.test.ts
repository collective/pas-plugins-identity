import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import config from '@plone/registry';

import { loader } from './callback';

/**
 * Answer every backend call with one JSON body.
 *
 * @param body What the backend answers.
 */
function backendAnswers(body: object) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => Response.json(body, { status: 200 })),
  );
}

/**
 * The provider's redirect back to the callback.
 *
 * @returns The loader's arguments.
 */
function providerRedirect() {
  return {
    request: new Request(
      'http://localhost:3000/login-identity?provider=dex&code=c&state=s',
    ),
    params: {},
    context: {},
  } as unknown as Parameters<typeof loader>[0];
}

describe('the callback', () => {
  beforeEach(() => {
    config.settings.apiPath = 'http://localhost:8080/Plone';
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('goes back to the sign-in methods once an identity is linked', async () => {
    // The backend's answer to a link names no `came_from`.
    backendAnswers({ linked: { provider: 'dex', subject: 'subject-1' } });

    const answer = (await loader(providerRedirect())) as Response;

    expect(answer.status).toBe(302);
    expect(answer.headers.get('Location')).toBe('/identities');
  });

  it('goes back to where a sign-in started from', async () => {
    backendAnswers({ token: 'not.a.jwt', came_from: '/news' });

    const answer = (await loader(providerRedirect())) as Response;

    expect(answer.status).toBe(302);
    expect(answer.headers.get('Location')).toBe('/news');
  });
});

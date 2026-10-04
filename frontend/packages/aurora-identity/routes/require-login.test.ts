import { describe, expect, it } from 'vitest';

import { loader } from './require-login';

/**
 * Run the loader for a request.
 *
 * @param url The URL asked for.
 * @returns The loader's answer.
 */
async function answer(url: string): Promise<Response> {
  return (await loader({
    request: new Request(url),
    params: {},
    context: {},
  } as unknown as Parameters<typeof loader>[0])) as Response;
}

describe('require_login', () => {
  it("sends Plone's challenge to Aurora's login page, keeping where it was going", async () => {
    const response = await answer(
      'http://localhost:3000/acl_users/credentials_cookie_auth/require_login' +
        '?came_from=/%40%40oauth-authorize%3Fclient_id%3Dapp',
    );

    expect(response.status).toBe(302);
    expect(response.headers.get('Location')).toBe(
      '/login?came_from=%2F%40%40oauth-authorize%3Fclient_id%3Dapp',
    );
  });

  it('sends a bare challenge to the login page alone', async () => {
    const response = await answer(
      'http://localhost:3000/acl_users/credentials_cookie_auth/require_login',
    );

    expect(response.headers.get('Location')).toBe('/login');
  });
});

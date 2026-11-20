import { afterEach, describe, expect, it } from 'vitest';

import {
  afterSignIn,
  clearHandoff,
  HANDOFF_COOKIE,
  HANDOFF_PATH,
  loopbackUrl,
  pendingHandoff,
  readHandoffRequest,
  storeHandoff,
} from './handoff';

const LOOPBACK = 'http://127.0.0.1:8765/callback';

/**
 * The login page's query string for a handoff.
 *
 * @param returnUrl The `return_url`.
 * @param state The `state`, left out when undefined.
 * @returns The query string.
 */
function search(returnUrl: string, state?: string): string {
  const params = new URLSearchParams({ return_url: returnUrl });
  if (state !== undefined) {
    params.set('state', state);
  }
  return `?${params.toString()}`;
}

describe('loopbackUrl', () => {
  it.each([
    ['http://127.0.0.1:8765/callback', 'http://127.0.0.1:8765/callback'],
    ['http://[::1]:8765/', 'http://[::1]:8765/'],
    ['http://localhost:8765/cb?x=1', 'http://localhost:8765/cb?x=1'],
    ['HTTP://LOCALHOST:8765/', 'http://localhost:8765/'],
  ])('accepts %s', (value, expected) => {
    expect(loopbackUrl(value)).toBe(expected);
  });

  it.each([
    // Not a listener on this computer.
    ['another host', 'http://evil.example:8765/'],
    ['a name ending in localhost', 'http://localhost.evil.example:8765/'],
    ['https', 'https://127.0.0.1:8765/'],
    // Every listener has a port it chose; without one this is port 80.
    ['no port', 'http://127.0.0.1/'],
    ['credentials', 'http://user:pw@127.0.0.1:8765/'],
    ['a relative path', '/callback'],
    ['a protocol-relative URL', '//127.0.0.1:8765/'],
    // Built, because the linter refuses a script URL written out.
    ['javascript', ['javascript', 'alert(1)'].join(':')],
    ['not a string', 42],
    ['nothing', undefined],
  ])('refuses %s', (_label, value) => {
    expect(loopbackUrl(value)).toBeNull();
  });
});

describe('readHandoffRequest', () => {
  it('reads a loopback return_url with its state', () => {
    expect(readHandoffRequest(search(LOOPBACK, 'xyz'))).toEqual({
      returnUrl: LOOPBACK,
      state: 'xyz',
    });
  });

  it('refuses a loopback return_url without a state', () => {
    expect(readHandoffRequest(search(LOOPBACK))).toBe('refused');
  });

  it('refuses an empty state', () => {
    expect(readHandoffRequest(search(LOOPBACK, ''))).toBe('refused');
  });

  it('refuses two states', () => {
    // Which one the client expects back is a guess.
    expect(readHandoffRequest(`${search(LOOPBACK, 'a')}&state=b`)).toBe(
      'refused',
    );
  });

  it('refuses two return_urls', () => {
    const query = `${search(LOOPBACK, 'xyz')}&return_url=${encodeURIComponent(
      'http://127.0.0.1:9999/',
    )}`;

    expect(readHandoffRequest(query)).toBe('refused');
  });

  it.each([
    ['a relative return_url', search('/news', 'xyz')],
    ['another host', search('http://evil.example:8765/', 'xyz')],
    ['no return_url', '?came_from=%2Fnews'],
    ['nothing', ''],
  ])('is not a handoff for %s', (_label, query) => {
    expect(readHandoffRequest(query)).toBeNull();
  });
});

describe('the pending request', () => {
  afterEach(() => {
    clearHandoff();
  });

  it('survives until the consent page', () => {
    storeHandoff({ returnUrl: LOOPBACK, state: 'xyz' });

    expect(pendingHandoff()).toEqual({ returnUrl: LOOPBACK, state: 'xyz' });
  });

  it('is gone once cleared', () => {
    storeHandoff({ returnUrl: LOOPBACK, state: 'xyz' });

    clearHandoff();

    expect(pendingHandoff()).toBeNull();
  });

  it('is not there to begin with', () => {
    expect(pendingHandoff()).toBeNull();
  });

  it('is checked again when read', () => {
    // A cookie is input. One that names somewhere else is not a request.
    const forged = encodeURIComponent(
      JSON.stringify({ returnUrl: 'http://evil.example:8765/', state: 'x' }),
    );
    document.cookie = `${HANDOFF_COOKIE}=${forged}; Path=/`;

    expect(pendingHandoff()).toBeNull();
  });

  it('ignores a cookie that is not JSON', () => {
    document.cookie = `${HANDOFF_COOKIE}=not-json; Path=/`;

    expect(pendingHandoff()).toBeNull();
  });

  it('needs a state', () => {
    const value = encodeURIComponent(JSON.stringify({ returnUrl: LOOPBACK }));
    document.cookie = `${HANDOFF_COOKIE}=${value}; Path=/`;

    expect(pendingHandoff()).toBeNull();
  });
});

describe('afterSignIn', () => {
  afterEach(() => {
    clearHandoff();
  });

  it('goes to the consent page while a handoff is pending', () => {
    storeHandoff({ returnUrl: LOOPBACK, state: 'xyz' });

    expect(afterSignIn('/news')).toBe(HANDOFF_PATH);
  });

  it('goes where the flow was going otherwise', () => {
    expect(afterSignIn('/news')).toBe('/news');
  });
});

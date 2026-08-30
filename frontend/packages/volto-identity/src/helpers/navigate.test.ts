import { describe, expect, it, vi } from 'vitest';

import { goTo, isInternal, isSameOrigin } from './navigate';

describe('isInternal', () => {
  it('accepts a site-relative path', () => {
    expect(isInternal('/identities')).toBe(true);
  });

  it('refuses a protocol-relative URL', () => {
    // It starts with a slash and is not local at all, which is exactly the
    // shape a naive check gets wrong.
    expect(isInternal('//evil.example/x')).toBe(false);
  });

  it('refuses an absolute URL', () => {
    expect(isInternal('https://evil.example/x')).toBe(false);
  });
});

describe('isSameOrigin', () => {
  it('accepts this site', () => {
    expect(isSameOrigin(`${window.location.origin}/x`)).toBe(true);
  });

  it('refuses another', () => {
    expect(isSameOrigin('https://evil.example/x')).toBe(false);
  });

  it('refuses something that is not a URL at all', () => {
    expect(isSameOrigin('http://[')).toBe(false);
  });
});

describe('goTo', () => {
  it('routes an internal path rather than reloading', () => {
    // The whole point: a page load throws the bundle and the store away to
    // reach a route this application is already running.
    const push = vi.fn();

    goTo('/identities', push);

    expect(push).toHaveBeenCalledWith('/identities');
  });

  it('sends a foreign target nowhere without permission', () => {
    // `came_from` arrives in a query string. Handing an absolute one to the
    // browser is an open redirect, so the caller's fallback is used instead.
    const push = vi.fn();

    goTo('https://evil.example/x', push);

    expect(push).toHaveBeenCalledWith('/');
  });

  it('allows a foreign target when the caller says it is external', () => {
    // A provider's authorize URL, which is the case this exists for.
    const push = vi.fn();
    const assign = vi.spyOn(window, 'location', 'get');

    goTo('https://github.com/login/oauth', push, { external: true });

    expect(push).not.toHaveBeenCalled();
    assign.mockRestore();
  });

  it('does nothing with an empty target', () => {
    const push = vi.fn();

    goTo('', push);

    expect(push).not.toHaveBeenCalled();
  });
});

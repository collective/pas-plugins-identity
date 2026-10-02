import { describe, expect, it, vi } from 'vitest';

import { goTo, isBackendView, isInternal, isSameOrigin } from './navigate';

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

describe('isBackendView', () => {
  it('recognises a view at the root', () => {
    expect(isBackendView('/@@oauth-authorize?response_type=code')).toBe(true);
  });

  it('recognises a view traversed to further down', () => {
    // Per segment rather than by prefix: a view can hang off any object.
    expect(isBackendView('/profiles/jane/@@download')).toBe(true);
  });

  it('recognises a traversal namespace', () => {
    expect(isBackendView('/++api++/@profile')).toBe(true);
    expect(isBackendView('/++resource++plone-logo.svg')).toBe(true);
  });

  it('recognises the user folder', () => {
    expect(
      isBackendView('/acl_users/credentials_cookie_auth/require_login'),
    ).toBe(true);
  });

  it('leaves an ordinary route alone', () => {
    expect(isBackendView('/identities')).toBe(false);
    expect(isBackendView('/profiles/jane/edit')).toBe(false);
  });

  it('is not fooled by a query string mentioning one', () => {
    // The decision is about where the browser is going, not about what it
    // carries: this target is the login route and the router owns it.
    expect(isBackendView('/login?came_from=%2F%40%40oauth-authorize')).toBe(
      false,
    );
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

  it('does not route a site-relative backend view', () => {
    // The bug this predicate exists for. Plone's `require_login` hands
    // `came_from` back as `/@@oauth-authorize?…`, the router took it because
    // it starts with a slash, and Volto asked plone.restapi for the content
    // at that path -- dropping the authorization request's query string,
    // getting a 400, and rendering its own 404 at exactly that URL.
    const push = vi.fn();

    goTo('/@@oauth-authorize?response_type=code&client_id=demo-rp', push);

    expect(push).not.toHaveBeenCalled();
  });

  it('does not route a backend view given as an absolute URL', () => {
    // The shape `handedOverReturn` produces: the backend hands the paused
    // authorization request over as a full URL on this origin.
    const push = vi.fn();

    goTo(`${window.location.origin}/@@oauth-authorize?x=1`, push);

    expect(push).not.toHaveBeenCalled();
  });

  it('does nothing with an empty target', () => {
    const push = vi.fn();

    goTo('', push);

    expect(push).not.toHaveBeenCalled();
  });
});

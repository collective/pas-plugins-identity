import { describe, expect, it } from 'vitest';

import { editPath, gateTarget, goTo, handedOverReturn } from './profileGate';
import type { MyProfile } from '../types';

const PROFILE_URL = 'http://backend:8080/Plone/identity-profiles/alice';

function profile(overrides: Partial<MyProfile> = {}): MyProfile {
  return {
    '@id': 'http://backend:8080/Plone/@my-profile',
    userid: 'alice',
    profile: PROFILE_URL,
    review_state: 'incomplete',
    ...overrides,
  };
}

describe('editPath', () => {
  it('is the profile path with /edit on it', () => {
    expect(editPath(PROFILE_URL, 'http://backend:8080/Plone')).toBe(
      '/identity-profiles/alice/edit',
    );
  });
});

describe('gateTarget', () => {
  const api = 'http://backend:8080/Plone';

  it('sends an incomplete profile to its edit form', () => {
    expect(gateTarget(profile(), '/news', api)).toBe(
      '/identity-profiles/alice/edit',
    );
  });

  it('lets a complete profile through', () => {
    expect(
      gateTarget(profile({ review_state: 'complete' }), '/news', api),
    ).toBe(null);
  });

  it('lets a deactivated profile through', () => {
    // Being deactivated is not something the user can fix by filling a form
    // in, and holding them on one would be a loop with no exit at all.
    expect(
      gateTarget(profile({ review_state: 'deactivated' }), '/news', api),
    ).toBe(null);
  });

  it('lets a user with no profile through', () => {
    expect(gateTarget(profile({ profile: null }), '/news', api)).toBe(null);
  });

  it('lets a site without the extra through', () => {
    expect(
      gateTarget(profile({ profile: null, review_state: null }), '/news', api),
    ).toBe(null);
  });

  it('does nothing before the answer has arrived', () => {
    expect(gateTarget(null, '/news', api)).toBe(null);
    expect(gateTarget(undefined, '/news', api)).toBe(null);
  });

  it('does not gate the edit form it redirects to', () => {
    // The loop this whole function exists to avoid.
    expect(gateTarget(profile(), '/identity-profiles/alice/edit', api)).toBe(
      null,
    );
  });

  it('does not gate the profile itself', () => {
    expect(gateTarget(profile(), '/identity-profiles/alice', api)).toBe(null);
  });

  it('does not gate anything beneath the profile', () => {
    // The edit form loads widgets and vocabularies against paths under it,
    // and saving bounces the user to the profile's own view.
    expect(
      gateTarget(profile(), '/identity-profiles/alice/@@images/image', api),
    ).toBe(null);
  });

  it('does not gate another user profile whose path merely starts the same', () => {
    // `/identity-profiles/alice2` starts with `/identity-profiles/alice`, and
    // a naive prefix test would let somebody sit on a stranger's profile
    // instead of filling in their own.
    expect(gateTarget(profile(), '/identity-profiles/alice2', api)).toBe(
      '/identity-profiles/alice/edit',
    );
  });

  it.each([
    '/login',
    '/login-identity',
    '/logout',
    '/first-login',
    '/oauth-consent',
  ])('does not gate %s', (path) => {
    expect(gateTarget(profile(), path, api)).toBe(null);
  });

  it('does not gate a route beneath an exempt one', () => {
    expect(gateTarget(profile(), '/first-login?return_url=/news', api)).toBe(
      '/identity-profiles/alice/edit',
    );
    expect(gateTarget(profile(), '/logout/anything', api)).toBe(null);
  });

  it('treats an empty path as the front page', () => {
    expect(gateTarget(profile(), '', api)).toBe(
      '/identity-profiles/alice/edit',
    );
  });
});

describe('handedOverReturn', () => {
  // The backend's authorization endpoint pauses its request at the profile
  // form and hands the request to resume over in the query string. Honouring
  // it is a real navigation, so an unchecked value here is an open redirect:
  // a link to somebody's profile carrying a `return_url` would bounce a
  // signed-in user anywhere.

  it('takes a site-relative path', () => {
    expect(
      handedOverReturn('?identity_resume=%2F%40%40oauth-authorize%3Fx%3D1'),
    ).toBe('/@@oauth-authorize?x=1');
  });

  it('is nothing when there is none', () => {
    expect(handedOverReturn('')).toBe(null);
    expect(handedOverReturn('?other=1')).toBe(null);
    // Volto's own parameter is not ours, and taking it would fight the
    // edit form for the same navigation.
    expect(handedOverReturn('?return_url=%2Fnews')).toBe(null);
  });

  it('refuses a protocol-relative target', () => {
    // "//evil.example" is not site-relative, however much it looks it.
    expect(handedOverReturn('?identity_resume=%2F%2Fevil.example%2Fx')).toBe(
      null,
    );
  });

  it('refuses another origin', () => {
    expect(
      handedOverReturn('?identity_resume=https%3A%2F%2Fevil.example%2Fx'),
    ).toBe(null);
  });
});

describe('goTo', () => {
  it('lets the router handle a path it owns', () => {
    const seen: string[] = [];

    goTo('/news', (path) => seen.push(path));

    expect(seen).toEqual(['/news']);
  });

  it('does not hand an absolute URL to the router', () => {
    // `@@oauth-authorize` is a backend view, not a route. Asking the router
    // for it renders a Volto page that does not exist, which is how a
    // resumed sign-in turns into a 404.
    const seen: string[] = [];

    goTo('http://id.example.org/@@oauth-authorize?x=1', (path) =>
      seen.push(path),
    );

    expect(seen).toEqual([]);
  });
});

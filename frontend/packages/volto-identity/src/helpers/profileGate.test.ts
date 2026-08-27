import { describe, expect, it } from 'vitest';

import { editPath, gateTarget } from './profileGate';
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

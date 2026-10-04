import { describe, expect, it } from 'vitest';
import type { MyProfile } from '@plone-collective/identity-core';

import { COMPLETE_PROFILE_PATH, gateTarget, profileEditPath } from './gate';

const HELD: MyProfile = {
  '@id': 'http://localhost:3000/@my-profile',
  userid: 'alice',
  profile: 'http://localhost:3000/profiles/alice',
  review_state: 'incomplete',
  missing: ['organisation'],
};

describe('gateTarget', () => {
  it('lets through a user without a profile, or with a complete one', () => {
    expect(gateTarget(null, '/news')).toBeNull();
    expect(gateTarget({ ...HELD, profile: null }, '/news')).toBeNull();
    expect(
      gateTarget({ ...HELD, review_state: 'complete' }, '/news'),
    ).toBeNull();
  });

  it('sends a held user to the explanation', () => {
    expect(gateTarget(HELD, '/news')).toBe(COMPLETE_PROFILE_PATH);
    expect(gateTarget(HELD, '/')).toBe(COMPLETE_PROFILE_PATH);
  });

  it('leaves them on the explanation, the profile and its edit form', () => {
    expect(gateTarget(HELD, COMPLETE_PROFILE_PATH)).toBeNull();
    expect(gateTarget(HELD, '/profiles/alice')).toBeNull();
    expect(gateTarget(HELD, '/@@edit/profiles/alice')).toBeNull();
  });

  it('never holds them on the way in or out', () => {
    for (const path of ['/login', '/logout', '/login-identity']) {
      expect(gateTarget(HELD, path)).toBeNull();
    }
  });

  it('asks for the address first when that is all that is missing', () => {
    const confirming = { ...HELD, missing: [], confirm_email: true };

    expect(gateTarget(confirming, '/news')).toBe('/confirm-email');
    // Even from the profile, whose form cannot answer it.
    expect(gateTarget(confirming, '/profiles/alice')).toBe('/confirm-email');
    expect(gateTarget(confirming, '/confirm-email')).toBeNull();
  });
});

describe('profileEditPath', () => {
  it("is Aurora's edit form for the profile's path", () => {
    expect(profileEditPath('http://localhost:3000/profiles/alice')).toBe(
      '/@@edit/profiles/alice',
    );
  });
});

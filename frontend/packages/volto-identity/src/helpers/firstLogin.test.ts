import { describe, expect, it } from 'vitest';

import { afterLogin, toAppPath } from './firstLogin';
import type { MyProfile } from '../types';

function profile(overrides: Partial<MyProfile> = {}): MyProfile {
  return {
    '@id': 'http://backend:8080/Plone/@my-profile',
    userid: 'alice-userid',
    profile: 'http://backend:8080/Plone/identity-profiles/alice-userid',
    review_state: 'incomplete',
    ...overrides,
  };
}

describe('toAppPath', () => {
  it('strips a configured backend base', () => {
    expect(
      toAppPath(
        'http://backend:8080/Plone/identity-profiles/alice',
        'http://backend:8080/Plone',
      ),
    ).toBe('/identity-profiles/alice');
  });

  it('strips the origin when there is no configured base', () => {
    expect(toAppPath('https://example.com/identity-profiles/alice')).toBe(
      '/identity-profiles/alice',
    );
  });

  it('leaves an already relative path alone', () => {
    expect(toAppPath('/identity-profiles/alice')).toBe(
      '/identity-profiles/alice',
    );
  });

  it('adds the leading slash a relative answer may lack', () => {
    expect(toAppPath('identity-profiles/alice')).toBe(
      '/identity-profiles/alice',
    );
  });

  it('handles an origin with nothing after it', () => {
    expect(toAppPath('https://example.com')).toBe('/');
  });

  it('treats an empty URL as the site root', () => {
    expect(toAppPath('')).toBe('/');
  });
});

describe('afterLogin', () => {
  it('diverts a user whose profile is incomplete', () => {
    expect(afterLogin(profile(), '/news', 'http://backend:8080/Plone')).toBe(
      '/identity-profiles/alice-userid',
    );
  });

  it('leaves a completed profile alone', () => {
    expect(afterLogin(profile({ review_state: 'complete' }), '/news')).toBe(
      '/news',
    );
  });

  it('does not divert a deactivated profile', () => {
    // Diverting here would send somebody to a Profile they cannot even view.
    expect(afterLogin(profile({ review_state: 'deactivated' }), '/news')).toBe(
      '/news',
    );
  });

  it('carries on when the user has no profile', () => {
    expect(
      afterLogin(profile({ profile: null, review_state: null }), '/news'),
    ).toBe('/news');
  });

  it('carries on in a site without the extra installed', () => {
    expect(afterLogin(null, '/news')).toBe('/news');
  });

  it('carries on before the answer has loaded', () => {
    expect(afterLogin(undefined, '/news')).toBe('/news');
  });
});

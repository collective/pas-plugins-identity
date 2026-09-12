import { describe, expect, it } from 'vitest';

import {
  CONFIRM_EMAIL_PATH,
  editPath,
  expandedProfile,
  gateTarget,
  handedOverReturn,
} from './profileGate';
import type { MyProfile } from '../types';

const PROFILE_URL = 'http://backend:8080/Plone/identity-profiles/alice';

function profile(overrides: Partial<MyProfile> = {}): MyProfile {
  return {
    '@id': 'http://backend:8080/Plone/@my-profile',
    userid: 'alice',
    profile: PROFILE_URL,
    review_state: 'incomplete',
    missing: [],
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

  describe('a profile held only for an address confirmation', () => {
    // The edit form cannot give one, so holding somebody there is a loop.
    const waiting = () => profile({ confirm_email: true, missing: [] });

    it('is sent to be asked', () => {
      expect(gateTarget(waiting(), '/news', api)).toBe(CONFIRM_EMAIL_PATH);
    });

    it('is left alone on the page that asks', () => {
      expect(gateTarget(waiting(), CONFIRM_EMAIL_PATH, api)).toBe(null);
    });

    it.each(['/identity-profiles/alice', '/identity-profiles/alice/edit'])(
      'is sent on from %s, which cannot answer',
      (path) => {
        expect(gateTarget(waiting(), path, api)).toBe(CONFIRM_EMAIL_PATH);
      },
    );

    it('still passes the exempt routes', () => {
      expect(gateTarget(waiting(), '/logout', api)).toBe(null);
    });

    it('fills its missing fields in first', () => {
      // From the confirmation page too: those are what the form is for, and
      // the question is still waiting once the form is saved.
      const both = profile({ confirm_email: true, missing: ['fullname'] });

      expect(gateTarget(both, '/news', api)).toBe(
        '/identity-profiles/alice/edit',
      );
      expect(gateTarget(both, CONFIRM_EMAIL_PATH, api)).toBe(
        '/identity-profiles/alice/edit',
      );
    });
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

describe('expandedProfile', () => {
  const component = { userid: 'alice', review_state: 'incomplete' };

  // The apiPath the test environment configures, which is what
  // `flattenToAppURL` measures against.
  const API = 'http://localhost:8080/Plone';

  function content(id: string, extra: any = component) {
    return {
      data: {
        '@id': `${API}${id}`,
        '@components': extra ? { 'my-profile': extra } : {},
      },
    };
  }

  it('returns the component when the content is this page', () => {
    expect(expandedProfile(content('/a-page'), '/a-page')).toEqual(component);
  });

  it('is null when the content is a different page', () => {
    // Volto keeps the last content it loaded, so a route that fetches none
    // leaves the previous page's answer in the store. Using it would read a
    // stale answer to a question whose whole point is freshness.
    expect(expandedProfile(content('/a-page'), '/identities')).toBeNull();
  });

  it('is null when the component is only an @id', () => {
    // Unexpanded. A URL is not an answer.
    expect(
      expandedProfile(content('/a-page', { '@id': '/@my-profile' }), '/a-page'),
    ).toBeNull();
  });

  it('is null when there is no component at all', () => {
    // An anonymous response, or a backend too old to offer it.
    expect(expandedProfile(content('/a-page', null), '/a-page')).toBeNull();
  });

  it('is null when nothing has loaded', () => {
    expect(expandedProfile(undefined, '/a-page')).toBeNull();
    expect(expandedProfile({}, '/a-page')).toBeNull();
  });

  it('matches the site root, which flattens to an empty string', () => {
    // The one path where the two spellings genuinely differ: the router says
    // `/` and `flattenToAppURL` says ``.
    expect(expandedProfile(content(''), '/')).toEqual(component);
  });
});

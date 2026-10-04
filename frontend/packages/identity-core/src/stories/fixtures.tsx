/**
 * Data for the stories of this package's components.
 *
 * Shared with the Volto add-on's stories, which re-export it, so a provider
 * looks the same in every story.
 * @module stories/fixtures
 */
import React from 'react';
import type { ReactNode } from 'react';

import LoginCard from '../components/Login/LoginCard';
import type { Identity, LoginProvider, ProfileEmail } from '../types';

/** A request that has finished with data. */
export const LOADED = { loading: false, loaded: true, error: null };

/** A request still in flight. */
export const LOADING = { loading: true, loaded: false, error: null };

/** A request that was refused. */
export const FAILED = { loading: false, loaded: false, error: { status: 401 } };

export const GOOGLE: LoginProvider = {
  '@id': '/@login-providers/google',
  id: 'google',
  title: 'Google',
  driver: 'google',
};

export const GITHUB: LoginProvider = {
  '@id': '/@login-providers/github',
  id: 'github',
  title: 'GitHub',
  driver: 'github',
};

export const KEYCLOAK: LoginProvider = {
  '@id': '/@login-providers/keycloak',
  id: 'keycloak',
  title: 'Sign in with Keycloak',
  driver: 'oidc-generic',
};

export const EMAIL: LoginProvider = {
  '@id': '/@login-providers/email',
  id: 'email',
  title: 'Email',
  driver: 'email',
};

export const PROVIDERS = [GOOGLE, GITHUB, KEYCLOAK];

/** A profile's addresses: one proved, one not. */
export const PROFILE_EMAILS: ProfileEmail[] = [
  { address: 'erico@plone.org', verified: true, preferred: true },
  { address: 'erico@example.com', verified: false, preferred: false },
];

export const IDENTITIES: Identity[] = [
  {
    '@id': '/@identities/google:1234',
    provider: 'google',
    subject: '1234567890',
    title: 'Google',
    created: '2026-01-14T09:12:00+00:00',
    last_login: '2026-08-21T18:03:00+00:00',
    can_unlink: true,
  },
  {
    '@id': '/@identities/github:99',
    provider: 'github',
    subject: '99',
    title: 'GitHub',
    created: '2026-03-02T11:40:00+00:00',
    last_login: null,
    can_unlink: true,
  },
];

/** The last way in: unlinking it would lock the user out. */
export const ONLY_IDENTITY: Identity[] = [
  { ...IDENTITIES[0], can_unlink: false },
];

/**
 * A provider carrying the look an operator gave it.
 *
 * The icon is a real SVG rather than a placeholder, because the point of the
 * story is that the button is drawn from it: a stand-in string would render
 * an empty box and prove nothing.
 */
export const STYLED: LoginProvider = {
  '@id': '/@login-providers/acme',
  id: 'acme',
  title: 'Acme SSO',
  driver: 'oidc-generic',
  icon:
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">' +
    '<path d="M8 1l7 13H1z"/></svg>',
  background_color: '#4b3f72',
  foreground_color: '#ffffff',
};

/**
 * Render a story inside the login card, at the real page's dimensions.
 *
 * `LoginForm`, `PasswordForm` and `MagicLinkForm` are never seen anywhere but
 * inside `LoginCard`, and the card is what sizes them: the card is
 * `--identity-login-width` wide and the forms lay themselves out against
 * that. On Storybook's full-width canvas they stretched to whatever the
 * viewport was, so a story could look fine and the page wrong -- and two
 * forms meant to be indistinguishable could not be compared at all.
 *
 * The real component rather than a `<div>` of the same width, so the stories
 * cannot drift from the page: a change to the card's width or padding shows
 * up here without anybody remembering to copy it.
 *
 * @param description The strip under the heading, which names what is below
 *   -- the real page picks between two sentences depending on what a site has
 *   configured, so a story showing only the password form passes the other.
 * @returns A Storybook decorator.
 */
export function withLoginCard(
  description = 'Choose how you would like to sign in.',
) {
  const Decorator = (Story: () => ReactNode) => (
    <LoginCard title="Log in" description={description}>
      {Story()}
    </LoginCard>
  );
  return Decorator;
}

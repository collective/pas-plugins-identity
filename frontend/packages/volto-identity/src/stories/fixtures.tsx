/**
 * Shared fixtures and decorators for the stories.
 *
 * Two things every story in this package needs. The data is the shape the
 * backend actually returns, copied from `types` rather than invented, so a
 * story that renders is evidence the component can render what it will really
 * be given. And the connected components need a store: Storybook's preview
 * wraps stories in an `IntlProvider` and a router, but not a redux
 * `Provider`, and half of this add-on reads `useSelector`.
 *
 * The store is inert on purpose. A story is a picture of one state, so
 * dispatching does nothing and the state never changes -- which is also what
 * makes a loading state or an error state something you can simply ask for.
 * @module stories/fixtures
 */
import React from 'react';
import type { ReactNode } from 'react';
import { Provider } from 'react-redux';

import type {
  ConfiguredProvider,
  Driver,
  Identity,
  LoginProvider,
  OAuthClient,
  SigningKeyRing,
} from '../types';

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

export const OIDC_DRIVER: Driver = {
  id: 'oidc-generic',
  title: 'OpenID Connect',
  schema: {
    client_id: {
      type: 'string',
      title: 'Client ID',
      required: true,
      secret: false,
    },
    client_secret: {
      type: 'string',
      title: 'Client secret',
      required: true,
      secret: true,
    },
    issuer: {
      type: 'string',
      title: 'Issuer URL',
      description:
        'Discovery is fetched from <issuer>/.well-known/openid-configuration.',
      required: true,
      secret: false,
    },
    scope: { type: 'string', title: 'Scope', required: false, secret: false },
  },
};

export const DRIVERS: Driver[] = [
  OIDC_DRIVER,
  { id: 'google', title: 'Google', schema: OIDC_DRIVER.schema },
  { id: 'github', title: 'GitHub', schema: OIDC_DRIVER.schema },
];

export const CONFIGURED: ConfiguredProvider[] = [
  {
    '@id': '/@identity-providers/keycloak',
    id: 'keycloak',
    driver: 'oidc-generic',
    title: 'Sign in with Keycloak',
    enabled: true,
    config: {
      client_id: 'plone',
      client_secret: '••••••••',
      issuer: 'https://id.example.org/realms/main',
      scope: 'openid email profile',
    },
  },
  {
    '@id': '/@identity-providers/github',
    id: 'github',
    driver: 'github',
    title: 'GitHub',
    enabled: false,
    config: { client_id: 'Iv1.0123456789abcdef', client_secret: '••••••••' },
  },
];

export const CLIENT: OAuthClient = {
  '@id': '/@identity-clients/intranet',
  client_id: 'intranet',
  title: 'Intranet',
  redirect_uris: ['https://intranet.example.org/login-identity'],
  grant_types: ['authorization_code', 'refresh_token'],
  scope: 'openid email profile',
  auth_method: 'client_secret_post',
  public: false,
  enabled: true,
  service_user: '',
};

export const CLIENTS: OAuthClient[] = [
  CLIENT,
  {
    ...CLIENT,
    '@id': '/@identity-clients/kiosk',
    client_id: 'kiosk',
    title: 'Lobby kiosk',
    auth_method: 'none',
    public: true,
    enabled: false,
  },
];

/** A client as it comes back from the one response that carries a secret. */
export const MINTED_CLIENT: OAuthClient = {
  ...CLIENT,
  secret: 'Yb3nT7qk-2sV1pE0xR8wL4mZ6aQ9cJ5dN0gH2fK1uS',
  notice:
    'This secret is shown once and is not recoverable. Store it before leaving this page.',
};

export const KEYRING: SigningKeyRing = {
  '@id': '/@identity-keys',
  algorithm: 'RS256',
  ring_size: 2,
  jwks_uri: 'https://example.org/@@oauth-jwks',
  items_total: 2,
  items: [
    { kid: 'q7Yk2mVx', active: true },
    { kid: 'b1Rn8dTs', active: false },
  ],
};

/**
 * Wrap a story in a redux store holding exactly the state it wants.
 *
 * @param state The store's whole state, as the component's selectors read it.
 * @returns A Storybook decorator.
 */
export function withStore(state: Record<string, unknown>) {
  const store = {
    getState: () => state,
    dispatch: (action: unknown) => action,
    subscribe: () => () => {},
  };
  const Decorator = (Story: () => ReactNode) => (
    <Provider store={store as never}>{Story()}</Provider>
  );
  return Decorator;
}

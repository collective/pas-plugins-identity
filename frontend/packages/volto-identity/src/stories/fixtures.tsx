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
  ConsentRequest,
  Driver,
  Identity,
  LoginProvider,
  OAuthClient,
  OAuthGrants,
  SigningKeyRing,
  UserProfile,
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
    group_claim: {
      type: 'string',
      title: 'Groups arrive in the claim',
      description: 'Which claim carries the group names this provider asserts.',
      required: false,
      secret: false,
      default: 'groups',
    },
  },
};

/**
 * A driver whose providers have no groups.
 *
 * The real GitHub driver is this case, and the difference is worth having in
 * the fixtures: the group mapping is offered for a driver that declares a
 * group claim and hidden for one that does not, so a story showing only the
 * first would never show the second.
 */
const { group_claim: _groupClaim, ...NO_GROUPS_SCHEMA } = OIDC_DRIVER.schema;

export const DRIVERS: Driver[] = [
  OIDC_DRIVER,
  { id: 'google', title: 'Google', schema: OIDC_DRIVER.schema },
  { id: 'github', title: 'GitHub', schema: NO_GROUPS_SCHEMA },
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
    propertymap: {
      preferred_username: 'username',
      'address.formatted': 'location',
    },
    groupmap: {
      'plone-editors': 'Site Administrators',
      'plone-staff': 'Reviewers',
    },
  },
  {
    '@id': '/@identity-providers/github',
    id: 'github',
    driver: 'github',
    title: 'GitHub',
    enabled: false,
    config: { client_id: 'Iv1.0123456789abcdef', client_secret: '••••••••' },
    propertymap: {},
    groupmap: {},
  },
];

/**
 * The vocabulary the property-map editor reads, already loaded.
 *
 * Served by the backend from the site's live user schema, so a story shows
 * a representative subset rather than a list this file owns.
 */
export const USER_FIELDS_STATE = {
  'pas.plugins.identity.UserFields': {
    loaded: true,
    loading: false,
    items: [
      { value: 'description', label: 'Biography' },
      { value: 'email', label: 'Email' },
      { value: 'fullname', label: 'Full Name' },
      { value: 'home_page', label: 'Home page' },
      { value: 'location', label: 'Location' },
      { value: 'username', label: 'Username' },
    ],
    itemsTotal: 6,
  },
};

/**
 * The vocabulary the group-map editor reads, already loaded.
 *
 * Every group PAS knows on the site, which is why the local half of a group
 * mapping is a picker: a group that does not exist here grants nothing, and
 * that is a typo worth catching in the form rather than in a log line.
 */
export const GROUPS_STATE = {
  'pas.plugins.identity.Groups': {
    loaded: true,
    loading: false,
    items: [
      { value: 'Administrators', label: 'Administrators' },
      { value: 'Reviewers', label: 'Reviewers' },
      { value: 'Site Administrators', label: 'Site Administrators' },
    ],
    itemsTotal: 3,
  },
};

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

/** The applications a user has authorized, as `@oauth-grants` lists them. */
export const GRANTS: OAuthGrants = {
  '@id': 'http://id.localhost/@oauth-grants',
  access_token_ttl: 900,
  items: [
    {
      '@id': 'http://id.localhost/@oauth-grants/demo-rp',
      client_id: 'demo-rp',
      title: 'Plone Content Site',
      registered: true,
      enabled: true,
      granted_at: '2026-08-24T09:15:00+00:00',
      scopes: [
        { id: 'openid', claims: [] },
        {
          id: 'profile',
          claims: ['name', 'preferred_username', 'picture', 'description'],
        },
        { id: 'email', claims: ['email', 'email_verified'] },
      ],
    },
    {
      '@id': 'http://id.localhost/@oauth-grants/reporting',
      client_id: 'reporting',
      title: 'Nightly reporting job',
      registered: true,
      enabled: true,
      granted_at: '2026-06-02T22:40:00+00:00',
      scopes: [{ id: 'openid', claims: [] }],
    },
  ],
};

/** A pending authorization request, as `@oauth-consent` describes one. */
export const CONSENT_REQUEST: ConsentRequest = {
  '@id': 'http://id.localhost/@oauth-consent',
  client: { id: 'demo-rp', title: 'Plone Content Site' },
  user: { id: 'alice', label: 'Alice Liddell' },
  scopes: [
    { id: 'openid', claims: [] },
    { id: 'profile', claims: ['name', 'preferred_username', 'picture'] },
    { id: 'email', claims: ['email', 'email_verified'] },
  ],
  authorize_url: 'http://id.localhost/@@oauth-authorize',
  params: {
    response_type: 'code',
    client_id: 'demo-rp',
    redirect_uri: 'http://plone.localhost/login-identity',
    scope: 'openid profile email',
    state: 'a1b2c3',
  },
  authenticator: 'a-plone-protect-token',
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

/**
 * A portrait, inline.
 *
 * A data URI rather than a URL: a story has to render the same whether or
 * not Storybook can reach the network, and a portrait that silently 404s
 * would show the fallback while claiming to show the picture.
 */
export const PORTRAIT =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96">
       <rect width="96" height="96" fill="#0083be"/>
       <circle cx="48" cy="36" r="18" fill="#bfe3f2"/>
       <path d="M12 96c0-20 16-32 36-32s36 12 36 32z" fill="#bfe3f2"/>
     </svg>`,
  );

/** The signed-in user, as `@users/<userid>` describes them. */
export const USER: UserProfile = {
  '@id': 'https://example.org/@users/alice',
  id: 'alice',
  username: 'alice@example.org',
  fullname: 'Alice Liddell',
  email: 'alice@example.org',
  portrait: null,
  source: 'identity_profile',
  identities: [],
  profile_url: 'https://example.org/identity-profiles/alice',
};

/**
 * Wrap a story in a store holding one signed-in user.
 *
 * The common case for anything in the user menu, which is why it is here
 * rather than repeated per story.
 *
 * @param user The user, or null for an anonymous visitor.
 * @returns A Storybook decorator.
 */
export function withUser(user: Partial<UserProfile> | null) {
  return withStore({
    userProfile: {
      ...LOADED,
      data: user === null ? null : { ...USER, ...user },
    },
  });
}

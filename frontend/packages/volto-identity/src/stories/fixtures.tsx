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

import LoginPanel from '../components/Login/LoginPanel';

import type {
  ConfiguredProvider,
  ConsentRequest,
  Driver,
  Identity,
  LoginProvider,
  OAuthClient,
  OAuthGrants,
  SigningKeyRing,
  UserAccount,
  UserProfile,
  ProfileEmail,
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
 * What one entry of `@identity-drivers` sends: `IOIDCSettings`, serialized.
 *
 * An ordinary JSON schema, because that is what the backend produces now --
 * `plone.restapi`'s own `get_fieldsets` / `get_jsonschema_properties` /
 * `get_fieldset_infos`, the same three calls that answer `@controlpanels`.
 * Titles arrive translated and widgets arrive decided, which is why nothing
 * here carries a `secret` flag or an `order`: a secret is a `Password` field
 * and the order is the order the properties are in.
 */
export const OIDC_DRIVER: Driver = {
  id: 'oidc-generic',
  title: 'OpenID Connect',
  schema: {
    properties: {
      issuer: {
        type: 'string',
        title: 'Issuer URL',
        description:
          'Discovery is fetched from <issuer>/.well-known/openid-configuration.',
      },
      client_id: {
        type: 'string',
        title: 'Client ID',
        description: 'The identifier this provider issued for this site.',
      },
      client_secret: {
        type: 'string',
        title: 'Client secret',
        description: 'Write-only. It is never sent back by any endpoint here.',
        widget: 'password',
      },
      scope: {
        type: 'array',
        title: 'Scope',
        description: 'One permission per entry.',
        widget: 'token',
      },
      userid_source: {
        type: 'string',
        title: 'Userid taken from',
        choices: [
          ['uuid', 'A random id'],
          ['username', "The provider's username"],
          ['email', 'The email address'],
          ['subject', "The provider's subject identifier"],
        ],
      },
      group_claim: {
        type: 'string',
        title: 'Groups arrive in the claim',
        description:
          'Which claim carries the group names this provider asserts.',
      },
    },
    required: ['issuer', 'client_id', 'client_secret'],
    fieldsets: [
      {
        id: 'default',
        title: 'Default',
        fields: [
          'issuer',
          'client_id',
          'client_secret',
          'scope',
          'userid_source',
          'group_claim',
        ],
      },
    ],
  },
};

/**
 * A driver whose providers have no groups.
 *
 * The real GitHub driver is this case, and the difference is worth having in
 * the fixtures: the group mapping is offered for a driver that declares a
 * group claim and hidden for one that does not, so a story showing only the
 * first would never show the second. `IGitHubSettings` extends the OAuth2
 * base and adds nothing, so the absence here is the absence there.
 */
const NO_GROUPS_SCHEMA: Driver['schema'] = {
  properties: Object.fromEntries(
    Object.entries(OIDC_DRIVER.schema.properties ?? {}).filter(
      ([name]) => name !== 'group_claim' && name !== 'issuer',
    ),
  ),
  required: ['client_id', 'client_secret'],
  fieldsets: [
    {
      id: 'default',
      title: 'Default',
      fields: ['client_id', 'client_secret', 'scope', 'userid_source'],
    },
  ],
};

export const DRIVERS: Driver[] = [
  OIDC_DRIVER,
  { id: 'google', title: 'Google', schema: OIDC_DRIVER.schema },
  { id: 'github', title: 'GitHub', schema: NO_GROUPS_SCHEMA },
];

/**
 * What `@identity-providers` sends alongside the listing: `IProviderRecords`.
 *
 * The provider's own half of the form -- everything true of a provider
 * whatever its driver. The panel renders this and the chosen driver's schema
 * together, which is why a story needs both.
 */
export const PROVIDER_SCHEMA = {
  type: 'object',
  properties: {
    // Served, and dropped again by `providerSchema`: a provider's storage
    // has a driver and two maps, and none of the three is renderable as
    // described. Kept here because a fixture that quietly leaves them out
    // would stop the stories from showing what the composition does.
    driver: { type: 'string', title: 'Driver' },
    propertymap: { type: 'object', title: 'Property map' },
    groupmap: { type: 'object', title: 'Group map' },
    title: { type: 'string', title: 'Title' },
    enabled: { type: 'boolean', title: 'Enabled' },
    show_in_login: { type: 'boolean', title: 'Show on the login screen' },
    order: { type: 'integer', title: 'Order' },
    icon: { type: 'string', title: 'Icon', widget: 'provider_icon' },
    background_color: {
      type: 'string',
      title: 'Background colour',
      widget: 'color_picker',
    },
    foreground_color: {
      type: 'string',
      title: 'Foreground colour',
      widget: 'color_picker',
    },
  },
  required: [],
  fieldsets: [
    {
      id: 'default',
      title: 'Default',
      fields: [
        'driver',
        'title',
        'enabled',
        'show_in_login',
        'order',
        'propertymap',
        'groupmap',
      ],
    },
    {
      id: 'style',
      title: 'Style',
      fields: ['icon', 'background_color', 'foreground_color'],
    },
  ],
};

export const CONFIGURED: ConfiguredProvider[] = [
  {
    '@id': '/@identity-providers/keycloak',
    id: 'keycloak',
    driver: 'oidc-generic',
    title: 'Sign in with Keycloak',
    enabled: true,
    show_in_login: true,
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
    show_in_login: false,
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
  scope: ['openid', 'email', 'profile'],
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
/**
 * One account as `@user-account` serves it.
 *
 * Shared, because two stories show it: the panel on its own, and the control
 * panel page that fetches it.
 */
export const USER_ACCOUNT: UserAccount = {
  '@id': '/@user-account/erico',
  userid: 'erico',
  fullname: 'Érico Andrei',
  profile_url: '/identity-profiles/erico',
  identities: [
    {
      provider: 'github',
      title: 'GitHub',
      subject: '99',
      created: '2026-03-02T11:40:00+00:00',
      last_login: '2026-08-21T18:03:00+00:00',
      provider_configured: true,
      provider_enabled: true,
      groups: ['site-editors'],
    },
    {
      provider: 'email',
      title: 'Email',
      subject: 'erico@plone.org',
      created: '2026-01-14T09:12:00+00:00',
      last_login: null,
      provider_configured: true,
      provider_enabled: true,
      groups: [],
    },
  ],
  emails: [
    { address: 'erico@plone.org', verified: true, preferred: true },
    { address: 'erico@example.com', verified: false, preferred: false },
  ],
  last_authenticated: '2026-08-21T18:03:00+00:00',
  events_total: 2,
  events: [
    {
      event: 'authenticated',
      provider: 'github',
      success: true,
      timestamp: '2026-08-21T18:03:00+00:00',
      detail: {},
    },
    {
      event: 'magic-link-sent',
      provider: 'email',
      success: true,
      timestamp: '2026-08-20T09:00:00+00:00',
      detail: {},
    },
  ],
};

/**
 * Render a story inside the login card, at the real page's dimensions.
 *
 * `LoginForm`, `PasswordForm` and `MagicLinkForm` are never seen anywhere but
 * inside `LoginPanel`, and the panel is what sizes them: the card is
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
    <LoginPanel title="Log in" description={description}>
      {Story()}
    </LoginPanel>
  );
  return Decorator;
}

/**
 * The store slices Volto's own chrome reads, which no story is about.
 *
 * Five pages here portal Volto's `Toolbar`, and it selects these four out of
 * the store whatever the page is. A story that left them out did not render
 * at all -- the failure was a TypeError from inside Volto, which reads as the
 * add-on being broken rather than as a fixture missing furniture.
 *
 * Exactly four, established by removing each in turn: `apierror`, `intl` and
 * `workflow` were guesses and are not read.
 */
export const VOLTO_CHROME = {
  actions: { actions: {} },
  content: { data: null },
  types: { types: [] },
  userSession: { token: null },
};

/**
 * A store for a story, over the chrome every page needs.
 *
 * The story's own state wins, so a story about being signed in can say so by
 * passing its own `userSession`.
 */
export function withStore(state: Record<string, unknown>) {
  const merged = { ...VOLTO_CHROME, ...state };
  const store = {
    getState: () => merged,
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

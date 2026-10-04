/**
 * Every REST path the frontends call, in one place.
 *
 * Each entry builds the path relative to the site root, query string
 * included. Volto's actions hand it to the API middleware; Aurora's loaders
 * prefix it with the backend URL. Neither frontend spells a path itself, so
 * the two cannot drift apart from each other, or from the backend services
 * they call.
 * @module endpoints
 */

const enc = encodeURIComponent;

/** `@identity-providers`: the providers this site lets people sign in with. */
const PROVIDERS = '/@identity-providers';

/** `@identity-clients`: the OAuth clients this site issues tokens to. */
const CLIENTS = '/@identity-clients';

/** `@oauth-grants`: the clients the current user has granted access to. */
const GRANTS = '/@oauth-grants';

/** `@identity-keys`: the keys this site signs its tokens with. */
const KEYS = '/@identity-keys';

export const endpoints = {
  /**
   * One user's account, with its audit trail.
   *
   * @param userid The user.
   * @param events How many audit events to include; the backend's default
   *   when absent.
   */
  userAccount(userid: string, events?: number): string {
    const query = events === undefined ? '' : `?events=${events}`;
    return `/@user-account/${enc(userid)}${query}`;
  },

  /** The OAuth clients. */
  clients(): string {
    return CLIENTS;
  },

  /** @param clientId One OAuth client. */
  client(clientId: string): string {
    return `${CLIENTS}/${enc(clientId)}`;
  },

  /** @param clientId The OAuth client whose secret to replace. */
  clientSecretRotation(clientId: string): string {
    return `${CLIENTS}/${enc(clientId)}/rotate-secret`;
  },

  /**
   * The consent request an OAuth client sent the user here with.
   *
   * @param search The query string the client sent, leading `?` included.
   */
  consent(search: string): string {
    return `/@oauth-consent${search}`;
  },

  /** The clients the current user has granted access to. */
  grants(): string {
    return GRANTS;
  },

  /** @param clientId The client whose grant to withdraw. */
  grant(clientId: string): string {
    return `${GRANTS}/${enc(clientId)}`;
  },

  /** The provider drivers this site has installed. */
  drivers(): string {
    return '/@identity-drivers';
  },

  /**
   * The members of one group, nested memberships included.
   *
   * @param groupId The group.
   * @param query Case-insensitive substring, matched against name and login.
   */
  groupMembers(groupId: string, query = ''): string {
    const search = query ? `?query=${enc(query)}` : '';
    return `/@group-members/${enc(groupId)}${search}`;
  },

  /**
   * The current user's linked identities.
   *
   * @param withProviders Whether to expand the providers they could link.
   */
  identities(withProviders = false): string {
    const query = withProviders ? '?expand=login-providers' : '';
    return `/@identities${query}`;
  },

  /**
   * One linked identity.
   *
   * @param provider The provider it was linked through.
   * @param subject The provider's identifier for the user.
   */
  identity(provider: string, subject: string): string {
    return `/@identities/${enc(provider)}/${enc(subject)}`;
  },

  /** The signing keys. */
  keys(): string {
    return KEYS;
  },

  /** Replacing the signing key. */
  keyRotation(): string {
    return `${KEYS}/rotate`;
  },

  /**
   * Signing in with a login name and password, through plone.restapi's own
   * `@login`.
   */
  login(): string {
    return '/@login';
  },

  /** The providers offered on the login form. */
  loginProviders(): string {
    return '/@login-providers';
  },

  /**
   * Starting a sign-in with one provider.
   *
   * The provider id is not encoded: the backend accepts only ids matching
   * `^[A-Za-z0-9_-]+$` (`PROVIDER_ID_PATTERN` in
   * `pas.plugins.identity.core.controlpanel`), none of which need it.
   *
   * @param providerId The provider.
   * @param cameFrom Where to return to afterwards.
   */
  loginProvider(providerId: string, cameFrom = ''): string {
    const query = cameFrom ? `?came_from=${enc(cameFrom)}` : '';
    return `/@login-providers/${providerId}${query}`;
  },

  /** Completing a sign-in a provider redirected back from. */
  callback(): string {
    return '/@identity-callback';
  },

  /** Sending a magic link. */
  magicLink(): string {
    return '/@magic-link';
  },

  /** Signing in with a magic link's token. */
  magicLinkConfirm(): string {
    return '/@magic-link-confirm';
  },

  /**
   * One user, through plone.restapi's own `@users`.
   *
   * @param userid The user, used as given.
   */
  user(userid: string): string {
    return `/@users/${userid}`;
  },

  /** The current user's profile state. */
  myProfile(): string {
    return '/@my-profile';
  },

  /** Confirming an email address. */
  confirmEmail(): string {
    return '/@confirm-email';
  },

  /** The configured providers. */
  providers(): string {
    return PROVIDERS;
  },

  /** @param providerId One provider. */
  provider(providerId: string): string {
    return `${PROVIDERS}/${enc(providerId)}`;
  },

  /**
   * Exporting providers as a registry document.
   *
   * @param providerId The one provider to export; every provider when absent.
   */
  providersExport(providerId?: string): string {
    return providerId === undefined
      ? `${PROVIDERS}/@export`
      : `${PROVIDERS}/${enc(providerId)}/export`;
  },

  /** @param providerId The provider whose connection to test. */
  providerTest(providerId: string): string {
    return `${PROVIDERS}/${enc(providerId)}/test-connection`;
  },
};

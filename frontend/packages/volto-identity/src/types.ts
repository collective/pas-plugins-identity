/**
 * Shapes the backend actually returns.
 * @module types
 */

/** One provider offered on the login page, from `@login-providers`. */
export interface LoginProvider {
  '@id': string;
  id: string;
  title: string;
  driver: string;
}

/** Answer from `@login-providers/<id>`: where to send the browser. */
export interface AuthorizeRedirect {
  provider: string;
  authorize_url: string;
}

/** Answer from `@identity-callback` and `@magic-link-confirm`. */
export interface TokenResponse {
  token: string;
  came_from?: string;
}

/** Reducer state shared by every request this add-on makes. */
export interface RequestState {
  loading: boolean;
  loaded: boolean;
  error: unknown | null;
}

/** One identity the signed-in user owns, from `@identities`. */
export interface Identity {
  '@id': string;
  provider: string;
  subject: string;
  title: string;
  created: string;
  last_login: string | null;
  /** False when this is the user's last way in. */
  can_unlink: boolean;
}

/** One field of a driver's configuration schema. */
export interface DriverField {
  type: string;
  title: string;
  description?: string;
  required?: boolean;
  secret: boolean;
  default?: unknown;
}

/** A driver and the form it needs, from `@identity-drivers`. */
export interface Driver {
  id: string;
  title: string;
  schema: Record<string, DriverField>;
}

/** A configured provider as the control panel sees it. */
export interface ConfiguredProvider {
  '@id': string;
  id: string;
  driver: string;
  title: string;
  enabled: boolean;
  config: Record<string, unknown>;
}

/** Answer from the per-provider connection check. */
export interface ConnectionCheck {
  ok: boolean;
  error?: string;
  authorization_endpoint?: string;
  token_endpoint?: string;
  has_jwks?: boolean;
}

/** Answer from `@my-profile`: where the caller's Profile is, and how far along. */
export interface MyProfile {
  '@id': string;
  userid: string;
  /** Absolute URL of the Profile, or null when the user has none. */
  profile: string | null;
  /** Workflow state, or null when the user has no Profile. */
  review_state: string | null;
}

/** One registered OAuth client: who may log in *to* this site. */
export interface OAuthClient {
  '@id': string;
  client_id: string;
  title: string;
  redirect_uris: string[];
  grant_types: string[];
  scope: string;
  auth_method: string;
  public: boolean;
  enabled: boolean;
  service_user: string;
  /**
   * The plaintext secret. Present only in the response that minted it, at
   * registration or rotation, and never readable again: the server stores a
   * hash. Anything holding this has to show it to the operator at once.
   */
  secret?: string;
  /** The server's own words about that, shown alongside the secret. */
  notice?: string;
}

/** One key in the signing ring. Metadata only; never key material. */
export interface SigningKey {
  kid: string;
  /** Whether this is the key currently signing. */
  active: boolean;
}

/** The signing ring, as the admin API describes it. */
export interface SigningKeyRing {
  '@id': string;
  algorithm: string;
  /** How many keys the ring holds before the oldest is dropped. */
  ring_size: number;
  jwks_uri: string;
  items_total: number;
  items: SigningKey[];
}

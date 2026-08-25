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
  /**
   * Where the field goes in the form, low first.
   *
   * A schema arrives as a JSON object serialised with sorted keys, so the
   * order the driver declared its fields in is already gone -- this is what
   * survives the wire. A field without one sinks below those that have one.
   */
  order?: number;
  /** Present on a `choice` field: the options, as [value, label] pairs. */
  choices?: [string, string][];
}

/** A driver and the form it needs, from `@identity-drivers`. */
export interface Driver {
  id: string;
  title: string;
  schema: Record<string, DriverField>;
  /**
   * Claim path to user field, seeded into a new provider's mapping.
   *
   * A starting point rather than a rule: it is written into the form like
   * anything typed there, and an operator edits or empties it before saving.
   */
  default_propertymap?: Record<string, string>;
}

/** A configured provider as the control panel sees it. */
export interface ConfiguredProvider {
  '@id': string;
  id: string;
  driver: string;
  title: string;
  enabled: boolean;
  config: Record<string, unknown>;
  /** Claim path to Plone user field, applied on every login. */
  propertymap: Record<string, string>;
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

/**
 * A user as `@users/<userid>` describes them once this add-on is installed.
 *
 * Only the fields this package adds or reads are named; the endpoint carries
 * the whole of Plone's own user representation alongside them.
 */
export interface UserProfile {
  '@id': string;
  id: string;
  /** The name this user signs in with; not the same as the userid. */
  username?: string | null;
  fullname?: string;
  email?: string;
  /** Portrait URL, when the user has uploaded one. */
  portrait?: string | null;
  /** The PAS plugin the userid came from, as PAS itself resolved it. */
  source: string | null;
  /** External identities linked to this account. */
  identities: Identity[];
  /** The user's Profile, when the `[profile]` layer has minted one. */
  profile_url: string | null;
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

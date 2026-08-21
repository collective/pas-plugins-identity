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
  /** S4: false when this is the user's last way in. */
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

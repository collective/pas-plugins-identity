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

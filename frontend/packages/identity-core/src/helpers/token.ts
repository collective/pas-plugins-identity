/**
 * Read the caller's userid out of the session token.
 *
 * Volto keeps the JWT in `state.userSession.token` and nothing else in the
 * store names the current user until something has fetched them, so the
 * token is where a userid comes from before the first request.
 *
 * This does **not** verify the token, and must never be used as if it did.
 * The signature is the backend's business: every request carrying this token
 * is checked there, and a forged one buys nothing but a userid this frontend
 * will then ask the server about and be refused.
 * @module helpers/token
 */

/**
 * Decode one base64url segment of a JWT.
 *
 * @param segment The segment, base64url encoded and unpadded.
 * @returns The decoded text, or an empty string when it is not decodable.
 */
function decodeSegment(segment: string): string {
  const base64 = segment.replace(/-/g, '+').replace(/_/g, '/');
  const padded = base64.padEnd(
    base64.length + ((4 - (base64.length % 4)) % 4),
    '=',
  );
  if (typeof atob !== 'function') {
    // Both halves of Volto have it -- the browser always, and Node since 16,
    // which is well below what Volto supports. Deliberately not falling back
    // to `Buffer`: naming it here makes webpack pull a polyfill for the whole
    // module into the client bundle, and the build then fails on a missing
    // dependency rather than on anything to do with tokens.
    return '';
  }
  try {
    // `atob` answers one character per *byte*, latin-1 -- so a userid with
    // anything outside ASCII in it arrives as mojibake unless the bytes are
    // decoded as the UTF-8 they are. A userid can hold one: `userid_source`
    // may make it the provider's username or an email address.
    const binary = atob(padded);
    const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
    return new TextDecoder().decode(bytes);
  } catch {
    return '';
  }
}

/**
 * Return the claims a JWT carries, without verifying it.
 *
 * Reading, not trusting: the backend verifies every token it is sent, and
 * nothing here decides access.
 *
 * @param token The JWT.
 * @returns The claims, or null when there is no usable token.
 */
function claimsFrom(
  token: string | undefined | null,
): Record<string, unknown> | null {
  const segment = (token ?? '').split('.')[1];
  if (!segment) {
    return null;
  }
  const decoded = decodeSegment(segment);
  if (!decoded) {
    return null;
  }
  try {
    const claims = JSON.parse(decoded);
    return claims && typeof claims === 'object' ? claims : null;
  } catch {
    // A token that is not a JWT at all. Answering "nothing" is right: the
    // alternative is throwing inside a component that renders on every page.
    return null;
  }
}

/**
 * Return the userid a session token was issued for.
 *
 * @param token The JWT from `state.userSession.token`, if there is one.
 * @returns The `sub` claim, or an empty string when there is no usable token.
 */
export function useridFromToken(token: string | undefined | null): string {
  const sub = claimsFrom(token)?.sub;
  return typeof sub === 'string' ? sub : '';
}

/**
 * Return when a session token stops being accepted.
 *
 * What a frontend storing the token in a cookie gives the cookie, so the
 * browser drops it when the backend would start refusing it.
 *
 * @param token The JWT.
 * @returns The `exp` claim as a date, or null when the token has none.
 */
export function expiryFromToken(token: string | undefined | null): Date | null {
  const exp = claimsFrom(token)?.exp;
  return typeof exp === 'number' && Number.isFinite(exp)
    ? new Date(exp * 1000)
    : null;
}

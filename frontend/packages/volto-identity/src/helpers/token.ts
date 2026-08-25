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
 * Return the userid a session token was issued for.
 *
 * @param token The JWT from `state.userSession.token`, if there is one.
 * @returns The `sub` claim, or an empty string when there is no usable token.
 */
export function useridFromToken(token: string | undefined | null): string {
  const segment = (token ?? '').split('.')[1];
  if (!segment) {
    return '';
  }
  const decoded = decodeSegment(segment);
  if (!decoded) {
    return '';
  }
  try {
    const claims = JSON.parse(decoded);
    return typeof claims?.sub === 'string' ? claims.sub : '';
  } catch {
    // A token that is not a JWT at all. Answering "nobody" is right: the
    // alternative is throwing inside a component that renders on every page.
    return '';
  }
}

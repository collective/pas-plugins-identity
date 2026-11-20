/**
 * Handing the session token to an application on the person's own computer.
 *
 * A command-line tool opens `/login?return_url=<loopback URL>&state=<state>`
 * in a browser and listens on that loopback address. After sign-in, and only
 * after the person allows it on the consent page, the browser form-POSTs
 * `token` and `state` there. The contract is `volto-authomatic`'s
 * (collective/volto-authomatic#50), so one client works against both add-ons.
 *
 * The request is kept in a cookie between the login page and the consent
 * page, not in the URL: a provider redirect drops the query string, and an
 * emailed magic link opens in another tab, where `sessionStorage` is empty.
 * It never reaches the backend as `came_from`.
 *
 * Pure apart from the cookie, because every branch here decides whether a
 * session token leaves the site.
 * @module helpers/handoff
 */

/** The route that asks whether to hand the token over. */
export const HANDOFF_PATH = '/login-handoff';

/** The cookie holding the pending request. */
export const HANDOFF_COOKIE = 'identity_handoff';

/**
 * How long a pending request survives, in seconds.
 *
 * Long enough for a provider round trip, a magic link and a profile form
 * the gate may put in the way. Short enough that an abandoned request does
 * not turn up on somebody's next ordinary sign-in.
 */
export const HANDOFF_MAX_AGE = 30 * 60;

/**
 * Host names a loopback `return_url` may use, as `URL.hostname` spells them.
 *
 * `localhost` as well as the two addresses: the contract allows it, and a
 * client that listens on it would otherwise get nothing.
 */
const LOOPBACK_HOSTS = ['127.0.0.1', '[::1]', 'localhost'];

/** A request to hand the token over. */
export interface HandoffRequest {
  /** The loopback URL the form is posted to, normalized. */
  returnUrl: string;
  /** Sent back unchanged, so the client can match the answer to its request. */
  state: string;
}

/**
 * Return a loopback `return_url` in normal form, or null.
 *
 * Plain `http` on one of the loopback hosts, with an explicit port and no
 * credentials. Anything else is not a loopback listener, and posting a
 * session token to it would be handing it to whoever owns that address.
 *
 * @param value The raw `return_url`.
 * @returns The normalized URL, or null when it is not a loopback URL.
 */
export function loopbackUrl(value: unknown): string | null {
  if (typeof value !== 'string' || !/^http:\/\//i.test(value)) {
    return null;
  }
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    return null;
  }
  if (
    url.protocol !== 'http:' ||
    !LOOPBACK_HOSTS.includes(url.hostname) ||
    url.port === '' ||
    url.username !== '' ||
    url.password !== ''
  ) {
    return null;
  }
  return url.href;
}

/**
 * Read a handoff request off the login page's query string.
 *
 * @param search The location's query string.
 * @returns The request; `refused` for a loopback `return_url` without a
 *   `state`, or with more than one of either; or null when the visit is not
 *   a handoff at all.
 */
export function readHandoffRequest(
  search: string,
): HandoffRequest | 'refused' | null {
  const params = new URLSearchParams(search);
  const urls = params.getAll('return_url');
  if (!urls.some((value) => loopbackUrl(value))) {
    return null;
  }
  const states = params.getAll('state');
  const returnUrl = urls.length === 1 ? loopbackUrl(urls[0]) : null;
  if (!returnUrl || states.length !== 1 || !states[0]) {
    return 'refused';
  }
  return { returnUrl, state: states[0] };
}

/**
 * Remember a handoff request until the consent page.
 *
 * @param request The request to keep.
 */
export function storeHandoff(request: HandoffRequest): void {
  if (typeof document === 'undefined') {
    return;
  }
  const value = encodeURIComponent(JSON.stringify(request));
  document.cookie =
    `${HANDOFF_COOKIE}=${value}; Path=/; Max-Age=${HANDOFF_MAX_AGE}; ` +
    'SameSite=Lax';
}

/** Forget any pending handoff request. */
export function clearHandoff(): void {
  if (typeof document === 'undefined') {
    return;
  }
  document.cookie = `${HANDOFF_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax`;
}

/**
 * Return the pending handoff request, checked again.
 *
 * Checked again because a cookie is input like any other: what was stored
 * as a loopback URL is not trusted to still be one.
 *
 * @returns The request, or null when none is pending or it is not valid.
 */
export function pendingHandoff(): HandoffRequest | null {
  if (typeof document === 'undefined') {
    return null;
  }
  const prefix = `${HANDOFF_COOKIE}=`;
  const raw = document.cookie
    .split(';')
    .map((part) => part.trim())
    .find((part) => part.startsWith(prefix));
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(decodeURIComponent(raw.slice(prefix.length)));
    const returnUrl = loopbackUrl(parsed?.returnUrl);
    const state = parsed?.state;
    if (!returnUrl || typeof state !== 'string' || !state) {
      return null;
    }
    return { returnUrl, state };
  } catch {
    return null;
  }
}

/**
 * Where to go once somebody has signed in.
 *
 * The consent page when a handoff is pending, otherwise the target the flow
 * already had.
 *
 * @param target Where the sign-in would otherwise land.
 * @returns The path to go to.
 */
export function afterSignIn(target: string): string {
  return pendingHandoff() ? HANDOFF_PATH : target;
}

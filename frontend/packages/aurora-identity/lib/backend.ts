/**
 * Talking to the backend from Aurora's server, on the browser's behalf.
 *
 * Volto's browser talks to the backend through Volto's own proxy, which
 * rewrites every request into a virtual-host URL naming the public origin.
 * Aurora's routes call the backend from the server instead, so they have to
 * do two things that proxy did for free:
 *
 * - **Name the public origin.** The backend builds the provider callback URL
 *   from the portal URL. Asked directly at `http://localhost:8080/Plone`, it
 *   would hand the provider a callback on the backend, and the provider would
 *   send the user there instead of back to Aurora.
 * - **Carry the flow cookie.** Starting a sign-in sets a signed cookie
 *   holding the `state`, the PKCE verifier and the nonce, and finishing it
 *   reads that cookie back. That cookie has to reach the browser, and come
 *   back from it, through Aurora.
 * @module lib/backend
 */

/**
 * The cookie the backend keeps a sign-in's state in.
 *
 * `COOKIE_NAME` in `pas.plugins.identity.core.flows.session`.
 */
export const FLOW_COOKIE = '__pas_identity_flow';

/**
 * Build the URL to call a backend service at, as the public site.
 *
 * The same virtual-host URL Volto's proxy builds: the backend sees the
 * public protocol, host and port, and the site's own path stays out of every
 * URL it answers with.
 *
 * @param apiPath The backend site's URL, `PLONE_API_PATH`.
 * @param publicUrl The URL the browser asked Aurora for.
 * @param path The service path, from `endpoints`.
 * @returns The URL to fetch.
 */
export function backendUrl(
  apiPath: string,
  publicUrl: string,
  path: string,
): string {
  const backend = new URL(apiPath);
  const site = backend.pathname.replace(/\/+$/, '');
  const visible = new URL(publicUrl);
  const protocol = visible.protocol.replace(/:$/, '');
  const port = visible.port || (protocol === 'https' ? '443' : '80');
  return (
    `${backend.origin}/VirtualHostBase/${protocol}/${visible.hostname}:${port}` +
    `${site}/++api++/VirtualHostRoot${path}`
  );
}

/**
 * Pick the flow cookie out of the browser's `Cookie` header.
 *
 * Only that one is passed on. Everything else the browser sends belongs to
 * Aurora, the session cookie included, and is not the backend's to see.
 *
 * @param cookieHeader The request's `Cookie` header.
 * @returns A `Cookie` header carrying the flow cookie alone, or an empty
 *   string when the browser sent none.
 */
export function flowCookie(cookieHeader: string | null): string {
  for (const part of (cookieHeader ?? '').split(';')) {
    const pair = part.trim();
    if (pair.startsWith(`${FLOW_COOKIE}=`)) {
      return pair;
    }
  }
  return '';
}

/**
 * The flow cookie the backend set, or cleared, as headers for the browser.
 *
 * Verbatim: the backend's cookie names no domain, so the browser files it
 * under Aurora's host, and `Path=/`, `HttpOnly` and `SameSite=Lax` keep
 * meaning what the backend chose. Cookies by any other name are dropped.
 *
 * @param from The backend's answer.
 * @returns Headers carrying its flow cookie, if it set one.
 */
export function flowCookieHeaders(from: Response): Headers {
  const headers = new Headers();
  for (const header of from.headers.getSetCookie()) {
    if (header.startsWith(`${FLOW_COOKIE}=`)) {
      headers.append('Set-Cookie', header);
    }
  }
  return headers;
}

/**
 * Copy the flow cookie the backend set, or cleared, onto a response.
 *
 * @param from The backend's answer.
 * @param to The response going to the browser.
 * @returns The response going to the browser.
 */
export function relayFlowCookie(from: Response, to: Response): Response {
  for (const header of flowCookieHeaders(from).getSetCookie()) {
    to.headers.append('Set-Cookie', header);
  }
  return to;
}

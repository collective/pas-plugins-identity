/**
 * Going somewhere, without throwing the application away to do it.
 *
 * `window.location.href` is a page load: the bundle is fetched again, the
 * store is rebuilt from nothing, and every route that was already rendered is
 * rendered a second time. For an address this app owns that is pure waste, and
 * it is what six places in this add-on were doing (Érico, 2026-08-29).
 *
 * It is also the *only* option for the addresses this app does not own — a
 * provider's authorize URL, `@@oauth-authorize` on the backend — so the
 * decision cannot be "never use it". It is a question about the target, asked
 * once, here.
 *
 * A second reason to ask it in one place: `came_from` and `return_url` reach
 * this app from a query string, and handing an absolute one to the browser is
 * an open redirect. Everything site-relative goes through the router;
 * everything else is checked against the current origin first.
 * @module helpers/navigate
 */

/**
 * Whether a target is a path this application can route to itself.
 *
 * `//evil.example` is the case worth naming: it is protocol-relative, so it
 * starts with a slash and is not local at all.
 *
 * @param target Where somebody wants to go.
 * @returns Whether the router can take them.
 */
export function isInternal(target: string): boolean {
  return target.startsWith('/') && !target.startsWith('//');
}

/**
 * Whether a full page load to this target is safe to perform.
 *
 * Same origin only. A target that arrived in a query string and points
 * somewhere else is an open redirect, and the caller's fallback is a route
 * this app owns.
 *
 * @param target An absolute URL.
 * @returns Whether it stays on this site.
 */
export function isSameOrigin(target: string): boolean {
  if (typeof window === 'undefined') {
    return false;
  }
  try {
    return (
      new URL(target, window.location.origin).origin === window.location.origin
    );
  } catch {
    return false;
  }
}

/**
 * Send the browser to a target, by the cheapest route that works.
 *
 * @param target Where to go.
 * @param push The router's push or replace, for the paths it owns.
 * @param options `external` allows a full load to another origin, which is
 *   what a provider's authorize URL needs and what a `came_from` must never
 *   get.
 */
export function goTo(
  target: string,
  push: (path: string) => void,
  options: { external?: boolean } = {},
): void {
  if (!target) {
    return;
  }
  if (isInternal(target)) {
    push(target);
    return;
  }
  if (typeof window === 'undefined') {
    return;
  }
  if (options.external || isSameOrigin(target)) {
    window.location.href = target;
    return;
  }
  // Somewhere else entirely, arriving from a query string. The caller asked
  // for a site-local navigation and this is not one.
  push('/');
}

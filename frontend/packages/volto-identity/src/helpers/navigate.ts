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
 * an open redirect. Everything site-relative and routable goes through the
 * router; everything else is checked against the current origin first.
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
 * Whether a path on this origin is published by the backend rather than Volto.
 *
 * Same origin is not the same as same application. Zope publishes a whole
 * grammar of traversal namespaces alongside Volto's routes — `@@` for a view,
 * `++api++` / `++resource++` / `++plone++` for a namespace, `acl_users` for
 * PAS — and the router owns none of them.
 *
 * The premise this replaces was "site-relative means a route this app owns",
 * and `came_from` is where it breaks. Plone's `require_login` hands back a
 * *site-relative* `/@@oauth-authorize?…`, so an authorization request paused
 * for sign-in came back through the router: Volto asked plone.restapi for the
 * content at that path, dropped the authorization request's query string on
 * the way, got a 400 and rendered its own 404. The relying party that sent
 * the visitor received neither a code nor an error (Érico, 2026-08-30,
 * running the demo stack).
 *
 * Matched per segment rather than by prefix: a view can be traversed to
 * anywhere, and `/profiles/x/@@something` is as much a backend view as
 * `/@@something` is.
 *
 * @param target A path or URL.
 * @returns Whether reaching it needs a real navigation.
 */
export function isBackendView(target: string): boolean {
  const path = target.split('?')[0].split('#')[0];
  return path
    .split('/')
    .some(
      (segment) =>
        segment.startsWith('@@') ||
        segment.startsWith('++') ||
        segment === 'acl_users',
    );
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
  if (isInternal(target) && !isBackendView(target)) {
    push(target);
    return;
  }
  if (typeof window === 'undefined') {
    return;
  }
  // A site-relative backend path is same-origin by construction, so it needs
  // no permission from the caller — only a real navigation.
  if (options.external || isInternal(target) || isSameOrigin(target)) {
    window.location.href = target;
    return;
  }
  // Somewhere else entirely, arriving from a query string. The caller asked
  // for a site-local navigation and this is not one.
  push('/');
}

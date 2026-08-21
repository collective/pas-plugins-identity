/**
 * Deciding where a signed-in user lands.
 *
 * Pure, and separate from the container, because this is an open-redirect
 * check (S6) and those are worth testing on their own.
 * @module helpers/returnUrl
 */

/**
 * Work out where to send the user once they are signed in.
 *
 * Only site-relative targets survive. An absolute or protocol-relative URL
 * here would be an open redirect; the backend refuses those too, but a target
 * that never leaves the browser would never reach the backend to be checked.
 *
 * @param search The location's query string.
 * @param pathname The location's path.
 * @returns A path inside this site.
 */
export function returnUrl(search: string, pathname: string): string {
  const params = new URLSearchParams(search);
  const values = [
    ...params.getAll('return_url'),
    ...params.getAll('came_from'),
  ];
  const requested = values.length === 1 ? values[0] : undefined;

  if (
    requested &&
    requested.startsWith('/') &&
    // "//evil.example" is protocol-relative, not site-relative.
    !requested.startsWith('//')
  ) {
    return requested;
  }

  if (pathname === '/login') {
    return '/';
  }
  return pathname.replace(/\/login$/, '') || '/';
}

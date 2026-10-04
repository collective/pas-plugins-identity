/**
 * Putting the add-on's page where one of Aurora's was.
 *
 * Aurora's registry can add a route but not replace one, and its login page
 * cannot hold this add-on's forms: the slot it offers sits inside its own
 * password `<Form>`, and a form inside a form is not HTML. So the add-on
 * swaps the file the login route renders, keeping the route itself -- its
 * path, its place under Aurora's layout -- as it was.
 * @module lib/routes
 */
import type { ReactRouterRouteEntry } from '@plone/types';

/** The file Aurora's `@plone/cmsui` renders `/login` with. */
export const AURORA_LOGIN_FILE = '@plone/cmsui/routes/auth/login.tsx';

/**
 * Make every route rendered by one file render another instead.
 *
 * Changes the entries in place, the way the registry's own `registerRoute`
 * does, since the registry hands out its own array.
 *
 * @param routes The registry's routes.
 * @param from The file to replace.
 * @param to The file to render instead.
 * @returns How many routes were changed: none means `from` was not there.
 */
export function replaceRouteFile(
  routes: ReactRouterRouteEntry[],
  from: string,
  to: string,
): number {
  let replaced = 0;
  for (const route of routes) {
    if ('file' in route && route.file === from) {
      route.file = to;
      replaced += 1;
    }
    if ('children' in route && route.children) {
      replaced += replaceRouteFile(route.children, from, to);
    }
  }
  return replaced;
}

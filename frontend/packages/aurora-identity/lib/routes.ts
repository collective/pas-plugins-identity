/**
 * Placing the add-on's pages among Aurora's own.
 *
 * Aurora's registry can add a route at the top of the tree, but neither
 * replace one nor add one under a layout another add-on registered. Two
 * things the add-on needs:
 *
 * - **Its login page where Aurora's was.** Aurora's login page cannot hold
 *   this add-on's forms: the slot it offers sits inside its own password
 *   `<Form>`, and a form inside a form is not HTML. So the add-on swaps the
 *   file the login route renders, keeping the route itself -- its path, its
 *   place under Aurora's layout -- as it was.
 * - **Its other pages inside the site's frame.** A page registered at the
 *   top renders without the header, and with it the user menu that leads
 *   back. So they go under `@plone/publicui`'s layout, beside its search
 *   page.
 * @module lib/routes
 */
import type { ReactRouterRouteEntry } from '@plone/types';

/** The file Aurora's `@plone/cmsui` renders `/login` with. */
export const AURORA_LOGIN_FILE = '@plone/cmsui/routes/auth/login.tsx';

/** The layout `@plone/publicui` renders the site's pages in. */
export const PUBLIC_LAYOUT_FILE = '@plone/publicui/routes/index.tsx';

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

/**
 * Add a route under the layout a file renders.
 *
 * Changes the registry's own array in place, as `replaceRouteFile` does. The
 * route goes last: React Router ranks routes by how specific their paths
 * are, not by order, so it still wins over the layout's catch-all.
 *
 * @param routes The registry's routes.
 * @param layoutFile The file the layout renders.
 * @param route The route to add.
 * @returns Whether the layout was found.
 */
export function addRouteUnder(
  routes: ReactRouterRouteEntry[],
  layoutFile: string,
  route: ReactRouterRouteEntry,
): boolean {
  for (const entry of routes) {
    if (entry.type === 'layout' && entry.file === layoutFile) {
      entry.children.push(route);
      return true;
    }
    if ('children' in entry && entry.children) {
      if (addRouteUnder(entry.children, layoutFile, route)) {
        return true;
      }
    }
  }
  return false;
}

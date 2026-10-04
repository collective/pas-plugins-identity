/**
 * Plone's own login challenge, answered with Aurora's login page.
 *
 * The authorization endpoint hands a signed-out visitor to Plone's challenge,
 * which sends the browser to `require_login` with the whole authorization
 * request as `came_from`. That is the backend's form, and Aurora's address
 * has no such page, so this sends the browser to Aurora's login page with
 * the same `came_from`. The login page returns there only when it is a path
 * on this site.
 * @module routes/require-login
 */
import { redirect } from 'react-router';
import type { LoaderFunctionArgs } from 'react-router';

export async function loader({ request }: LoaderFunctionArgs) {
  const cameFrom = new URL(request.url).searchParams.get('came_from') ?? '';
  return redirect(
    cameFrom ? `/login?came_from=${encodeURIComponent(cameFrom)}` : '/login',
  );
}

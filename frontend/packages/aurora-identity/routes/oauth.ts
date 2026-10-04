/**
 * The authorization server's endpoints, passed on to the backend.
 *
 * A resource route: it draws nothing, and answers every method the same way.
 * See `lib/oauth` for why Aurora serves these at all.
 * @module routes/oauth
 */
import type { ActionFunctionArgs, LoaderFunctionArgs } from 'react-router';

import { passOn } from '../lib/oauth';

export async function loader({ request }: LoaderFunctionArgs) {
  return passOn(request);
}

export async function action({ request }: ActionFunctionArgs) {
  return passOn(request);
}

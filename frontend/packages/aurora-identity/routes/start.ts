/**
 * Starting a sign-in with one provider.
 *
 * A provider button sends the browser here. The backend mints the flow --
 * `state`, PKCE verifier, nonce -- answers with the provider's authorize URL,
 * and sets the cookie that holds the flow. This passes the cookie on and
 * sends the browser to the provider.
 * @module routes/start
 */
import config from '@plone/registry';
import { endpoints } from '@plone-collective/identity-core';
import { redirect } from 'react-router';
import type { LoaderFunctionArgs } from 'react-router';

import { backendUrl, relayFlowCookie } from '../lib/backend';
import { CALLBACK_PATH, PROVIDER_ID } from '../lib/paths';

/**
 * Where to go when the sign-in cannot be started.
 *
 * The callback page, which explains it and leads back to the options.
 */
const UNAVAILABLE = `${CALLBACK_PATH}?error=unavailable`;

export async function loader({ request, params }: LoaderFunctionArgs) {
  const providerId = params.provider ?? '';
  if (!PROVIDER_ID.test(providerId)) {
    throw new Response('Unknown provider', { status: 404 });
  }
  const cameFrom = new URL(request.url).searchParams.get('came_from') ?? '';

  let answer: Response;
  try {
    answer = await fetch(
      backendUrl(
        config.settings.apiPath,
        request.url,
        endpoints.loginProvider(providerId, cameFrom),
      ),
      { headers: { Accept: 'application/json' } },
    );
  } catch {
    return redirect(UNAVAILABLE);
  }
  if (!answer.ok) {
    return redirect(UNAVAILABLE);
  }

  const { authorize_url: authorizeUrl } = (await answer.json()) as {
    authorize_url?: string;
  };
  // The provider's address, from the provider's discovery document. Only a
  // web address is followed: anything else is not a provider.
  if (!authorizeUrl || !/^https?:\/\//.test(authorizeUrl)) {
    return redirect(UNAVAILABLE);
  }
  return relayFlowCookie(answer, redirect(authorizeUrl));
}

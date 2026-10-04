/**
 * The page a provider -- or a magic link -- sends the browser back to.
 *
 * The loader finishes the sign-in on the server: it hands the backend the
 * `code` and `state` with the flow cookie the browser brought back, or the
 * magic link's token, and stores the session token the backend answers with
 * in Aurora's own session cookie. The page itself is drawn only when that did
 * not work, to say why.
 * @module routes/callback
 */
import config from '@plone/registry';
import { getAuthFromRequest, setAuthOnResponse } from '@plone/react-router';
import {
  CallbackCard,
  CHOOSE_LOGIN_PATH,
  endpoints,
  expiryFromToken,
  readCallback,
} from '@plone-collective/identity-core';
import type { CallbackFailure } from '@plone-collective/identity-core';
import { data, redirect, useLoaderData } from 'react-router';
import type { LoaderFunctionArgs } from 'react-router';

import AuroraIdentityUI from '../components/IdentityUI/AuroraIdentityUI';
import {
  backendUrl,
  flowCookie,
  flowCookieHeaders,
  relayFlowCookie,
} from '../lib/backend';
import { afterSignIn, IDENTITIES_PATH } from '../lib/paths';

import './callback.css';

/** What the page draws when the sign-in did not complete. */
interface CallbackData {
  failure: CallbackFailure;
}

/**
 * Answer with the page, explaining why the sign-in did not complete.
 *
 * @param failure Why.
 * @param from The backend's answer, whose flow cookie to pass on.
 * @returns The page's data.
 */
function failed(failure: CallbackFailure, from?: Response) {
  return data<CallbackData>(
    { failure },
    from ? { headers: flowCookieHeaders(from) } : undefined,
  );
}

export async function loader({ request }: LoaderFunctionArgs) {
  const parsed = readCallback(new URL(request.url).search);
  if (parsed.kind === 'error') {
    // `unavailable` is the start route's own; anything else is the
    // provider's refusal, whatever word it used for it.
    return failed(parsed.error === 'unavailable' ? 'unavailable' : 'refused');
  }
  if (parsed.kind === 'none') {
    return failed('incomplete');
  }

  const [path, body] =
    parsed.kind === 'magic-link'
      ? [endpoints.magicLinkConfirm(), { token: parsed.token }]
      : [
          endpoints.callback(),
          { provider: parsed.provider, code: parsed.code, state: parsed.state },
        ];

  const headers = new Headers({
    Accept: 'application/json',
    'Content-Type': 'application/json',
  });
  const flow = flowCookie(request.headers.get('Cookie'));
  if (flow) {
    headers.set('Cookie', flow);
  }
  // Somebody already signed in is linking another identity to the account
  // they are signed in to, and the backend needs to know which account.
  const session = await getAuthFromRequest(request);
  if (session) {
    headers.set('Authorization', `Bearer ${session}`);
  }

  let answer: Response;
  try {
    answer = await fetch(
      backendUrl(config.settings.apiPath, request.url, path),
      { method: 'POST', headers, body: JSON.stringify(body) },
    );
  } catch {
    return failed('unavailable');
  }
  if (!answer.ok) {
    // Expired, replayed, from another session: every refusal reads the same,
    // because telling them apart helps nobody but somebody probing.
    return failed('invalid', answer);
  }

  const result = (await answer.json()) as {
    token?: string;
    came_from?: string;
    linked?: unknown;
  };
  if (result.token) {
    const expires = expiryFromToken(result.token) ?? undefined;
    return setAuthOnResponse(
      relayFlowCookie(answer, redirect(afterSignIn(result.came_from))),
      result.token,
      { expires },
    );
  }
  if (result.linked) {
    // The identity is linked to the account already signed in. The answer
    // names no `came_from`, so back to the page linking is done from, which
    // lists the new identity: where the Volto add-on goes too.
    return relayFlowCookie(answer, redirect(IDENTITIES_PATH));
  }
  return failed('invalid', answer);
}

export default function Callback() {
  const { failure } = useLoaderData<CallbackData>();
  return (
    <AuroraIdentityUI>
      <main className="identity-callback-page">
        {/* The options, not the plain login page: with one provider that would
            start the same sign-in again, and fail the same way. */}
        <CallbackCard failure={failure} retryHref={CHOOSE_LOGIN_PATH} />
      </main>
    </AuroraIdentityUI>
  );
}

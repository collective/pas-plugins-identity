/**
 * Asking a signed-in user whether an application may use their account.
 *
 * Where the authorization server sends the browser when it has a question
 * for the user: `server_consent_url`, with the authorization request as the
 * query string. `identity-core`'s `ConsentPanel` asks it, in the site's own
 * look, which is the reason the question is asked here rather than on the
 * server's standalone page.
 *
 * The loader describes the request through `@oauth-consent`, as the user.
 * The answer is not sent from here: it is a navigation back to the
 * authorization endpoint (`answerUrl`), because the endpoint answers it with
 * a redirect to the application, and it is the browser that has to get
 * there.
 * @module routes/oauth-consent
 */
import { useState } from 'react';
import { redirect, useLoaderData } from 'react-router';
import type { LoaderFunctionArgs, MetaFunction } from 'react-router';
import { getAuthFromRequest } from '@plone/react-router';
import { Container } from '@plone/quanta';
import {
  answerUrl,
  ConsentPanel,
  endpoints,
} from '@plone-collective/identity-core';
import type { ConsentRequest } from '@plone-collective/identity-core';

import AuroraIdentityUI from '../components/IdentityUI/AuroraIdentityUI';
import { callBackend } from '../lib/api';

export async function loader({ request }: LoaderFunctionArgs) {
  const url = new URL(request.url);
  const token = await getAuthFromRequest(request);
  if (!token) {
    // Back here after signing in, with the request still in the query
    // string: it is the whole of what is being asked.
    throw redirect(
      `/login?came_from=${encodeURIComponent(`${url.pathname}${url.search}`)}`,
    );
  }
  // The query string handed on as it came: an authorization request is
  // compared byte for byte further down the flow.
  const answer = await callBackend(request, endpoints.consent(url.search), {
    token,
  });
  return {
    consent: answer.ok ? ((await answer.json()) as ConsentRequest) : null,
  };
}

// One step of somebody's sign-in, reached with their authorization request
// in the URL: not a page to index.
export const meta: MetaFunction = () => [
  { name: 'robots', content: 'noindex, nofollow' },
];

export default function OAuthConsent() {
  const { consent } = useLoaderData<typeof loader>();
  // Set once the browser is on its way out: a second click must not send a
  // second answer to a request already decided.
  const [answering, setAnswering] = useState(false);

  return (
    <AuroraIdentityUI>
      <Container width="default" className="identity-consent-page">
        <ConsentPanel
          request={consent}
          loading={false}
          error={consent ? undefined : true}
          answering={answering}
          onAnswer={(allow) => {
            if (!consent) {
              return;
            }
            setAnswering(true);
            window.location.assign(answerUrl(consent, allow));
          }}
        />
      </Container>
    </AuroraIdentityUI>
  );
}

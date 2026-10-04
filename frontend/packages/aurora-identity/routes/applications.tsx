/**
 * The applications the signed-in user has authorized.
 *
 * `identity-core`'s `ApplicationsPanel`, the one the Volto add-on shows. The
 * loader reads `@oauth-grants` as the user; the action withdraws one. The
 * page asks before a withdrawal, because it signs the application out
 * everywhere, and says once it has.
 *
 * Only a site running the authorization server has the endpoint. Elsewhere
 * the panel reports that the list could not be loaded, and the entry leading
 * here is not offered (see `lib/features`).
 * @module routes/applications
 */
import { useState } from 'react';
import { useFetcher, useLoaderData } from 'react-router';
import type { ActionFunctionArgs, LoaderFunctionArgs } from 'react-router';
import {
  redirectWithClearedCookie,
  requireAuthCookie,
} from '@plone/react-router';
import { Container } from '@plone/quanta';
import {
  applicationsMessages,
  ApplicationsPanel,
  ConfirmDialog,
  endpoints,
  useIdentityUI,
} from '@plone-collective/identity-core';
import type { OAuthGrants } from '@plone-collective/identity-core';

import AuroraIdentityUI from '../components/IdentityUI/AuroraIdentityUI';
import { callBackend } from '../lib/api';
import { APPLICATIONS_PATH } from '../lib/paths';

/** What the action answers with. */
interface ActionResult {
  /** The client withdrawn. */
  withdrawn?: string;
  /** The backend's status, when it refused. */
  error?: number;
}

/**
 * Send somebody whose session the backend no longer accepts to sign in.
 *
 * @returns The redirect, to throw.
 */
function signInAgain() {
  return redirectWithClearedCookie(
    `/login?came_from=${encodeURIComponent(APPLICATIONS_PATH)}`,
  );
}

export async function loader({ request }: LoaderFunctionArgs) {
  const token = await requireAuthCookie(request);
  const answer = await callBackend(request, endpoints.grants(), { token });
  if (answer.status === 401) {
    throw await signInAgain();
  }
  return {
    grants: answer.ok ? ((await answer.json()) as OAuthGrants) : null,
  };
}

export async function action({ request }: ActionFunctionArgs) {
  const token = await requireAuthCookie(request);
  const clientId = String((await request.formData()).get('client') ?? '');
  let answer: Response;
  try {
    answer = await callBackend(request, endpoints.grant(clientId), {
      method: 'DELETE',
      token,
    });
  } catch {
    return { error: 502 } satisfies ActionResult;
  }
  if (answer.status === 401) {
    throw await signInAgain();
  }
  return (
    answer.ok ? { withdrawn: clientId } : { error: answer.status }
  ) satisfies ActionResult;
}

/**
 * The page inside the add-on's translations: the panel, the question before
 * a withdrawal, and what came of it.
 *
 * @returns The page.
 */
function Page() {
  const { t } = useIdentityUI();
  const { grants } = useLoaderData<typeof loader>();
  const fetcher = useFetcher<ActionResult>();
  const [selected, setSelected] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<string | null>(null);

  const titleOf = (clientId: string) =>
    grants?.items.find((item) => item.client_id === clientId)?.title ||
    clientId;
  const result = fetcher.data;

  return (
    <Container width="default" className="identity-applications-page">
      <h1 className="documentFirstHeading">{t(applicationsMessages.title)}</h1>
      {fetcher.state === 'idle' && result?.withdrawn ? (
        <p className="identity-note" role="status">
          {t(applicationsMessages.withdrawn)}
        </p>
      ) : null}
      {fetcher.state === 'idle' && result?.error ? (
        <p className="identity-error" role="alert">
          {t(applicationsMessages.failed)}
        </p>
      ) : null}
      <ApplicationsPanel
        grants={grants}
        loading={false}
        error={grants ? undefined : true}
        selected={selected}
        withdrawing={
          fetcher.state === 'idle'
            ? null
            : String(fetcher.formData?.get('client') ?? '')
        }
        onSelect={setSelected}
        onWithdraw={setConfirming}
      />
      <ConfirmDialog
        isOpen={confirming !== null}
        title={confirming ? titleOf(confirming) : ''}
        message={t(applicationsMessages.confirm, {
          client: confirming ? titleOf(confirming) : '',
        })}
        confirmLabel={t(applicationsMessages.withdraw)}
        onCancel={() => setConfirming(null)}
        onConfirm={() => {
          if (confirming) {
            fetcher.submit({ client: confirming }, { method: 'post' });
            setSelected(null);
          }
          setConfirming(null);
        }}
      />
    </Container>
  );
}

export default function Applications() {
  return (
    <AuroraIdentityUI>
      <Page />
    </AuroraIdentityUI>
  );
}

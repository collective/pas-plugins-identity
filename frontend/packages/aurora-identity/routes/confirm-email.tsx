/**
 * Asking which verified address stands for the signed-in user.
 *
 * `identity-core`'s `ConfirmEmailCard`, the card the Volto add-on shows. The
 * loader reads the profile as the user; the action sends the answer to
 * `@confirm-email`, which answers with the profile as it is afterwards. The
 * profile gate sends a user here when that answer is all their profile is
 * waiting for, and lets them go once it is given.
 * @module routes/confirm-email
 */
import { useFetcher, useLoaderData } from 'react-router';
import type { ActionFunctionArgs, LoaderFunctionArgs } from 'react-router';
import {
  redirectWithClearedCookie,
  requireAuthCookie,
} from '@plone/react-router';
import { Container } from '@plone/quanta';
import { ConfirmEmailCard, endpoints } from '@plone-collective/identity-core';
import type { MyProfile, ProfileEmail } from '@plone-collective/identity-core';

import AuroraIdentityUI from '../components/IdentityUI/AuroraIdentityUI';
import { callBackend } from '../lib/api';
import { CONFIRM_EMAIL_PATH } from '../lib/paths';

/** What the action answers with. */
interface ActionResult {
  /** The address the backend recorded. */
  recorded?: string;
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
    `/login?came_from=${encodeURIComponent(CONFIRM_EMAIL_PATH)}`,
  );
}

export async function loader({ request }: LoaderFunctionArgs) {
  const token = await requireAuthCookie(request);
  const answer = await callBackend(request, endpoints.myProfile(), { token });
  if (answer.status === 401) {
    throw await signInAgain();
  }
  const me: Partial<MyProfile> = answer.ok ? await answer.json() : {};
  return {
    asking: Boolean(me.confirm_email),
    emails: me.emails ?? [],
  };
}

export async function action({ request }: ActionFunctionArgs) {
  const token = await requireAuthCookie(request);
  const form = await request.formData();
  let answer: Response;
  try {
    answer = await callBackend(request, endpoints.confirmEmail(), {
      method: 'POST',
      token,
      body: { email: String(form.get('address') ?? '') },
    });
  } catch {
    return { error: 502 } satisfies ActionResult;
  }
  if (answer.status === 401) {
    throw await signInAgain();
  }
  if (!answer.ok) {
    return { error: answer.status } satisfies ActionResult;
  }
  const me = (await answer.json()) as Partial<MyProfile>;
  return {
    recorded: (me.emails ?? []).find((entry) => entry.preferred)?.address,
  } satisfies ActionResult;
}

export default function ConfirmEmail() {
  const { asking, emails } = useLoaderData<typeof loader>();
  const fetcher = useFetcher<ActionResult>();
  const recorded = fetcher.data?.recorded;

  return (
    <AuroraIdentityUI>
      <Container width="default" className="identity-confirm-email-page">
        <ConfirmEmailCard
          status={recorded ? 'done' : asking ? 'asking' : 'nothing'}
          emails={emails as ProfileEmail[]}
          recorded={recorded}
          busy={fetcher.state !== 'idle'}
          failed={Boolean(fetcher.data?.error)}
          onConfirm={(address) =>
            fetcher.submit({ address }, { method: 'post' })
          }
        />
      </Container>
    </AuroraIdentityUI>
  );
}

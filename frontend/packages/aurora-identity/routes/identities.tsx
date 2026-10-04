/**
 * The signed-in user's sign-in methods.
 *
 * `identity-core`'s `IdentitiesList`, the panel the Volto add-on shows: the
 * providers linked to the account, the ones that could still be, and the
 * addresses on the profile. The loader reads all three from the backend, as
 * the user; the action carries out whatever the panel asks for.
 *
 * Linking another provider is a sign-in with it, so it leaves the site: the
 * action answers with a redirect to the provider, carrying the flow cookie,
 * and the provider sends the browser back to the callback route, which sees
 * the session and links instead of signing in.
 * @module routes/identities
 */
import { useFetcher, useLoaderData, redirect } from 'react-router';
import type { ActionFunctionArgs, LoaderFunctionArgs } from 'react-router';
import {
  redirectWithClearedCookie,
  requireAuthCookie,
} from '@plone/react-router';
import { Container } from '@plone/quanta';
import {
  defineMessages,
  EMAIL_DRIVER,
  endpoints,
  IdentitiesList,
  useIdentityUI,
} from '@plone-collective/identity-core';
import type {
  Identity,
  LoginProvider,
  MyProfile,
  ProfileEmail,
} from '@plone-collective/identity-core';

import AuroraIdentityUI from '../components/IdentityUI/AuroraIdentityUI';
import { callBackend } from '../lib/api';
import { relayFlowCookie } from '../lib/backend';
import { IDENTITIES_PATH } from '../lib/paths';

const messages = defineMessages({
  title: { id: 'Sign-in methods', defaultMessage: 'Sign-in methods' },
});

/** What the action answers the panel with, when it does not redirect. */
export interface ActionResult {
  intent: string;
  /** Whether a confirmation mail went out. */
  sent?: boolean;
  /** The backend's status, when it refused. */
  error?: number;
}

/** `@identities`, expanded with the login page's own listing. */
interface IdentitiesListing {
  items?: Identity[];
  available?: LoginProvider[];
  '@components'?: { 'login-providers'?: { items?: LoginProvider[] } };
}

/**
 * Send somebody whose session the backend no longer accepts to sign in.
 *
 * Aurora's cookie outlives a token the backend has stopped honouring, so the
 * cookie is cleared on the way, and the login page brings them back here.
 *
 * @returns The redirect, to throw.
 */
function signInAgain() {
  return redirectWithClearedCookie(
    `/login?came_from=${encodeURIComponent(IDENTITIES_PATH)}`,
  );
}

export async function loader({ request }: LoaderFunctionArgs) {
  const token = await requireAuthCookie(request);
  const [listing, profile] = await Promise.all([
    callBackend(request, endpoints.identities(true), { token }),
    callBackend(request, endpoints.myProfile(), { token }),
  ]);
  if (listing.status === 401) {
    throw await signInAgain();
  }
  const mine: IdentitiesListing = listing.ok ? await listing.json() : {};
  const me: Partial<MyProfile> = profile.ok ? await profile.json() : {};
  return {
    identities: mine.items ?? [],
    available: mine.available ?? [],
    loginProviders: mine['@components']?.['login-providers']?.items ?? [],
    emails: me.emails ?? [],
    // Absolute, and naming Aurora: the backend was asked through the
    // virtual-host URL.
    profile: me.profile ?? null,
    failed: !listing.ok,
  };
}

/**
 * Move one address to the front of the profile's list.
 *
 * The whole list is sent: `emails` is a field, and a PATCH carrying one entry
 * would replace the list with it. The current list is read again here rather
 * than taken from the browser, so the reorder applies to what the profile
 * holds now.
 *
 * @param request The browser's request.
 * @param token The session.
 * @param address The address to prefer.
 * @returns The backend's answer.
 */
async function preferEmail(
  request: Request,
  token: string,
  address: string,
): Promise<Response> {
  const answer = await callBackend(request, endpoints.myProfile(), { token });
  if (!answer.ok) {
    return answer;
  }
  const me = (await answer.json()) as Partial<MyProfile>;
  if (!me.profile) {
    return new Response(null, { status: 404 });
  }
  const addresses = (me.emails ?? []).map((entry) => entry.address);
  return callBackend(request, new URL(me.profile).pathname, {
    method: 'PATCH',
    token,
    body: {
      emails: [address, ...addresses.filter((each) => each !== address)],
    },
  });
}

export async function action({ request }: ActionFunctionArgs) {
  const token = await requireAuthCookie(request);
  const form = await request.formData();
  const intent = String(form.get('intent') ?? '');
  const field = (name: string) => String(form.get(name) ?? '');

  let answer: Response;
  try {
    if (intent === 'link' || intent === 'verify') {
      // Both start a link: with a provider, by signing in there; with the
      // email provider, by mailing a link to one of the profile's addresses.
      answer = await callBackend(request, endpoints.identities(), {
        method: 'POST',
        token,
        body:
          intent === 'verify'
            ? {
                provider: EMAIL_DRIVER,
                came_from: IDENTITIES_PATH,
                email: field('address'),
              }
            : { provider: field('provider'), came_from: IDENTITIES_PATH },
      });
    } else if (intent === 'unlink') {
      answer = await callBackend(
        request,
        endpoints.identity(field('provider'), field('subject')),
        { method: 'DELETE', token },
      );
    } else if (intent === 'prefer') {
      answer = await preferEmail(request, token, field('address'));
    } else {
      throw new Response('Unknown form', { status: 400 });
    }
  } catch (error) {
    if (error instanceof Response) {
      throw error;
    }
    return { intent, error: 502 } satisfies ActionResult;
  }

  if (answer.status === 401) {
    throw await signInAgain();
  }
  if (!answer.ok) {
    return { intent, error: answer.status } satisfies ActionResult;
  }
  if (intent === 'link') {
    const { authorize_url: authorizeUrl } = (await answer.json()) as {
      authorize_url?: string;
    };
    // The provider's address, from its discovery document. Only a web
    // address is followed.
    if (!authorizeUrl || !/^https?:\/\//.test(authorizeUrl)) {
      return { intent, error: 502 } satisfies ActionResult;
    }
    return relayFlowCookie(answer, redirect(authorizeUrl));
  }
  if (intent === 'verify') {
    return { intent, sent: true } satisfies ActionResult;
  }
  return { intent } satisfies ActionResult;
}

/**
 * The page's heading, translated the way the panel under it is.
 *
 * @returns The heading.
 */
function Heading() {
  const { t } = useIdentityUI();
  return <h1 className="documentFirstHeading">{t(messages.title)}</h1>;
}

export default function Identities() {
  const data = useLoaderData<typeof loader>();
  const fetcher = useFetcher<ActionResult>();
  const submit = (fields: Record<string, string>) =>
    fetcher.submit(fields, { method: 'post' });
  const result = fetcher.data;

  return (
    <AuroraIdentityUI>
      <Container width="default" className="identity-identities-page">
        <Heading />
        <IdentitiesList
          identities={data.identities}
          available={data.available}
          emails={data.emails as ProfileEmail[]}
          // Whether the login page offers signing in with a link: the panel
          // stops claiming a verified address does that when it does not.
          canSignInWithLink={data.loginProviders.some(
            (provider) => provider.driver === EMAIL_DRIVER,
          )}
          // Aurora's edit form for the profile, `/@@edit` and its path.
          profileEditHref={
            data.profile ? `/@@edit${new URL(data.profile).pathname}` : null
          }
          loading={false}
          busy={fetcher.state !== 'idle'}
          error={data.failed || result?.error ? true : undefined}
          emailSent={Boolean(result?.intent === 'verify' && result.sent)}
          onLink={(provider) =>
            submit({ intent: 'link', provider: provider.id })
          }
          onVerifyEmail={(address) => submit({ intent: 'verify', address })}
          onPreferEmail={(address) => submit({ intent: 'prefer', address })}
          onUnlink={(identity) =>
            submit({
              intent: 'unlink',
              provider: identity.provider,
              subject: identity.subject,
            })
          }
        />
      </Container>
    </AuroraIdentityUI>
  );
}

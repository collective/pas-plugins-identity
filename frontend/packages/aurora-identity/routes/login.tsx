/**
 * The login page, in place of Aurora's own.
 *
 * Aurora's page draws a password form and leaves a slot inside it; this
 * add-on's ways in -- a button per provider, the magic link, the password --
 * are three forms, and cannot live inside another one. So the add-on renders
 * `/login` with this file instead (see `lib/routes`), keeping Aurora's frame
 * around it: the close link, the logo and hero slots, the heading. What sits
 * in the frame is `identity-core`'s `LoginForm`, the one the Volto add-on
 * shows, so both frontends offer the same choices the same way.
 *
 * The providers are listed by the loader, so they are in the page as it is
 * served. Both forms post to the action below, which calls the backend from
 * the server, the way the callback route does.
 * @module routes/login
 */
import { useState } from 'react';
import config from '@plone/registry';
import {
  redirectIfLoggedInLoader,
  setAuthOnResponse,
} from '@plone/react-router';
import { Link } from '@plone/quanta';
import CloseSVG from '@plone/icons/svg/close.svg?react';
import SlotRenderer from '@plone/layout/slots/SlotRenderer';
import {
  asksToChoose,
  endpoints,
  expiryFromToken,
  isBackendView,
  LoginForm,
  returnUrl,
} from '@plone-collective/identity-core';
import type { LoginProvider } from '@plone-collective/identity-core';
import type { GetSlotArgs } from '@plone/types';
import { useTranslation } from 'react-i18next';
import {
  redirect,
  redirectDocument,
  useFetcher,
  useLoaderData,
  useLocation,
  useRouteLoaderData,
} from 'react-router';
import type { ActionFunctionArgs, LoaderFunctionArgs } from 'react-router';

import AuroraIdentityUI from '../components/IdentityUI/AuroraIdentityUI';
import { backendUrl } from '../lib/backend';
import { afterSignIn, startPath } from '../lib/paths';
import { loginSettings } from '../lib/settings';
import type { IdentitySettings } from '../lib/settings';

import './login.css';

/** What the action answers a form with, when it does not redirect. */
interface ActionResult {
  intent: 'magic-link' | 'password';
  /** Whether a magic link was sent. */
  sent?: boolean;
  /** The backend's status, when it refused. */
  error?: number;
}

/**
 * Ask the backend for the providers the login page offers.
 *
 * @param request The request for the page.
 * @returns The providers, or none when the backend could not say.
 */
async function listProviders(request: Request): Promise<LoginProvider[]> {
  try {
    const answer = await fetch(
      backendUrl(
        config.settings.apiPath,
        request.url,
        endpoints.loginProviders(),
      ),
      { headers: { Accept: 'application/json' } },
    );
    if (!answer.ok) {
      return [];
    }
    const listing = (await answer.json()) as { items?: LoginProvider[] };
    return listing.items ?? [];
  } catch {
    // No providers is a page with the password form on it: an unreachable
    // backend costs the buttons, not the way in.
    return [];
  }
}

/**
 * Send a form's fields to the backend as JSON.
 *
 * @param request The request the form came in.
 * @param path The endpoint.
 * @param body The fields.
 * @returns The backend's answer.
 */
function post(request: Request, path: string, body: object) {
  return fetch(backendUrl(config.settings.apiPath, request.url, path), {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
}

export async function loader(args: LoaderFunctionArgs) {
  // Aurora's own login page sends somebody signed in home, and so does this.
  await redirectIfLoggedInLoader(args);
  const { request } = args;
  const settings = loginSettings(
    (config.settings as { identity?: Partial<IdentitySettings> }).identity,
    process.env,
  );
  return {
    providers: await listProviders(request),
    showPloneLogin: settings.showPloneLogin,
    // `?choose` is somebody asking for the options -- among them the
    // callback page, after a sign-in failed. Starting the sole provider
    // again would only fail again.
    redirectToSoleProvider:
      settings.redirectToSoleProvider &&
      !asksToChoose(new URL(request.url).search),
  };
}

export async function action({ request }: ActionFunctionArgs) {
  const form = await request.formData();
  const intent = String(form.get('intent') ?? '');

  if (intent === 'magic-link') {
    try {
      const answer = await post(request, endpoints.magicLink(), {
        email: String(form.get('email') ?? ''),
      });
      return answer.ok
        ? ({ intent, sent: true } satisfies ActionResult)
        : ({ intent, error: answer.status } satisfies ActionResult);
    } catch {
      return { intent, error: 502 } satisfies ActionResult;
    }
  }

  if (intent === 'password') {
    let answer: Response;
    try {
      answer = await post(request, endpoints.login(), {
        login: String(form.get('login') ?? ''),
        password: String(form.get('password') ?? ''),
      });
    } catch {
      return { intent, error: 502 } satisfies ActionResult;
    }
    const { token } = answer.ok
      ? ((await answer.json()) as { token?: string })
      : {};
    if (!token) {
      return { intent, error: answer.status } satisfies ActionResult;
    }
    const target = afterSignIn(String(form.get('came_from') ?? ''));
    // A backend view -- the authorization endpoint resuming the request it
    // sent this visitor to sign in for -- is no route of this application,
    // so the browser loads it rather than the router navigating to it.
    return setAuthOnResponse(
      isBackendView(target) ? redirectDocument(target) : redirect(target),
      token,
      { expires: expiryFromToken(token) ?? undefined },
    );
  }

  throw new Response('Unknown form', { status: 400 });
}

export default function Login() {
  const { providers, showPloneLogin, redirectToSoleProvider } =
    useLoaderData<typeof loader>();
  const root = useRouteLoaderData('root') as
    | {
        content?: GetSlotArgs['content'];
        site?: Record<string, string | undefined>;
      }
    | undefined;
  const location = useLocation();
  const { t } = useTranslation();
  const magicLink = useFetcher<ActionResult>();
  const password = useFetcher<ActionResult>();
  const [starting, setStarting] = useState(false);
  const content = root?.content as GetSlotArgs['content'];
  const cameFrom = returnUrl(location.search, location.pathname);

  return (
    <AuroraIdentityUI>
      <main className="identity-login-page">
        <div className="identity-login-page__main">
          <Link
            className="identity-login-page__close"
            variant="icon"
            accent
            size="L"
            href="/"
            aria-label={t('cmsui.auth.returnToHome')}
            asButton
          >
            <CloseSVG />
          </Link>
          <div className="identity-login-page__header">
            <SlotRenderer
              name="loginLogo"
              content={content}
              location={location}
            />
            <h2 id="login-header">
              {t('cmsui.auth.signInTo', {
                site: root?.site?.['plone.site_title'] || 'Aurora',
              })}
            </h2>
          </div>
          <div className="identity-login-page__form">
            <LoginForm
              providers={providers}
              loading={false}
              starting={starting}
              magicLinkSent={Boolean(magicLink.data?.sent)}
              magicLinkLoading={magicLink.state !== 'idle'}
              magicLinkError={magicLink.data?.error}
              passwordLoading={password.state !== 'idle'}
              passwordError={password.data?.error}
              showPloneLogin={showPloneLogin}
              redirectToSoleProvider={redirectToSoleProvider}
              onSelectProvider={(provider) => {
                setStarting(true);
                // A whole-page navigation, not the router's: the start route
                // answers with a redirect to the provider, off this site.
                window.location.assign(
                  startPath(provider.id, cameFrom === '/' ? '' : cameFrom),
                );
              }}
              onSendMagicLink={(email) =>
                magicLink.submit(
                  { intent: 'magic-link', email },
                  { method: 'post' },
                )
              }
              onPasswordLogin={(login, secret) =>
                password.submit(
                  {
                    intent: 'password',
                    login,
                    password: secret,
                    came_from: cameFrom,
                  },
                  { method: 'post' },
                )
              }
            />
          </div>
        </div>
        <div className="identity-login-page__hero">
          <SlotRenderer
            name="loginHero"
            content={content}
            location={location}
          />
        </div>
      </main>
    </AuroraIdentityUI>
  );
}

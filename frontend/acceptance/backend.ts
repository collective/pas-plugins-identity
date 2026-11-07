/**
 * What the acceptance tests ask of the backend directly.
 *
 * The backend's acceptance server (`make acceptance-backend-start` from the
 * repository root): a site at `PLONE_API_PATH` with this add-on installed,
 * and a Manager at `PLONE_ADMIN`. Requests carry a token from `@login`,
 * because this add-on's authentication gate refuses Basic credentials on
 * its own endpoints.
 */
import type { BrowserContext } from '@playwright/test';

const SITE = process.env.PLONE_API_PATH ?? 'http://localhost:55001/plone';
const ADMIN = process.env.PLONE_ADMIN ?? 'admin:secret';

/** A member the tests create, with a password so they can sign in as them. */
export const MEMBER = {
  id: 'acceptance-member',
  password: 'acceptance-secret-153',
  fullname: 'Acceptance Member',
  emails: ['member@example.org', 'member.alias@example.org'],
};

/** Two providers, so the control panel has rows to list and reorder. */
export const PROVIDERS = [
  {
    id: 'acme',
    driver: 'oidc-generic',
    title: 'Acme',
    enabled: true,
    show_in_login: true,
    config: {
      issuer: 'https://acme.example.org',
      client_id: 'acceptance',
      // Never sent anywhere: the tests do not sign in through this provider.
      client_secret: 'acceptance',
      scope: ['openid', 'email'],
    },
  },
  {
    id: 'email',
    driver: 'email',
    title: 'Email',
    enabled: true,
    show_in_login: true,
    config: {},
  },
];

/**
 * A token for `user:password`, from `@login`.
 *
 * @param credentials `user:password`.
 * @returns The JSON Web Token the site issued.
 */
export async function tokenFor(credentials: string): Promise<string> {
  const [login, password] = credentials.split(':');
  const answer = await fetch(`${SITE}/@login`, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({ login, password }),
  });
  if (!answer.ok) {
    throw new Error(`Logging in as ${login} failed: ${answer.status}`);
  }
  return (await answer.json()).token;
}

/**
 * Call the site's REST API as the Manager.
 *
 * @param method The HTTP method.
 * @param path The path below the site, such as `/@users`.
 * @param body A JSON body, if any.
 * @returns The response.
 */
async function api(
  method: string,
  path: string,
  body?: unknown,
): Promise<Response> {
  const token = await tokenFor(ADMIN);
  return fetch(`${SITE}/++api++${path}`, {
    method,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

/**
 * Fail loudly when the backend refused a set-up step.
 *
 * @param answer The response.
 * @param what What was being done, for the message.
 */
async function check(answer: Response, what: string): Promise<void> {
  if (!answer.ok) {
    throw new Error(`${what} failed: ${answer.status} ${await answer.text()}`);
  }
}

/** Register {@link PROVIDERS}, replacing any a stopped run left behind. */
export async function addProviders(): Promise<void> {
  await removeProviders();
  for (const provider of PROVIDERS) {
    await check(
      await api('POST', '/@identity-providers', provider),
      `Adding provider ${provider.id}`,
    );
  }
}

/** Remove {@link PROVIDERS}. */
export async function removeProviders(): Promise<void> {
  for (const provider of PROVIDERS) {
    await api('DELETE', `/@identity-providers/${provider.id}`);
  }
}

/**
 * Create {@link MEMBER}, replacing one a stopped run left behind.
 *
 * Adding a user creates their Profile, which is where the addresses are
 * stored and edited.
 *
 * @returns The path of the member's Profile, below the site.
 */
export async function addMember(): Promise<string> {
  await removeMember();
  await check(
    await api('POST', '/@users', {
      username: MEMBER.id,
      email: MEMBER.emails[0],
      password: MEMBER.password,
      fullname: MEMBER.fullname,
    }),
    'Adding the member',
  );
  const search = await api(
    'GET',
    `/@search?portal_type=UserProfile&userid=${MEMBER.id}`,
  );
  await check(search, 'Finding the Profile');
  const [profile] = (await search.json()).items;
  if (!profile) {
    throw new Error(`No Profile was created for ${MEMBER.id}`);
  }
  const path = new URL(profile['@id']).pathname.replace(/^\/plone/, '');
  await check(
    await api('PATCH', path, { emails: MEMBER.emails }),
    'Storing the addresses',
  );
  return path;
}

/** Remove {@link MEMBER}, and their Profile with them. */
export async function removeMember(): Promise<void> {
  await api('DELETE', `/@users/${MEMBER.id}`);
}

/**
 * Sign the browser in, the way Volto keeps a session: its `auth_token`
 * cookie.
 *
 * @param context The browser context.
 * @param credentials `user:password`, the Manager by default.
 */
export async function signIn(
  context: BrowserContext,
  credentials: string = ADMIN,
): Promise<void> {
  const token = await tokenFor(credentials);
  const baseURL = process.env.BASE_URL ?? 'http://localhost:3000';
  await context.addCookies([
    { name: 'auth_token', value: token, url: baseURL },
  ]);
}

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

/** The layer the acceptance server runs, by the name its reset keywords take. */
const LAYER = 'pas.plugins.identity.testing.ACCEPTANCE_TESTING';

/**
 * Escape what XML reserves, for a value sent in an XML-RPC call.
 *
 * @param text The value.
 * @returns The escaped value.
 */
function xmlEscape(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

/**
 * Undo the escaping an XML-RPC response applies to its strings.
 *
 * @param text The escaped value.
 * @returns The value.
 */
function xmlUnescape(text: string): string {
  return text
    .replace(/&#(\d+);/g, (_, code: string) =>
      String.fromCodePoint(Number(code)),
    )
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&amp;/g, '&');
}

/**
 * Run one keyword of the site's Robot Framework remote library.
 *
 * The site serves the library at `RobotRemote`, speaking the remote protocol:
 * `run_keyword` takes a keyword's name and its arguments, and answers with a
 * status, an error and a return value.
 *
 * @param name The keyword, such as `remote_zodb_setup`.
 * @param args The keyword's arguments, as strings.
 * @returns The keyword's return value as text, empty when it returns nothing.
 * @throws Error when the keyword fails.
 */
async function keyword(name: string, args: string[] = []): Promise<string> {
  const values = args
    .map((arg) => `<value><string>${xmlEscape(arg)}</string></value>`)
    .join('');
  const call =
    '<?xml version="1.0"?><methodCall><methodName>run_keyword</methodName>' +
    '<params>' +
    `<param><value><string>${xmlEscape(name)}</string></value></param>` +
    `<param><value><array><data>${values}</data></array></value></param>` +
    '<param><value><struct/></value></param>' +
    '</params></methodCall>';
  const answer = await fetch(`${SITE}/RobotRemote`, {
    method: 'POST',
    headers: { 'Content-Type': 'text/xml' },
    body: call,
  });
  const xml = await answer.text();
  const status = /<name>status<\/name>\s*<value><string>([^<]*)<\/string>/.exec(
    xml,
  )?.[1];
  if (status !== 'PASS') {
    const error =
      /<name>error<\/name>\s*<value><string>([\s\S]*?)<\/string>/.exec(xml)?.[1];
    throw new Error(`${name} failed: ${xmlUnescape(error ?? '')}`);
  }
  const returned =
    /<name>return<\/name>\s*<value>([\s\S]*?)<\/value>\s*<\/member>/.exec(
      xml,
    )?.[1] ?? '';
  // A keyword answering with bytes -- a captured mail message is one -- comes
  // back as `<base64>`, which is the bytes themselves and not text to unescape.
  const binary = /^<base64>([\s\S]*)<\/base64>$/.exec(returned.trim());
  if (binary) {
    return Buffer.from(binary[1], 'base64').toString('utf-8');
  }
  return xmlUnescape(returned.replace(/^<(string|int)>|<\/(string|int)>$/g, ''));
}

/**
 * Put the site in the state the layer starts a test in.
 *
 * Every test calls this before it begins, and {@link stopSite} after it ends,
 * so no test sees what an earlier one made. It is the same pair the robot
 * server's own listener calls around each test.
 */
export async function startSite(): Promise<void> {
  await keyword('remote_zodb_setup', [LAYER]);
}

/** Discard what the test made, returning the site to the layer's state. */
export async function stopSite(): Promise<void> {
  await keyword('remote_zodb_teardown', [LAYER]);
}

/**
 * How many messages the site has sent since the test began.
 *
 * @returns The count.
 */
export async function sentMailCount(): Promise<number> {
  return Number(await keyword('get_the_total_amount_of_sent_emails'));
}

/**
 * The last message the site sent, as the mail server would have received it.
 *
 * @returns The message, headers and body.
 */
export async function lastSentMail(): Promise<string> {
  return keyword('get_the_last_sent_email');
}

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

/** Where Dex answers, and the issuer its discovery document names. */
export const DEX_ISSUER = process.env.DEX_ISSUER ?? 'http://127.0.0.1:5556/dex';

/**
 * The person Dex signs in, from `backend/tests/_resources/dex/config.yaml`.
 * Test credentials of a throwaway Dex, not secrets.
 */
export const DEX_USER = {
  email: 'erico@plone.org',
  password: 'plone-test-password',
};

/**
 * Two providers backed by Dex, one per static client in its configuration.
 * Linking a second sign-in method needs a second provider; Dex serves both
 * from one issuer, and they differ by provider id.
 */
export const DEX_PROVIDERS = [
  { id: 'dex', title: 'Dex', client_id: 'plone', secret: 'plone-secret' },
  {
    id: 'dex-second',
    title: 'Dex second',
    client_id: 'plone-second',
    secret: 'plone-second-secret',
  },
];

/**
 * Register Dex-backed providers in the site a test has just been given.
 *
 * @param issuer The issuer to register them with, Dex's by default.
 * @param providers Which providers, {@link DEX_PROVIDERS} by default.
 */
export async function addDexProviders(
  issuer: string = DEX_ISSUER,
  providers: typeof DEX_PROVIDERS = DEX_PROVIDERS,
): Promise<void> {
  for (const provider of providers) {
    await check(
      await api('POST', '/@identity-providers', {
        id: provider.id,
        driver: 'oidc-generic',
        title: provider.title,
        enabled: true,
        show_in_login: true,
        config: {
          issuer,
          client_id: provider.client_id,
          client_secret: provider.secret,
          scope: ['openid', 'email', 'profile'],
        },
      }),
      `Adding provider ${provider.id}`,
    );
  }
}

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

/**
 * Register {@link PROVIDERS} in the site a test has just been given.
 *
 * The site is reset after each test, so there is nothing to remove first.
 */
export async function addProviders(): Promise<void> {
  for (const provider of PROVIDERS) {
    await check(
      await api('POST', '/@identity-providers', provider),
      `Adding provider ${provider.id}`,
    );
  }
}

/**
 * Register only the email provider, which verifying an address goes through.
 */
export async function addEmailProvider(): Promise<void> {
  const email = PROVIDERS.find((provider) => provider.driver === 'email');
  await check(
    await api('POST', '/@identity-providers', email),
    'Adding the email provider',
  );
}

/**
 * Append an address to a user's Profile, unverified, as typing it in does.
 *
 * @param userid The Profile's owner.
 * @param address The address to add.
 */
export async function addProfileAddress(
  userid: string,
  address: string,
): Promise<void> {
  const path = `/identity-profiles/${userid}`;
  const profile = await api('GET', path);
  await check(profile, `Reading the Profile of ${userid}`);
  const emails: string[] = (await profile.json()).emails ?? [];
  await check(
    await api('PATCH', path, { emails: [...emails, address] }),
    `Adding ${address} to the Profile of ${userid}`,
  );
}

/** A relying party of the site's authorization server, for the consent tests. */
export const CLIENT = {
  id: 'acceptance-app',
  title: 'Acceptance app',
  // Volto answers it with its not-found page, which is all a test needs: the
  // code or the error is in the address the browser was sent to.
  redirect_uri: 'http://localhost:3000/oauth-client-callback',
};

/**
 * Register {@link CLIENT} as a public client, so PKCE alone proves it.
 */
export async function addClient(): Promise<void> {
  await check(
    await api('POST', '/@identity-clients', {
      client_id: CLIENT.id,
      title: CLIENT.title,
      redirect_uris: [CLIENT.redirect_uri],
      scope: ['openid', 'profile', 'email'],
      public: true,
    }),
    `Registering the client ${CLIENT.id}`,
  );
}

/**
 * The first link in a captured message.
 *
 * The message arrives quoted-printable, with soft line breaks and `=3D` for
 * `=`, so both are undone before the link is read.
 *
 * @param message The raw message, as the mail host captured it.
 * @returns The first link in the body.
 */
export function linkIn(message: string): string {
  const text = message.replace(/=\r?\n/g, '').replace(/=3D/g, '=');
  const link = /https?:\/\/[^\s"<>]+/.exec(text);
  if (!link) {
    throw new Error(`No link in the message: ${message}`);
  }
  return link[0];
}

/**
 * Sign somebody in by magic link, over the API, as their browser would.
 *
 * Needs the `email` provider, which {@link addProviders} registers. An
 * address nobody has yet gets a new account.
 *
 * @param email The address to sign in with.
 * @returns The userid the sign-in authenticated.
 */
export async function signInByMagicLink(email: string): Promise<string> {
  const headers = {
    Accept: 'application/json',
    'Content-Type': 'application/json',
  };
  await check(
    await fetch(`${SITE}/++api++/@magic-link`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ email }),
    }),
    `Asking for a link for ${email}`,
  );
  const token = new URL(linkIn(await lastSentMail())).searchParams.get(
    'magic_link',
  );
  const answer = await fetch(`${SITE}/++api++/@magic-link-confirm`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ token }),
  });
  await check(answer, `Confirming the link for ${email}`);
  const session = (await answer.json()).token as string;
  return JSON.parse(
    Buffer.from(session.split('.')[1], 'base64url').toString('utf-8'),
  ).sub;
}

/**
 * Create a group, with users and groups as its direct members.
 *
 * Groups are content here, so the group also gets a page: its path is
 * looked up and returned.
 *
 * @param id The group's id.
 * @param members User and group ids to add to it.
 * @returns The path of the group's page, below the site.
 */
export async function addGroup(
  id: string,
  members: string[] = [],
): Promise<string> {
  await check(
    await api('POST', '/@groups', { groupname: id, title: id }),
    `Adding the group ${id}`,
  );
  if (members.length) {
    await check(
      await api('PATCH', `/@groups/${id}`, {
        users: Object.fromEntries(members.map((member) => [member, true])),
      }),
      `Adding members to ${id}`,
    );
  }
  const search = await api('GET', `/@search?portal_type=UserGroup&getId=${id}`);
  await check(search, `Finding the page of ${id}`);
  const [group] = (await search.json()).items;
  if (!group) {
    throw new Error(`No page was created for the group ${id}`);
  }
  return new URL(group['@id']).pathname.replace(/^\/plone/, '');
}

/**
 * Create users with a password, by id.
 *
 * @param ids The users' ids, which are also their login names.
 */
export async function addUsers(ids: string[]): Promise<void> {
  for (const id of ids) {
    await check(
      await api('POST', '/@users', {
        username: id,
        email: `${id}@example.org`,
        password: `${id}-secret-155`,
        fullname: `User ${id}`,
      }),
      `Adding the user ${id}`,
    );
  }
}

/**
 * Set the site's language, which Volto's interface follows.
 *
 * Volto switches its interface to the language of the content it shows, so
 * a cookie or an `Accept-Language` header alone does not change it on a site
 * whose content is in English.
 *
 * @param language A Plone language code, such as `pt-br`.
 */
export async function setSiteLanguage(language: string): Promise<void> {
  await check(
    await api('PATCH', '/@registry', {
      'plone.default_language': language,
      'plone.available_languages': [language],
    }),
    `Setting the site language to ${language}`,
  );
}

/**
 * Name the fields a profile must hold before it counts as complete.
 *
 * Only profiles created afterwards are judged by it: the catalog column that
 * records what a profile misses is written when the profile is, and a change
 * here fires no event.
 *
 * @param fields Profile field names, such as `location`.
 */
export async function requireProfileFields(fields: string[]): Promise<void> {
  await check(
    await api('PATCH', '/@registry', {
      'pas.plugins.identity.required_profile_fields': fields,
    }),
    `Requiring the profile fields ${fields.join(', ')}`,
  );
}

/**
 * Create a published page holding the given blocks, in order.
 *
 * @param id The page's id, below the site root.
 * @param blocks The blocks, each with its `@type`.
 * @returns The page's path, below the site.
 */
export async function addPage(
  id: string,
  blocks: Record<string, unknown>[],
): Promise<string> {
  const ids = blocks.map((_, index) => `block-${index}`);
  await check(
    await api('POST', '/', {
      '@type': 'Document',
      id,
      title: id,
      blocks: Object.fromEntries(ids.map((key, i) => [key, blocks[i]])),
      blocks_layout: { items: ids },
    }),
    `Adding the page ${id}`,
  );
  await check(
    await api('POST', `/${id}/@workflow/publish`),
    `Publishing the page ${id}`,
  );
  return `/${id}`;
}

/**
 * Create {@link MEMBER} in the site a test has just been given.
 *
 * Adding a user creates their Profile, which is where the addresses are
 * stored and edited.
 *
 * @returns The path of the member's Profile, below the site.
 */
export async function addMember(): Promise<string> {
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

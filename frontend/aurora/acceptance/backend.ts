/**
 * What the acceptance tests ask of the backend directly.
 *
 * The backend's acceptance server, `pas.plugins.identity.testing.
 * ACCEPTANCE_TESTING`: a site at `PLONE_API_PATH`, a Manager at
 * `PLONE_ADMIN`, and `collective.MockMailHost`, which keeps every message
 * the site sends instead of sending it. The server's Robot Framework remote
 * library reads them back.
 */
const SITE = process.env.PLONE_API_PATH ?? 'http://localhost:55001/plone';
const ADMIN = process.env.PLONE_ADMIN ?? 'admin:secret';

const headers = {
  Accept: 'application/json',
  'Content-Type': 'application/json',
  Authorization: `Basic ${Buffer.from(ADMIN).toString('base64')}`,
};

/** The email "provider", which sends magic links. */
export const EMAIL_PROVIDER = {
  id: 'email',
  driver: 'email',
  title: 'Email',
  enabled: true,
  show_in_login: true,
  config: {},
};

/**
 * A second provider, served by the same Dex through its second client.
 *
 * `plone-second` in `backend/tests/_resources/dex/config.yaml`, the one the
 * backend's own linking tests use: one Dex user, two providers, so linking a
 * second identity to an account needs no second identity provider.
 */
export const SECOND_DEX = {
  id: 'dex-second',
  driver: 'oidc-generic',
  title: 'Dex (second)',
  enabled: true,
  show_in_login: true,
  config: {
    issuer: process.env.DEX_ISSUER ?? 'http://127.0.0.1:5556/dex',
    client_id: 'plone-second',
    // Dex's static test client, not a secret: see the Dex configuration.
    client_secret: 'plone-second-secret',
    scope: ['openid', 'email', 'profile'],
  },
};

/**
 * Stop offering a provider.
 *
 * @param id The provider.
 */
export async function removeProvider(id: string): Promise<void> {
  await fetch(`${SITE}/++api++/@identity-providers/${id}`, {
    method: 'DELETE',
    headers,
  });
}

/**
 * Offer a provider, for one test file's run.
 *
 * Every other test sees Dex alone, so a test adding one removes it after
 * itself, with `removeProvider`.
 *
 * @param provider The provider's record.
 */
export async function addProvider(provider: { id: string }): Promise<void> {
  // One left behind by a run that stopped before its cleanup.
  await removeProvider(provider.id);
  const answer = await fetch(`${SITE}/++api++/@identity-providers`, {
    method: 'POST',
    headers,
    body: JSON.stringify(provider),
  });
  if (!answer.ok) {
    throw new Error(
      `Adding the ${provider.id} provider failed: ${answer.status} ${await answer.text()}`,
    );
  }
}

/**
 * The last message the site sent, as MockMailHost kept it.
 *
 * Robot Framework's remote protocol is XML-RPC, which answers with the
 * message base64-encoded; inside it, the body is quoted-printable.
 *
 * @returns The message, decoded, or `''` when none was sent.
 */
async function lastSentEmail(): Promise<string> {
  const answer = await fetch(`${SITE}/RobotRemote`, {
    method: 'POST',
    headers: { 'Content-Type': 'text/xml' },
    body:
      '<?xml version="1.0"?><methodCall><methodName>run_keyword</methodName>' +
      '<params><param><value><string>get_the_last_sent_email</string>' +
      '</value></param><param><value><array><data/></array></value></param>' +
      '</params></methodCall>',
  });
  const xml = await answer.text();
  const encoded = xml.match(
    /<name>return<\/name>\s*<value><base64>([^<]*)<\/base64>/,
  )?.[1];
  if (!encoded) {
    return '';
  }
  const message = Buffer.from(encoded, 'base64').toString('utf-8');
  // Only the body is quoted-printable. Decoding the headers too would read
  // the `?=` closing an encoded subject as a soft line break.
  const split = message.search(/\r?\n\r?\n/);
  const [head, body] =
    split < 0 ? [message, ''] : [message.slice(0, split), message.slice(split)];
  return (
    head +
    body
      .replace(/=\r?\n/g, '')
      .replace(/=([0-9A-F]{2})/g, (_, hex: string) =>
        String.fromCharCode(parseInt(hex, 16)),
      )
  );
}

/**
 * The magic link in the last message the site sent, if it went to `address`.
 *
 * @param address The address the link was asked for.
 * @returns The link, or `null` when the last message is not one for it.
 */
export async function lastMagicLink(address: string): Promise<string | null> {
  const message = await lastSentEmail();
  if (!new RegExp(`^To: ${address}\\r?$`, 'm').test(message)) {
    return null;
  }
  return message.match(/https?:\/\/\S*[?&]magic_link=[\w.-]+/)?.[0] ?? null;
}

/** The registry record naming the fields a profile must carry. */
const REQUIRED_FIELDS = 'pas.plugins.identity.required_profile_fields';

/**
 * Name the fields a profile must carry to count as complete.
 *
 * The backend evaluates it at every sign-in and every edit of a profile, so
 * a change reaches a profile at its owner's next sign-in.
 *
 * @param fields The field names; none to require only what the type does.
 */
export async function requireProfileFields(fields: string[]): Promise<void> {
  const answer = await fetch(`${SITE}/++api++/@registry`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify({ [REQUIRED_FIELDS]: fields }),
  });
  if (!answer.ok) {
    throw new Error(
      `Setting the required fields failed: ${answer.status} ${await answer.text()}`,
    );
  }
}

/**
 * The path of the profile carrying an address, if there is one yet.
 *
 * @param address The address.
 * @returns The profile's path below the site, or null.
 */
export async function profileOf(address: string): Promise<string | null> {
  const search = await fetch(
    `${SITE}/++api++/@search?portal_type=UserProfile&b_size=100`,
    { headers },
  );
  const { items } = (await search.json()) as { items: { '@id': string }[] };
  for (const item of items) {
    const path = new URL(item['@id']).pathname.replace(
      new URL(SITE).pathname,
      '',
    );
    const profile = await fetch(`${SITE}/++api++${path}`, { headers });
    const { emails } = (await profile.json()) as { emails?: string[] };
    if (emails?.includes(address)) {
      return path;
    }
  }
  return null;
}

/**
 * Edit a profile, as an administrator.
 *
 * @param path The profile's path below the site.
 * @param fields The fields to set.
 */
export async function editProfile(
  path: string,
  fields: Record<string, unknown>,
): Promise<void> {
  const answer = await fetch(`${SITE}/++api++${path}`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify(fields),
  });
  if (!answer.ok) {
    throw new Error(
      `Editing ${path} failed: ${answer.status} ${await answer.text()}`,
    );
  }
}

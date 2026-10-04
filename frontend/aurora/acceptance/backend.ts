/**
 * What the acceptance tests ask of the backend, and of its mailbox, directly.
 *
 * The backend's acceptance server: a site at `PLONE_API_PATH` and a Manager
 * at `PLONE_ADMIN`. Its mail goes to Mailpit, which `make acceptance-mail-start`
 * starts: SMTP on `MAILPIT_SMTP_PORT`, and the messages over HTTP at
 * `MAILPIT_URL`.
 */
const SITE = process.env.PLONE_API_PATH ?? 'http://localhost:55001/plone';
const ADMIN = process.env.PLONE_ADMIN ?? 'admin:secret';
const MAILPIT_URL = process.env.MAILPIT_URL ?? 'http://localhost:8025';
const MAILPIT_SMTP_PORT = Number(process.env.MAILPIT_SMTP_PORT ?? 1025);

const headers = {
  Accept: 'application/json',
  'Content-Type': 'application/json',
  Authorization: `Basic ${Buffer.from(ADMIN).toString('base64')}`,
};

/** The email "provider", which sends magic links. */
const EMAIL_PROVIDER = {
  id: 'email',
  driver: 'email',
  title: 'Email',
  enabled: true,
  show_in_login: true,
  config: {},
};

/**
 * Offer magic links on the login page.
 *
 * The acceptance site has no sender address, without which Plone refuses to
 * send any mail at all, and no mail server. This gives it both first: an
 * address, and Mailpit.
 */
export async function addEmailProvider(): Promise<void> {
  const registry = await fetch(`${SITE}/++api++/@registry`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify({
      'plone.email_from_address': 'noreply@example.com',
      'plone.email_from_name': 'Acceptance tests',
      'plone.smtp_host': 'localhost',
      'plone.smtp_port': MAILPIT_SMTP_PORT,
    }),
  });
  if (!registry.ok) {
    throw new Error(
      `Configuring mail failed: ${registry.status} ${await registry.text()}`,
    );
  }
  // One left behind by a run that stopped before its cleanup.
  await removeEmailProvider();
  const answer = await fetch(`${SITE}/++api++/@identity-providers`, {
    method: 'POST',
    headers,
    body: JSON.stringify(EMAIL_PROVIDER),
  });
  if (!answer.ok) {
    throw new Error(
      `Adding the email provider failed: ${answer.status} ${await answer.text()}`,
    );
  }
}

/** Stop offering them, so the other tests see Dex alone. */
export async function removeEmailProvider(): Promise<void> {
  await fetch(`${SITE}/++api++/@identity-providers/${EMAIL_PROVIDER.id}`, {
    method: 'DELETE',
    headers,
  });
}

/**
 * The magic link in the last message sent to an address.
 *
 * @param address The address.
 * @returns The link, or `null` when no message to it has one.
 */
export async function lastMagicLink(address: string): Promise<string | null> {
  const search = await fetch(
    `${MAILPIT_URL}/api/v1/search?query=${encodeURIComponent(`to:${address}`)}&limit=1`,
  );
  const { messages } = (await search.json()) as {
    messages: { ID: string }[];
  };
  if (!messages.length) {
    return null;
  }
  const message = await fetch(
    `${MAILPIT_URL}/api/v1/message/${messages[0].ID}`,
  );
  const { Text } = (await message.json()) as { Text: string };
  return Text.match(/https?:\/\/\S*[?&]magic_link=[\w.-]+/)?.[0] ?? null;
}

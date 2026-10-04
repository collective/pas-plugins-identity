/**
 * Register the Dex provider on the acceptance backend.
 *
 * The backend's acceptance server starts with an empty site, and Dex's static
 * client is `backend/tests/_resources/dex/config.yaml`'s: the one the
 * backend's own flow tests sign in with. Run once per backend start; a
 * provider already there is left as it is.
 *
 * Environment:
 *
 * - `PLONE_API_PATH`: the site, `http://localhost:55001/plone` by default.
 * - `PLONE_ADMIN`: `user:password` of a Manager, the acceptance server's
 *   `admin:secret` by default.
 * - `DEX_ISSUER`: `http://127.0.0.1:5556/dex` by default, the issuer Dex's
 *   configuration publishes.
 */
const site = process.env.PLONE_API_PATH ?? 'http://localhost:55001/plone';
const admin = process.env.PLONE_ADMIN ?? 'admin:secret';
const issuer = process.env.DEX_ISSUER ?? 'http://127.0.0.1:5556/dex';

const headers = {
  Accept: 'application/json',
  'Content-Type': 'application/json',
  Authorization: `Basic ${Buffer.from(admin).toString('base64')}`,
};
const providers = `${site}/++api++/@identity-providers`;

const existing = await fetch(`${providers}/dex`, { headers });
if (existing.ok) {
  console.log('The Dex provider is already registered.');
  process.exit(0);
}

const answer = await fetch(providers, {
  method: 'POST',
  headers,
  body: JSON.stringify({
    id: 'dex',
    driver: 'oidc-generic',
    title: 'Dex',
    enabled: true,
    show_in_login: true,
    config: {
      issuer,
      client_id: 'plone',
      // Dex's static test client, not a secret: see the Dex configuration.
      client_secret: 'plone-secret',
      scope: ['openid', 'email', 'profile'],
    },
  }),
});
if (!answer.ok) {
  console.error(
    `Registering the Dex provider failed: ${answer.status} ${await answer.text()}`,
  );
  process.exit(1);
}
console.log('Registered the Dex provider.');

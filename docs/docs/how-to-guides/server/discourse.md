---
myst:
  html_meta:
    "description": "Let a Discourse forum sign its users in against a Plone site running the server layer."
    "property=og:description": "Let a Discourse forum sign its users in against a Plone site running the server layer."
    "property=og:title": "Client recipe: Discourse"
---

(how-to-client-discourse)=

# Discourse

Let a Discourse forum sign its users in with accounts from your Plone site,
using the OpenID Connect plugin that ships with Discourse.

```{note}
Verified on 2026-09-24.
```

The examples use `https://id.example.org` as the issuer and
`https://forum.example.org` as the forum.

## 1. Register the client

Follow {doc}`/how-to-guides/server/register-an-oauth-client` with:

| Field | Value |
|---|---|
| Redirect URI | `https://forum.example.org/auth/oidc/callback` |
| Grant | Authorization code |
| Scope | `openid`, `profile`, `email` |
| Secret | Yes. Discourse is a confidential client |

Capture the client secret from the response. It is shown once.

## 2. Configure Discourse

<!-- source: backend/src/pas/plugins/identity/server/discovery.py, metadata -->
<!-- source: backend/src/pas/plugins/identity/server/browser/token.py, _exchange -->
<!-- source: backend/src/pas/plugins/identity/server/grants/codes.py, check_challenge -->

As an administrator, open `/admin/config/login-and-authentication/oidc` on the
forum, or search the site settings for `openid_connect`. Set each setting, in
the order the page lists them:

| Setting | Value |
|---|---|
| {guilabel}`OpenID Connect enabled` | on |
| {guilabel}`OpenID Connect discovery document` | `https://id.example.org/.well-known/openid-configuration` |
| {guilabel}`OpenID Connect client ID` | The client ID from step 1 |
| {guilabel}`OpenID Connect client secret` | The client secret from step 1 |
| {guilabel}`OpenID Connect rp initiated logout` | off. This server has no `end_session_endpoint` |
| {guilabel}`OpenID Connect rp initiated logout redirect` | empty |
| {guilabel}`OpenID Connect rp initiated logout include client ID` | off |
| {guilabel}`OpenID Connect allow association change` | on while existing users move over, then off |
| {guilabel}`OpenID Connect overrides email` | on to keep each forum address in step with your site at every sign-in; off to let people keep a different address on the forum |
| {guilabel}`OpenID Connect authorize scope` | `openid profile email` |
| {guilabel}`OpenID Connect verbose logging` | on while you test, then off |
| {guilabel}`OpenID Connect token scope` | empty. This server takes the scope from the authorization, and ignores one sent to the token endpoint |
| {guilabel}`OpenID Connect error redirects` | empty |
| {guilabel}`OpenID Connect authorize parameters` | empty |
| {guilabel}`OpenID Connect claims` | empty. This server releases claims by scope |
| {guilabel}`OpenID Connect match by email` | on |
| {guilabel}`OpenID Connect groups claim` | `groups`, or empty to leave groups out |
| {guilabel}`OpenID Connect user field mappings` | empty, or map `website` or `description` onto a Discourse user field |
| {guilabel}`OpenID Connect use pkce` | off. This recipe has not been run with it on; this server accepts the `S256` method only |
| {guilabel}`OpenID Connect mtls client cert` | empty. This server authenticates a client by its secret |
| {guilabel}`OpenID Connect mtls client key` | empty |
| {guilabel}`OpenID Connect mtls client key passcode` | empty |

Discourse reads the endpoints and the token endpoint authentication from the
discovery document.

## Verify

1. Sign out of Discourse and open its login dialog. It offers the OpenID
   Connect button.
2. Choosing it takes you to your Plone site, which asks you to approve the
   forum once.
3. You come back to Discourse signed in. A first sign-in offers the account
   creation form, filled in from `preferred_username` and `name`.

## Known quirks

<!-- source: backend/src/pas/plugins/identity/server/discovery.py, metadata -->

- **Matching by email depends on `email_verified`.** Discourse attaches a
  sign-in to an existing forum account with the same address, unless
  `email_verified` is `false`. This server sends `true` only for an address it
  holds as verified, so a user whose address is unverified here gets a new
  forum account instead. See {doc}`/concepts/email-verification`.
- **Existing users can link by hand.** With
  {guilabel}`OpenID Connect allow association change` on, a signed-in user can
  connect their forum account from their preferences, whatever their address.
  It also lets them disconnect it, so turn it off once everybody has moved.
- **Username and name are suggestions.** Discourse uses `preferred_username`
  and `name` only when it creates an account.
- **Logout ends only the forum session.** This server has no
  `end_session_endpoint`, so leave
  {guilabel}`OpenID Connect rp initiated logout` off.
- **Groups:** with {guilabel}`OpenID Connect groups claim` set to `groups`, Discourse
  records the Plone groups as associated groups, and a Discourse group can be
  tied to one for automatic membership. The claim carries only the groups your
  site releases. See {doc}`/reference/claims`.

## Related

- {doc}`/how-to-guides/server/index`—the other client recipes, and what every client needs
- {doc}`/how-to-guides/server/register-an-oauth-client`—restricting the forum to some groups
- {doc}`/reference/claims`—what the `profile` and `email` scopes release

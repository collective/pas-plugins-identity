---
myst:
  html_meta:
    "description": "Step-by-step recipes for connecting other applications to a Plone site running the server layer."
    "property=og:description": "Step-by-step recipes for connecting other applications to a Plone site running the server layer."
    "property=og:title": "Act as an identity provider"
---

(how-to-clients)=

# Act as an identity provider

Let other applications sign their users in with accounts from your Plone site.
This needs the `[server]` layer.

Registering a client, and everything else on this side, is described once in
{doc}`register-an-oauth-client`. Each recipe below says which values one
application needs, with the same shape: what to register here, what to type
into the application, and how to tell that it worked.

## Pick a recipe

| Application | Recipe |
|---|---|
| Another Plone site | {doc}`/how-to-guides/server/another-plone-site` |
| Discourse | {doc}`/how-to-guides/server/discourse` |
| Portainer | {doc}`/how-to-guides/server/portainer` |
| Matomo, with the RebelOIDC plugin | {doc}`/how-to-guides/server/matomo` |
| GitLab, self-managed | {doc}`/how-to-guides/server/gitlab` |
| oauth2-proxy | {doc}`/how-to-guides/server/oauth2-proxy` |

For anything not listed, register a client and give the application the
discovery document. An application that reads one needs nothing else.

## Before any recipe works

<!-- source: backend/src/pas/plugins/identity/server/discovery.py, metadata -->
<!-- source: docker-compose.demo.yml, rt-idp-oauth and rt-idp-login -->

1. Set the issuer, as {doc}`/how-to-guides/server/register-an-oauth-client` describes. Until it is
   set, the discovery document answers `503 server_not_configured`.

2. Route these paths on the issuer's host to the Plone **backend**, not to the
   Volto frontend:

   | Path | Serves |
   |---|---|
   | `/.well-known` | The discovery document |
   | `/@@oauth-authorize` | Authorization, and the consent screen |
   | `/@@oauth-token` | Tokens |
   | `/@@oauth-userinfo` | The claims about the signed-in user |
   | `/@@oauth-jwks` | The public signing keys |
   | `/acl_users/credentials_cookie_auth` | Where the authorize view sends a visitor who is not signed in, on the way to `/login` |

   A rule that sends `/++api++` to the backend does not carry them. See
   {doc}`/concepts/federation` for why, and `docker-compose.demo.yml` in the
   repository for a working set of Traefik rules.

## What every client is given

<!-- source: backend/src/pas/plugins/identity/server/discovery.py, metadata -->
<!-- source: backend/src/pas/plugins/identity/server/browser/token.py, _authenticate_client -->

An application that reads the discovery document needs only these:

| Value | Is |
|---|---|
| Client ID | Minted when you register the client |
| Client secret | Shown **once**, in the response that registers the client |
| Discovery document | `<issuer>/.well-known/openid-configuration` |

An application that asks for each endpoint instead gets them from the same
document, under these names:

| Discovery field | Endpoint |
|---|---|
| `authorization_endpoint` | `<issuer>/@@oauth-authorize` |
| `token_endpoint` | `<issuer>/@@oauth-token` |
| `userinfo_endpoint` | `<issuer>/@@oauth-userinfo` |
| `jwks_uri` | `<issuer>/@@oauth-jwks` |

Every client works within the same limits:

| Limit | Is |
|---|---|
| Response type | `code`, and nothing else |
| Client authentication | Either `client_secret_basic` or `client_secret_post` for a client with a secret; `none` for a public client |
| PKCE | `S256` only. Required for a public client |
| Logout URL | None. This server has no `end_session_endpoint` |

`sub` is the Plone user id, and it never changes. `preferred_username` is the
login name, which can. Where an application asks which claim identifies a
user, `sub` is the safer answer. See {doc}`/reference/claims` for every claim
each scope releases.

## Decide who may sign in

By default, anybody with an account on your site may sign in to every client.
To keep an application to some people, give its client **Allowed groups**. See
{ref}`how-to-restrict-a-client`.

## Verification status

Application user interfaces change, and a recipe that claims to be current when
it is not is worse than one that says it is unverified.

| Recipe | Application-side steps |
|---|---|
| {doc}`/how-to-guides/server/another-plone-site` | verified against the demo stack, 2026-09-05 |
| {doc}`/how-to-guides/server/discourse` | verified, 2026-09-24 |
| {doc}`/how-to-guides/server/portainer` | verified, 2026-09-24 |
| {doc}`/how-to-guides/server/matomo` | verified, 2026-09-28 |
| {doc}`/how-to-guides/server/gitlab` | **not verified** |
| {doc}`/how-to-guides/server/oauth2-proxy` | **not verified** |

An unverified recipe keeps its application-side steps short and links to the
application's own documentation, which is the part that stays current. The
Plone side of every recipe is read from this package's source.

## Related

- {doc}`/how-to-guides/server/register-an-oauth-client`—registering, amending, and revoking a client
- {doc}`/reference/claims`—every scope and the claims it releases
- {doc}`/reference/endpoints`—the server layer's full surface
- {doc}`/how-to-guides/providers/index`—the other direction, signing in *to* this site

```{toctree}
:maxdepth: 1
:hidden: true

register-an-oauth-client
another-plone-site
discourse
portainer
matomo
gitlab
oauth2-proxy
```

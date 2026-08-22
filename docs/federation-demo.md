# The federation demo

Two full Plone sites, in a browser, one signing users in against the other.

| Host | Site | Layers |
|---|---|---|
| `http://id.localhost` | The identity provider | `core` + `profile` + `server` |
| `http://plone.localhost` | The relying party | `core`, with the generic OIDC driver |

```bash
make demo-stack-start
```

Then open **http://plone.localhost**, choose *Sign in with the demo IdP*, and
authenticate as **`alice`** / **`alice-demo-password`**.

Alice exists only on `id.localhost`. The account you end up with on
`plone.localhost` was created by the login itself.

`make demo-stack-rm` removes the containers and both databases.

## What it demonstrates

The relying party was configured with an **issuer URL and a client credential,
and nothing else**. Every endpoint it uses, and the keys it verifies the
`id_token` with, came out of `http://id.localhost/.well-known/openid-configuration`
at runtime. Nothing about the provider is special-cased anywhere.

Things worth doing once it is up:

- **Sign in again.** The consent screen appears once per user and client. The
  second time you are redirected straight back.
- **Look at `/identities` on the relying party.** The federated identity is
  listed there, and can be unlinked.
- **Look at `/controlpanel/identity-clients` on the provider**, as `admin`.
  The demo client is registered there; its secret is not, and cannot be
  recovered.
- **Fetch the discovery document** — it is the whole contract:
  ```bash
  curl -s http://id.localhost/.well-known/openid-configuration | jq
  ```

## Why this is not the Gate S3 stack

`backend/tests/federation/docker-compose.yml` runs the same two roles
headless, with published ports, and is asserted by `pytest -m docker`. It has
to run in CI, so it gets no browser and no real provider.

This stack exists for what CI cannot do: a real browser, real cookies between
sibling `.localhost` hosts, Volto's real login and callback routes. Both are
driven from the same `identitydemo` package; they differ only in the four
URLs, which come from the environment.

## The three things that go wrong

**The issuer is compared as a string, never parsed.** `http://id.localhost` and
`http://id.localhost/` are different issuers, and so are the same host on
different ports. `DEMO_IDP_URL` in `docker-compose.demo.yml` is what the
provider publishes and what the relying party expects; if a login fails with a
mismatched `iss`, that is the variable.

**One URL has to resolve in two places.** The browser is redirected to
`http://id.localhost`, and the relying party's *container* fetches discovery
from the same URL. Traefik carries a network alias for both hostnames so the
name means the same thing inside and outside. There is no second, internal URL
to configure — deliberately, because a provider only answers to the name it
publishes.

**The OAuth endpoints need their own Traefik router.** They are Zope views on
the site root, not REST API services, so the `/++api++` rule does not carry
them and without `rt-idp-oauth` they reach the Volto frontend instead. This is
what makes configuring the issuer, rather than deriving it from the portal
URL, load-bearing rather than fussy.

## Why the provider shows a Classic login form

`http://id.localhost/login` serves Plone's own login form, not Volto's
provider picker, and that is deliberate rather than an oversight in the
routing.

`@@oauth-authorize` is a browser view. When an anonymous visitor reaches it,
Plone's challenge machinery sends them to the cookie-auth plugin's
`require_login`, which lands on `/login`, and whatever authenticates them
there has to leave them authenticated **for a subsequent browser view** —
which means the `__ac` cookie the Classic form sets. Volto's login returns a
JWT, which authenticates the REST API and nothing else, so a visitor who
signed in through Volto's picker would arrive back at `@@oauth-authorize`
still anonymous and be challenged again.

So the provider's `/login`, `/logged_in`, `/login_form` and the cookie-auth
challenge path are all routed to the backend, at a higher Traefik priority
than the frontend's catch-all host rule. The relying party has no such router:
there, `/login` is Volto's picker, which is the whole point.

Everything else on `id.localhost` is Volto as usual.

## Credentials

Every credential in this stack is a fixed literal in
`backend/demo/src/identitydemo/settings.py`, and therefore public.

| What | Value |
|---|---|
| Demo user, on the provider | `alice` / `alice-demo-password` |
| Zope admin, both sites | `admin` / `admin` |
| OAuth client | `demo-rp` / `demo-secret-not-for-any-real-site` |

The `identitydemo` package is never published to PyPI, is not installed into
the production image at all, and both of its GenericSetup profiles refuse to
install unless `IDENTITY_DEMO` is set in the environment.

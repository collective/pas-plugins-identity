---
myst:
  html_meta:
    "description": "Why the issuer is configured rather than derived, and what a Plone site has to grow to be an identity provider."
    "property=og:description": "Why the issuer is configured rather than derived, and what a Plone site has to grow to be an identity provider."
    "property=og:title": "About federation"
---

(concepts-federation)=

# About federation

A Plone site running the `[server]` layer can be the provider that another Plone site signs in against.
{doc}`/tutorials/federation-demo` runs exactly that, in a browser, in a few minutes.

This page is about the parts of it that are not obvious, and the three things that go wrong.

## The issuer is a string, and it is compared as one

A relying party fetches the discovery document from a URL, reads the `issuer` field inside it, and compares the two byte for byte.
If they differ, it refuses the document.

That comparison is in the specification, and it is what stops an attacker serving a document that claims to speak for somebody else.
It is also unforgiving in ways that read as bugs.

`http://id.localhost` and `http://id.localhost/` are different issuers.
So is the same host on a different port.
So is `https` where the document says `http`.

This is why the issuer is a registry setting, `pas.plugins.identity.server_issuer`, and why the server builds every URL in the discovery document from it rather than from `portal_url`.

Deriving endpoints from `portal_url` would make that byte comparison depend on a proxy header, a virtual host, or a trailing slash.
It would work in development and fail behind a load balancer, which is the worst possible place for it to fail.

If a sign-in fails with a mismatched `iss`, that setting is where to look first.

## One URL has to resolve in two places

The browser is redirected to the provider's issuer URL.
The relying party's own process fetches the discovery document from the same URL.

Those are two different network positions, and they have to agree on what the name means.
In the demo stack, Traefik carries a network alias so the hostname resolves the same way inside a container and outside it.

There is deliberately no second, internal URL to configure.
A provider answers only to the name it publishes, because that name is the issuer, and the issuer is what everything is checked against.
An internal alias that differed would be a second issuer, and the comparison above would fail.

## OAuth endpoints are not REST API services

`@@oauth-authorize` and its siblings are Zope browser views on the site root.

They are not `plone.restapi` services, so a routing rule that sends `/++api++` to the backend does not carry them.
Without a router of their own, they reach the Volto frontend instead, which knows nothing about them.

This is what makes configuring the issuer load-bearing rather than fussy.
The issuer determines the URLs in the discovery document, and those URLs have to be routed to the backend by a rule that was written for them specifically.

## How a Plone provider authenticates its own users

This is the part that had to be built, and the reason is a genuine mismatch between two things Plone already had.

`@@oauth-authorize` is a browser view, so the visitor arriving at it has to be a Zope principal.
A Volto sign-in does not produce one.
Volto keeps its token in an `auth_token` cookie and sends it as an `Authorization` header on its own API calls, and `plone.restapi`'s JWT plugin is the only reader of that header.

Measured on a running site: the authorize view with only the cookie answers as anonymous, and the same request with the token in a header authenticates.
Two halves that each work, unable to talk to each other.

So the `[server]` layer installs a PAS plugin that reads that cookie, for the authorization endpoint and nothing else.
Everywhere else the site behaves exactly as `plone.restapi` left it, because widening the reader would mean every request in the site now accepts a credential from a cookie, which is a different security posture than the one the site was configured with.

There was a second problem in the same area.
This add-on's `/login` route replaces Volto's, and it used to offer providers and the magic link only.
An identity provider has no providers of its own, so it showed "no sign-in options" and no way in at all.
The password form is back, controlled by `RAZZLE_IDENTITY_SHOW_PLONE_LOGIN`.

```{note}
`RAZZLE_` variables are substituted into the browser bundle when the frontend is built.
Setting one at runtime reaches the Node process and never the browser, so the two demo frontends build two images rather than sharing one.
```

## Groups cross, but only as far as you let them

A Plone provider releases a `groups` claim, and a relying party can map it onto local groups.
Neither half assumes the other.

The provider states a fact: these are the groups this person is in over here.
It has no idea what they mean anywhere else, and it never says what they should grant.

The relying party decides.
It starts with an empty map, so a peer's groups grant nothing at all until somebody says which of them mean something on this site.
A provider group with no row grants nothing and is never created here, which matters because a group name is whatever the far end's directory happens to call it: minting local groups from it would let anyone who can name a group over there create one here.

Two sites in a federation do not have the same groups just because they run the same package.
That is why the `plone-identity` driver ships an empty group map even though it knows the peer releases the claim.

### Revocation is the hard half

Adding a membership is easy; taking one back is where federated group membership differs from local group membership.
A membership revoked at the provider has to stop granting here, and nobody is going to notice that by hand, so every sign-in reconciles.

A reconciliation that simply wrote what the provider said would also erase every group an administrator granted locally, and every group a second provider granted, silently, on the next sign-in.

So each identity records what its own provider granted.
A sign-in adds what is newly granted and removes only what that same provider granted before.
A group granted by hand is never touched, and two providers cannot revoke each other's grants.

One consequence is worth stating: clearing a group map does not take its grants back.
Clearing is at least as likely to mean that the map is being rewritten as that every grant should be revoked, so a provider with an empty map touches no membership at all.

## Two stacks, on purpose

The repository has two federation setups, and they are not redundant.

`backend/tests/federation/docker-compose.yml` runs the same two roles headless, with published ports, asserted by `pytest -m docker`.
It has to run in CI, so it gets no browser and no real provider.

The demo stack exists for what CI cannot do.
A real browser, real cookies between sibling `.localhost` hosts, and Volto's real login and callback routes.

Both are driven from the same `identitydemo` package, and they differ only in four URLs that come from the environment.

## Where to go next

-   {doc}`/tutorials/federation-demo` to run it.
-   {doc}`/reference/claims` for what a Plone provider releases.
-   {doc}`/how-to-guides/register-an-oauth-client` to register a relying party of your own.

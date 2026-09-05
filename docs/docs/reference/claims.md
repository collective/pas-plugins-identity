---
myst:
  html_meta:
    "description": "Endpoints, scopes, and claims released when a Plone site acts as an authorization server."
    "property=og:description": "Endpoints, scopes, and claims released when a Plone site acts as an authorization server."
    "property=og:title": "Claims released by the server layer"
---

(reference-claims)=

# Claims released by the server layer

What this site tells a relying party about a user when it acts as an
authorization server, and what a relying party may rely on.

Published only where the `pas.plugins.identity.server:default` profile has been
applied.

```{note}
This page is about claims going **out**. For the normalized shape a driver
produces from a provider's claims coming **in**, see {doc}`events`.
```

## Client and key endpoints

Every client and key endpoint is bound to the `[server]` browser layer, so a site
that never applied the server profile does not publish them at all, and all of
them require `Manage portal`. They are listed with their exact sub-paths in
{doc}`endpoints`.

To use them, see {doc}`/how-to-guides/register-an-oauth-client`.

## Discovery

Point a conforming OpenID Connect client at the issuer URL and it needs nothing else.

```text
<issuer>/.well-known/openid-configuration
```

The document carries the endpoints, the `jwks_uri`, the signing algorithm, the supported scopes, and the claim list below.

Configure the issuer with `pas.plugins.identity.server_issuer`.
The package never derives it from the portal URL, and it builds every URL in the document from it.
See {doc}`/concepts/federation`.

```{note}
The document lists only what this server implements and the test suite exercises: one response type, one signing algorithm, and `S256` and nothing else for PKCE.
A client that trusts the document should not get a surprise.
```

## Learning who signed in

There are two ways, and they are not interchangeable.

`id_token`
:   Returned from the token endpoint when the `openid` scope was granted.
    A signed statement the relying party reads itself, carrying the claims its scopes released.
    It echoes the `nonce` from the authorization request verbatim.

The userinfo endpoint
:   For clients that prefer to ask.
    Present the access token as a Bearer credential and get the same claims back.
    The scope comes from the token, so a caller cannot widen what it was granted by asking for more here.

An access token is a credential, not an identity assertion.
A client that did not request `openid` gets no `id_token` at all.

## Scopes and the claims they release

| Scope | Claims |
| --- | --- |
| `openid` | None of its own. `sub` is not scope-gated and is always present. |
| `profile` | `name`, `preferred_username`, `website`, `picture`, `description`, `groups` |
| `email` | `email`, `email_verified` |
| `address` | `address` |

## Claim values

| Claim | Source | Notes |
| --- | --- | --- |
| `sub` | The Plone userid | A `uuid4` hex string on accounts this package created. Permanent, and never derived from an email address or a provider's subject. |
| `name` | `fullname` | |
| `preferred_username` | The login name | Not `sub`. A userid here is 32 hex characters and means nothing to a person. |
| `website` | `home_page` | |
| `email` | `email` | |
| `email_verified` | Computed | Sent only alongside an `email`. See {doc}`/concepts/email-verification`. |
| `address` | `location`, as `{"formatted": ...}` | Plone's `location` is one free-text line, which is what the OIDC `formatted` member is for. Splitting it into street, locality, and postal code would be guessing. |
| `picture` | The `@portrait` URL | Only when a portrait is actually stored. Built from the configured issuer, under `++api++`, because a relying party fetches it server to server. |
| `description` | `description` | Plone's biography. Not a registered OIDC claim. See below. |
| `groups` | The groups PAS resolved for the principal | Not a registered OIDC claim. Sorted, and never carrying `AuthenticatedUsers`. See below. |

A claim with no value is omitted, never sent as an empty string, so a relying party can tell an unknown value from a blank one.

## Where claims come from

Claims are read from Plone user properties.
They are not read from a `UserProfile` directly, even though that is usually where the values live.

The profile plugin serves a Profile's fields as a property sheet, through its `IPropertiesPlugin`.
So asking PAS for a property returns Profile-backed values for a user who has a Profile, and stock `mutable_properties` values for a userid that does not, with no branch in the server layer at all.

See {doc}`/concepts/layers` for the boundary that makes this necessary.

## The two claims that are not registered

`description` and `groups` have no registered OIDC claim to be. Both are released
under `profile` anyway, rather than under a private scope.

| Fact | Value |
|---|---|
| `AuthenticatedUsers` | Never released. |
| A user in no other group | The `groups` claim is omitted entirely, not sent as an empty list. |
| Order | Sorted. |
| Who receives it | Every client granted `profile`, whether it maps groups or not. |

```{warning}
`groups` is authorization data riding on a display scope. If your site's group
names are themselves sensitive, do not grant `profile` to a client you would not
grant the group list to.
```

There is no per-site claim extension. A field a site adds to its `UserProfile`
type has no claim to go in. See {doc}`/concepts/federation` for why.

```{note}
This page describes the contract as of the `[server]` layer's first release.
Adding a claim to an existing scope is a compatible change.
Moving one between scopes, or changing what `email_verified` asserts, is not.
```

## Related

- {doc}`endpoints`—the client, key and OAuth endpoints, with their sub-paths
- {doc}`events`—claims coming the other way, in from a provider
- {doc}`/concepts/federation`—why `description` and `groups` are released under `profile`
- {doc}`/how-to-guides/register-an-oauth-client`—putting a relying party on the other end

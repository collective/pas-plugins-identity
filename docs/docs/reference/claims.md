---
myst:
  html_meta:
    "description": "Endpoints, scopes, and claims released when a Plone site acts as an authorization server."
    "property=og:description": "Endpoints, scopes, and claims released when a Plone site acts as an authorization server."
    "property=og:title": "The claims contract"
---

(reference-claims)=

# The claims contract

This page describes the `[server]` layer.

When this site acts as an authorization server, this is what it tells a relying party about a user, and what a relying party may rely on.

## Client and key endpoints

Every endpoint here is bound to the `[server]` browser layer, so a site that never applied the server profile does not publish them at all.
All of them require `Manage portal`.

| Endpoint | Effect |
| --- | --- |
| `GET @identity-clients` | List registrations. |
| `GET @identity-clients/<id>` | Read one registration. |
| `POST @identity-clients` | Register a client. |
| `POST @identity-clients/<id>/rotate-secret` | Mint a fresh secret. |
| `PATCH @identity-clients/<id>` | Amend title, redirect URIs, grants, scope, service user, and enabled. |
| `DELETE @identity-clients/<id>` | Remove a client's registration. |
| `GET @identity-keys` | Describe the signing ring. |
| `POST @identity-keys/rotate` | Rotate the signing key. |

`client_id` and `auth_method` are not editable.
A `PATCH` naming any other unknown field is refused rather than ignored.

For how to use these, see {doc}`/how-to-guides/register-an-oauth-client`.

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
| `profile` | `name`, `preferred_username`, `website` |
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

A claim with no value is omitted, never sent as an empty string, so a relying party can tell an unknown value from a blank one.

## Where claims come from

Claims are read from Plone user properties.
They are not read from a `Profile`, even on a site that installs the `[profile]` extra.

The `[profile]` extra serves its fields as a property sheet, through its `IPropertiesPlugin`.
So asking PAS for a property returns Profile-backed values on a site that has that layer, and stock `mutable_properties` values on a site that does not, with no branch in the server layer and without the `[server]` layer importing the `[profile]` layer.

See {doc}`/concepts/layers` for the boundary that makes this necessary.

## What is not released

`description`, which is Plone's biography field, has no registered OIDC claim.
Putting it in a private claim would emit something no other implementation can read, so the server does not emit it at all.
The same goes for any field a site adds to its `Profile` type.

The extension point for that is a private scope releasing namespaced claims.
It is deliberately not built, because it needs a naming decision that should be made once, by somebody who has a second implementation to be compatible with.

```{note}
This page describes the contract as of the `[server]` layer's first release.
Adding a claim to an existing scope is a compatible change.
Moving one between scopes, or changing what `email_verified` asserts, is not.
```

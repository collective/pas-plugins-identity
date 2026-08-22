# The claims contract

*The `[server]` extra.*

When this site acts as an authorization server, this is what it will tell a
relying party about a user, and what a relying party may rely on.

## Where a relying party finds all this

Point a conforming OIDC client at the **issuer URL** and it needs nothing else.

`<issuer>/.well-known/openid-configuration` carries the endpoints, the
`jwks_uri`, the signing algorithm, the supported scopes and this claim list.
The issuer is configured (`pas.plugins.identity.server_issuer`), never derived
from the portal URL, and every URL in the document is built from it — because
a client compares the document's `issuer` field to the URL it fetched the
document from, byte for byte, and refuses the document if they differ. Deriving
endpoints from `portal_url` would make that comparison depend on a proxy
header, a virtual host or a trailing slash.

Two ways to learn who signed in, and they are not interchangeable:

- the **`id_token`**, returned from the token endpoint when the `openid` scope
  was granted. A signed *statement* the relying party reads itself, carrying
  the claims its scopes released. It echoes the `nonce` from the authorization
  request verbatim.
- the **userinfo endpoint**, for clients that prefer to ask. Present the access
  token as a Bearer credential and get the same claims back. The scope comes
  from the token, so a caller cannot widen what it was granted by asking for
  more here.

An access token is a *credential*, not an identity assertion. A client that did
not request `openid` gets no `id_token` at all.

```{note}
The document lists only what this server implements and the test suite
exercises — one response type, one signing algorithm, `S256` and nothing else
for PKCE. A client that trusts it should not get a surprise.
```

## Where claims come from

Claims are read from **Plone user properties**. Not from a `Profile`, even on
a site that installs the `[profile]` extra.

That matters more than it looks. The `[profile]` extra serves its fields *as a
property sheet*, through its `IPropertiesPlugin`. So asking PAS for a property
gets Profile-backed values on a site that has that layer and stock
`mutable_properties` values on a site that does not — with no branch here, and
without the `[server]` layer importing the `[profile]` layer, which the
package's import-linter contract forbids.

The consequence is worth stating for anyone planning a federation: the trip
from an upstream provider to a downstream Plone site *looks* like two mappings
and is one. A provider's claims land in this site's user properties (via the
core layer, or via a Profile if you have one). Those same properties are what
leave again as claims. Configure the first hop and the second follows.

## What each scope releases

| Scope | Claims |
| --- | --- |
| `openid` | none of its own — `sub` is not scope-gated and is always present |
| `profile` | `name`, `preferred_username`, `website` |
| `email` | `email`, `email_verified` |
| `address` | `address` |

And the values:

| Claim | Source | Notes |
| --- | --- | --- |
| `sub` | the Plone userid | `uuid4` hex on accounts this package created (D10). Permanent, and never derived from an email address or a provider's subject. |
| `name` | `fullname` | |
| `preferred_username` | the login name | Not `sub`. A userid here is 32 hex characters and means nothing to a person. |
| `website` | `home_page` | |
| `email` | `email` | |
| `email_verified` | computed — see below | Only sent alongside an `email`. |
| `address` | `location`, as `{"formatted": ...}` | Plone's `location` is one free-text line, which is what OIDC's `formatted` member is for. Splitting it into street, locality and postal code would be guessing. |

A claim with no value is **omitted**, never sent as an empty string, so a
relying party can tell "we do not know" from "it is blank".

## `email_verified` means this site verified it

This is the claim a relying party is most likely to auto-link accounts on, so
be clear about what it asserts.

`email_verified: true` means the user proved that address **to this site**,
with a magic link. It does not mean an upstream provider said the address was
verified.

That asymmetry is deliberate and matches what the core layer already does when
*consuming* identities: its opt-in auto-linking refuses a provider's
`email_verified` and matches only against addresses this site verified itself,
because anyone able to register at that provider with a chosen address could
otherwise walk into the matching account. An authorization server that passed
a provider's word along as its own would export exactly that problem to every
relying party downstream.

So a user who signed in with Google and never used a magic link here gets
`email_verified: false`, even though Google verified the address. That is not
a bug, and a relying party that wants to trust Google should trust Google
directly.

## What is not released

`description` — Plone's biography field — has no registered OIDC claim. Putting
it in a private one would emit something no other implementation can read, so
it is not emitted at all. The same goes for any field a site adds to its
Profile type.

The extension point for that is a private scope releasing namespaced claims.
It is deliberately not built: it needs a naming decision that should be made
once, by somebody who has a second implementation to be compatible with.

```{note}
This page describes the contract as of the `[server]` layer's first release.
Adding a claim to an existing scope is a compatible change; moving one between
scopes, or changing what `email_verified` asserts, is not.
```

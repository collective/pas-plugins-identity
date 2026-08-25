---
myst:
  html_meta:
    "description": "Register an OAuth client against a Plone site running the server layer, and rotate its secret and signing keys."
    "property=og:description": "Register an OAuth client against a Plone site running the server layer, and rotate its secret and signing keys."
    "property=og:title": "How to register an OAuth client"
---

(how-to-register-a-client)=

# How to register an OAuth client

This guide shows you how to let another application sign its users in against your Plone site.

It applies to the `[server]` layer.
Every endpoint below is bound to the `[server]` browser layer, so a site that never applied the server profile does not publish them at all.

All of these calls need the `Manage portal` permission.

## Register the client

```text
POST @identity-clients
```

Send the title, the redirect URIs, the grants, the scope, and the authentication method.

```{important}
The response to this call contains the client secret, and it is the only response that ever will.
Capture it now.
```

The secret is stored as a scrypt hash and nothing ever needs the plaintext again, so it cannot be read back.
If it is lost, rotate it.
There is no recovery, by design.

Read {doc}`/concepts/secrets` for why this differs from how a provider's secret behaves.

## Point the client at the discovery document

Give the client the issuer URL and its credential, and it needs nothing else.

```text
<issuer>/.well-known/openid-configuration
```

That document carries the endpoints, the `jwks_uri`, the signing algorithm, the supported scopes, and the claim list.

Set the issuer with the `pas.plugins.identity.server_issuer` registry record.
The package never derives it from the portal URL.
See {doc}`/concepts/federation` for why.

## Amend a registration

```text
PATCH @identity-clients/<id>
```

You can change the title, the redirect URIs, the grants, the scope, the service user, and whether the client is enabled.

You cannot change `client_id` or `auth_method`.
Renaming a client would orphan every token already minted for it, and turning a confidential client public would leave a stored secret hash that nothing checks.
Both are a delete and a re-register.

A `PATCH` naming any other unknown field is refused rather than ignored.
Silently dropping one is how an operator comes to believe they changed something they did not.

## Rotate a client secret

```text
POST @identity-clients/<id>/rotate-secret
```

The response carries the new secret, once.

## Revoke a client

```text
DELETE @identity-clients/<id>
```

Or set `enabled: false` with a `PATCH`, which is reversible.

Either one stops the client's tokens working immediately.
Access tokens carry the client id as their audience, and the Bearer plugin looks that id up in the registry on every request.
With no denylist, that is the only revocation this server has, which makes it worth knowing before you do it by accident.

## Rotate the signing key

```text
POST @identity-keys/rotate
```

Rotating mints a new signing key and keeps the previous ones, so tokens issued before the rotation keep verifying until they expire.
A relying party finds the right key by `kid`.

The ring is bounded, and the response reports the bound.
Rotating more times than the ring holds within one access-token lifetime does invalidate tokens still in flight.
That is a decision rather than an accident, which is why the number is in the response instead of only in the source.

To inspect the ring without rotating it:

```text
GET @identity-keys
```

This returns metadata only: key ids, and which one is signing.
It never returns key material.
The public halves are already served at `@@oauth-jwks`, and a second copy would only be something to fetch out of step with the first.

## Next steps

-   {doc}`/reference/claims` lists every endpoint, every scope, and every claim the server releases.
-   {doc}`/tutorials/federation-demo` runs the whole thing end to end against a second Plone site.

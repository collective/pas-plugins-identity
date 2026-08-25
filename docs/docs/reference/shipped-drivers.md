---
myst:
  html_meta:
    "description": "The drivers that ship with pas.plugins.identity and what each one requires."
    "property=og:description": "The drivers that ship with pas.plugins.identity and what each one requires."
    "property=og:title": "Shipped drivers"
---

(reference-shipped-drivers)=

# Shipped drivers

A driver is registered as a named ZCA utility providing `IDriver`, and the utility name is the driver id.
The following drivers ship with the package.

`github`
:   GitHub OAuth.
    Uses GitHub's published endpoints rather than discovery, because GitHub publishes no discovery document.

`google`
:   Google, through OpenID Connect discovery.

`oidc-generic`
:   Any OpenID Connect provider, configured with its discovery URL.

`plone-identity`
:   Another Plone site running this package's `[server]` layer.
    Built on the generic OIDC driver, because a peer is a conforming OIDC provider and gets no special path through the flow.
    It carries the configuration a peer can be known in advance to want: the `address` scope, an attribute mapping for every claim the peer actually releases, and the remote `sub` as the local userid, so one person keeps one id across the federation.

`email`
:   Magic-link sign-in.
    There is no external provider.
    The site emails a single-use signed token instead.

To add a driver for a provider not listed here, see {doc}`/how-to-guides/write-a-driver`.

(reference-magic-link)=

## The `email` driver

| Property | Value |
| --- | --- |
| Token lifetime | At most fifteen minutes, whatever you configure. |
| Reuse | Single use. The token is burned server-side. |
| Rate limit | Per address and per IP. |
| Response to an unknown address | Identical to the response for a known address. |

The rate limit applies per address and per IP because limiting per address alone misses the enumeration attack, which uses a fresh address every time.

The send endpoint answers identically whether or not the address belongs to an account.
A different answer would be an account-existence oracle.

A magic-link sign-in is the only email verification this package trusts for linking decisions.
See {doc}`/concepts/email-verification`.

(reference-backchannel-logout)=

## The back-channel logout endpoint

```text
POST @@backchannel-logout
```

One endpoint serves every configured provider.
The logout token names its issuer, and that is how the package chooses the provider, and therefore the key to verify the signature with.

To enable it, see {doc}`/how-to-guides/enable-back-channel-logout`.

### What the endpoint checks

The endpoint follows OpenID Connect Back-Channel Logout 1.0.
A token must satisfy all of the following:

-   a valid signature, from the issuer's published key
-   a matching issuer and audience
-   an acceptable `iat`
-   a `jti` that has not already been acted on, since a repeat is a replay
-   a declared back-channel logout event
-   a `sub` or a `sid`
-   no `nonce`, since a nonce means somebody is trying to pass an `id_token` off as a logout instruction

```{note}
Only `sub`-based logout is supported.
This package does not track provider session identifiers, so a token carrying only a `sid` is refused.
```

A logout for an identity this site has never seen answers `200`, not an error.
There is nothing to end, and answering differently would tell an unauthenticated caller which of a provider's subjects have accounts here.

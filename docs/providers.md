# Providers and secrets

A provider is a configured instance of a driver. The driver knows how to talk
to a kind of service; the provider record holds this site's credentials for
one particular one. Two GitHub organizations are two providers sharing one
driver.

Configuration lives in the registry as a single JSON record, which keeps the
whole thing exportable and importable through GenericSetup in one place.

## The control panel

**Identity providers** lists what is configured and offers a form per driver.
The form is generated from the driver's published schema, so a site that
installs a third-party driver gets its form with no frontend change.

Each provider has a **test connection** action, which fetches the provider's
discovery document (or validates the static configuration, for drivers that
have no discovery) and reports what it found. It clears the discovery cache
first: a button that reports the answer from twelve hours ago is worse than no
button.

## Secrets are write-only

Client secrets never leave the backend.

- The REST API and the control panel serialize a stored secret as a mask,
  never as its value.
- Saving the form back with the mask unchanged preserves the stored secret.
  That is what the mask is *for* — blanking the field would send an empty
  string, which is a different instruction and would destroy the secret.
- GenericSetup export omits secrets.
- The audit log never records credentials or tokens.

:::{warning}
This means a GenericSetup export of your provider configuration is not enough
to rebuild a working site. The secrets have to travel separately, by whatever
means your deployment already uses for secrets.
:::

## Deleting a provider

Deleting a provider removes its configuration. It does **not** delete the
identities linked through it: those are account data, and a configuration
change is not an instruction to lock people out. If you want the identities
gone as well, remove them first.

## Drivers shipped with the package

`github`
: GitHub OAuth. Uses GitHub's published endpoints rather than discovery,
  because GitHub does not publish a discovery document.

`google`
: Google, via OIDC discovery.

`oidc-generic`
: Any OpenID Connect provider, configured with its discovery URL.

`email`
: Magic-link sign-in. No external provider at all; the site emails a
  single-use signed token. See below.

## Magic links

The `email` driver sends a signed, single-use token with a lifetime of at most
fifteen minutes whatever you configure. The send endpoint is rate limited per
address **and** per IP — limiting per address alone misses the enumeration
attack, which uses a fresh address every time.

The send endpoint answers identically whether or not the address belongs to an
account. That is deliberate: a different answer is an account-existence oracle.

## Back-channel logout

When somebody signs out at the provider, the provider can tell this site
directly — server to server, with no browser involved, which is exactly why it
still works after the user has closed the tab.

Register this URL with the provider as the client's back-channel logout URI:

```
https://your-site.example.org/@@backchannel-logout
```

One endpoint serves every configured provider. The logout token names its
issuer, and that is how the provider — and therefore the key to verify the
signature with — is chosen.

### Turn on per-user keyrings, or this does nothing

A `plone.session` ticket is stateless and signed from a keyring, so there is
normally no way to end one person's session without ending everybody's.
`plone.session` has a switch for exactly this case:

1. Go to `acl_users/session` in the ZMI.
2. Open the **Manage secrets** tab.
3. Enable **per user keyring**.

Each user then gets their own signing ring, and a back-channel logout clears
and rotates only theirs.

```{warning}
Without `per_user_keyring` the endpoint still accepts and validates the
provider's token, but it **cannot end the user's Plone session** — their
existing ticket stays valid until it times out. The failure is logged as an
error rather than passed over quietly, and the `sessions_ended` attribute on
the `SessionsRevoked` event reports `False`.
```

### What a logout does and does not reach

| | |
| --- | --- |
| Plone session tickets | Ended, with `per_user_keyring` on. |
| Refresh tokens issued by the `[server]` layer | Revoked, across every client — the logout was about the person, not one application. |
| Access tokens issued by the `[server]` layer | **Not** revoked. They are self-encoded and there is no denylist (D3), so they live out their lifetime — at most the configured access-token TTL, fifteen minutes by default. |

That last row is the cost of the self-encoded design, and it is stated rather
than hidden: the access-token lifetime is also the worst case between a logout
and the last token honouring it going quiet.

### What is refused

The endpoint follows OpenID Connect Back-Channel Logout 1.0: the token's
signature, issuer, audience, `iat` and `jti` are checked; it must declare the
back-channel logout event; it must carry a `sub` or a `sid`; and it must not
carry a `nonce`, since a nonce means somebody is trying to pass an `id_token`
off as a logout instruction. A `jti` already acted on is refused as a replay.

A logout for an identity this site has never seen answers `200`, not an error.
There is nothing to end, and answering differently would tell an
unauthenticated caller which of a provider's subjects have accounts here.

```{note}
Only `sub`-based logout is supported. This package does not track provider
session identifiers, so a token carrying only a `sid` is refused.
```

## Writing your own driver

See {doc}`drivers`.

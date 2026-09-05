---
myst:
  html_meta:
    "description": "The five drivers that ship with pas.plugins.identity, their defaults, and the settings each one offers."
    "property=og:description": "The five drivers that ship with pas.plugins.identity, their defaults, and the settings each one offers."
    "property=og:title": "Shipped drivers"
---

(reference-shipped-drivers)=

# Shipped drivers

<!-- source: backend/src/pas/plugins/identity/core/drivers/ -->
<!-- source: backend/src/pas/plugins/identity/core/flows/metadata.py -->

A driver is registered as a named ZCA utility providing `IDriver`, and the
utility name is the driver id. Five ship with the package.

| Driver id | Title | Provider |
|---|---|---|
| `oidc-generic` | OpenID Connect | Any conforming OpenID Connect provider. |
| `plone-identity` | Plone site | Another Plone site running the `[server]` layer. Built on `oidc-generic`. |
| `google` | Google | Google, through discovery at an issuer the driver fixes. |
| `github` | GitHub | GitHub OAuth2. Not an OpenID Connect provider. |
| `email` | Email | No external provider: this site emails a single-use signed token. |

## Attributes

Every column is a class attribute on the driver, and every one of them is only a
**default**. What a given deployment trusts a given provider with is a fact about
the deployment, so the operator can override each one per provider.

| | `oidc-generic` | `plone-identity` | `google` | `github` | `email` |
|---|---|---|---|---|---|
| Settings schema | `IOIDCSettings` | `IPloneIdentitySettings` | `IOAuth2Settings` | `IGitHubSettings` | `IEmailSettings` |
| Endpoints from | discovery, at an issuer you type | discovery, at an issuer you type | discovery, at `https://accounts.google.com` | fixed, built in | none |
| Default scope | `openid email profile` | `openid email profile address` | `openid email profile` | `read:user user:email` | — |
| Subject read from | `sub` | `sub` | `sub` | `id`, then `node_id` | `email` |
| Default userid source | `uuid` | `username` | `uuid` | `username` | `uuid` |
| Trusts `email_verified` by default | no | no | **yes** | **yes** | — |
| Default group claim | `groups` | `groups` | none | none | none |
| Can be linked from a form | yes | yes | yes | yes | **no** |

`email` is the only driver a user cannot start a link against from a form: its
subject is an address the user would type, and a free-text box there is a box for
claiming any address at all. Its addresses come from the profile instead.

### Which settings each schema carries

<!-- source: backend/src/pas/plugins/identity/core/drivers/settings.py -->

This is what decides which fields a provider's form shows. A driver on
`IOAuth2Settings` has no `issuer` field and **no group fields at all**.

| Schema | Extends | Adds |
|---|---|---|
| `IDriverSettings` | `Interface` | nothing |
| `IOAuth2Settings` | `IDriverSettings` | `client_id`, `client_secret`, `scope`, `userid_source`, `trust_email_verification`, `create_user`, `accept_string_booleans`, `auto_link_by_email` |
| `IOIDCSettings` | `IOAuth2Settings` | `issuer`, `group_claim`, `allowed_groups`, `sync_groups`, `picture_over_http` |
| `IGitHubSettings` | `IOAuth2Settings` | nothing |
| `IPloneIdentitySettings` | `IOIDCSettings` | nothing but a different `issuer` description |
| `IEmailSettings` | `IDriverSettings` | `token_ttl`, `rate_limit_per_hour` |

Two consequences worth reading off that table:

- **`google` and `github` have no group settings.** Not a group claim you can
  name, not an allowed-groups list, not a sync switch. Neither provider sends
  groups this package can read.
- **`email` has no account settings.** No `create_user`, no `auto_link_by_email`,
  no `trust_email_verification`. A missing `create_user` reads as `True`, so an
  `email` provider always creates accounts.

See {doc}`settings` for each field's type and default, and {doc}`provider-form`
for how they are arranged in the control panel.

### Default property maps

Seeded into a new provider's attribute mapping, written against the **normalized**
claim names rather than any one provider's.

| Driver | Map |
|---|---|
| `oidc-generic`, `google`, `github` | `email` → `email`, `fullname` → `fullname` |
| `plone-identity` | those two, plus `website` → `home_page`, `description` → `description`, `address.formatted` → `location`, `picture_url` → `portrait` |
| `email` | `email` → `email` |

No driver maps `username`. Providers publish it; Plone has no property for it.

## Driver notes

`github`
:   `GET /user` omits the address of anybody who marked it private and carries no
    `email_verified` at all, so the driver names `GET /user/emails` as an
    enrichment endpoint and the flow fetches it after userinfo. That call is
    best-effort: a narrowed scope answers 403, and a login is not the moment to
    fail over an address. Every address on the account goes onto the person's
    profile, the account's own primary first.

`google`
:   Its issuer is fixed at `https://accounts.google.com` rather than typed. There
    is nothing to configure and nothing to get wrong.

`plone-identity`
:   A peer is a conforming OIDC provider and gets no special path through the
    flow. What the driver carries is the configuration a peer can be known in
    advance to want: the `address` scope, a map for every claim the peer actually
    releases, and the peer's `preferred_username` as the local userid, so one
    person is recognisable by the same name across the federation.

`email`
:   See below.

To add a driver for a provider not listed here, see
{doc}`/how-to-guides/write-a-driver`.

## Group claims

A driver declares whether its providers assert group membership, and that
declaration is what offers the group map in the control panel. A driver with no
group claim offers no field to name one, and a group map stored against such a
provider grants nothing rather than guessing at a claim name.

`groups` is not a registered OIDC claim. It is the name Keycloak, Okta and Entra
all use, and the one this package's own `[server]` layer releases. Set a dotted
path for a provider that nests them, such as `realm_access.roles`.

Mapping and revocation are covered in {doc}`/how-to-guides/map-provider-groups`.

(reference-magic-link)=

## The `email` driver

| Property | Value |
|---|---|
| Token lifetime | At most fifteen minutes, whatever `token_ttl` says. |
| Reuse | Single use. The token is burned server side. |
| Rate limit | Per address **and** per IP. |
| Response to an unknown address | Identical to the response for a known address. |

The rate limit applies per IP as well as per address because limiting per address
alone misses the enumeration attack, which uses a fresh address every time. The
send endpoint answers identically whether or not the address belongs to an
account: a different answer would be an account-existence oracle.

A magic-link sign-in is the only email verification this package trusts for
linking decisions. See {doc}`/concepts/email-verification`.

### Two kinds of link

| Link | Asked for from | Effect | Redeemed at |
|---|---|---|---|
| Sign-in | The login page | Signs its holder in | `@magic-link-confirm` |
| Confirmation | {guilabel}`Sign-in methods` | Adds the address to the account that asked for it, and signs nobody in | its own endpoint |

Each endpoint accepts only the purpose it handles, so neither link can be
redeemed as the other.

A confirmation link has to be opened while the account that asked for it is still
signed in. Opening it as somebody else, or as nobody, is refused—and the link is
spent either way.

## Related

- {doc}`/how-to-guides/providers/index`—a recipe per provider
- {doc}`driver-contract`—what a driver must implement
- {doc}`settings`—every field named here
- {doc}`endpoints`—including back-channel logout
- {doc}`/how-to-guides/write-a-driver`—adding one

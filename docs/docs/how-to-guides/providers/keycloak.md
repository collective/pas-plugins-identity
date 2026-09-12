---
myst:
  html_meta:
    "description": "Add Keycloak sign-in to a Plone site, including group membership."
    "property=og:description": "Add Keycloak sign-in to a Plone site, including group membership."
    "property=og:title": "Provider recipe: Keycloak"
---

(how-to-provider-keycloak)=

# Keycloak

<!-- source: backend/src/pas/plugins/identity/core/drivers/keycloak.py -->

Sign in with accounts from a Keycloak realm, and honour its groups.

This uses the `keycloak` driver. A realm is a standard OpenID Connect provider,
and the driver is the generic one with a realm's defaults on top: the realm's
username as the Plone userid, and its email verification trusted.

```{note}
The provider-side steps were verified on 2026-09-05 against Keycloak **26.0**
running in Docker. The claims in step 5 were read out of a real `id_token` and
userinfo response, not from documentation, and read again on 2026-09-12.
```

## 1. What you need from Keycloak

| | |
|---|---|
| Issuer | `https://kc.example.com/realms/<realm>` |
| Client ID | the client you create below |
| Client secret | from the client's **Credentials** tab |

The issuer is the **realm** URL, not the server root. A Keycloak server hosts
many realms and each is its own issuer; the server root serves no discovery
document at all. Confirm it:

```shell
curl -s https://kc.example.com/realms/myrealm/.well-known/openid-configuration | jq .issuer
```

## 2. Create the client in Keycloak

In the realm's admin console, create a client with:

| Setting | Value |
|---|---|
| Client type | OpenID Connect |
| Client authentication | **On**—this package uses a confidential client |
| Standard flow | enabled |
| Valid redirect URIs | `https://www.example.com/login-identity` |

Take the secret from the **Credentials** tab afterwards.

## 3. Add a groups mapper—Keycloak does not send groups by default

This is the step people miss, and its symptom is that group mapping silently
does nothing.

A default Keycloak client sends **no `groups` claim at all**. Verified: an
`id_token` from a user who *is* in a group has no `groups` key until a mapper
exists.

On the client, go to **Client scopes**, open the client's dedicated scope, and add
a mapper:

| Setting | Value |
|---|---|
| Mapper type | Group Membership |
| Name | `groups` |
| Token Claim Name | `groups` |
| Full group path | **Off** |
| Add to ID token | On |
| Add to userinfo | On |

With **Full group path** off, a group named `site-editors` arrives as
`site-editors`. With it on it arrives as `/site-editors`, and your group map has
to match that instead. Off is easier to live with.

```{note}
`realm_access.roles` is a different thing: those are **roles**, not groups, and
they are not in the `id_token` by default either. Map groups unless you
specifically want roles.
```

## 4. Add the provider in Plone

1. Open the **Identity providers** control panel.
2. Add a provider and choose **Keycloak** (`keycloak`).
3. On the **Settings** tab:

   | Field | Value |
   |---|---|
   | Title | your realm's name |
   | Issuer | `https://kc.example.com/realms/<realm>` |
   | Client ID | from step 2 |
   | Client secret | from step 2 |
   | Scope | leave empty for `openid email profile` |

4. Save, then **Test connection**.

## 5. What Keycloak actually sends

Read from a real `id_token` on 26.0, for a user in one group, with the mapper
from step 3:

| Claim | Value | Notes |
|---|---|---|
| `sub` | `5c867388-…` | a UUID, stable across username changes |
| `email` | `dana@example.com` | |
| `email_verified` | `true` | a **real boolean** |
| `groups` | `["site-editors"]` | only with the mapper |
| `preferred_username` | `dana` | the Plone userid, by default |
| `name` | `Dana Example` | normalized to `fullname` by this package |
| `given_name`, `family_name` | `Dana`, `Example` | mapped to nothing by default |

A default realm sends nothing else under this scope: no `website`, no `picture`
and no `address`, because its user profile has no attribute to fill them from.
That is why the driver's property map has one row, `fullname`. A realm that adds
attributes, and mappers releasing them, can map more on the **Mapping** tab.

**`email_verified` is a proper boolean in a default Keycloak.** You do not need
**This provider sends verification flags as text** unless your realm has been
customized to send a string. Turn it on only if you have established that yours
does—see {doc}`../link-accounts-by-email`.

## 6. Check the account defaults

On the **Accounts** tab. The driver starts a new provider with the first two
fields set for a realm:

| Field | Starts as | Guidance |
|---|---|---|
| Userid taken from | The provider's username | The realm's `preferred_username`. Choose **A random id** for a userid that reveals nothing. |
| This provider's email verification counts | on | Switch it off for a realm that lets people sign up without verifying their address, or whose administrators mark addresses verified by hand. |
| Attach to an existing account with the same verified email | off | Needs the switch above |
| Let this provider create accounts | on | Off if membership is decided in Plone |

The identity is recorded against `sub`, so a username the realm renames later
does not break the sign-in. The Plone userid keeps the name it was created with,
and a username already taken in Plone gets a numeric suffix.

```{warning}
A trusted verification is what an existing account is attached to. A realm
whose administrators mark addresses verified without proof hands those
administrators every account with a matching address. See
{doc}`/concepts/email-verification`.
```

## 7. Map the groups

On the **Groups** tab:

1. Leave **Groups arrive in the claim** as `groups`.
2. Add one row per Keycloak group you want to honour, pointing at a local group id.

An unmapped Keycloak group grants nothing here and is never created. See
{doc}`../map-provider-groups`.

## Verify

1. `/login` shows the button, and signing in returns you signed in.
2. `/identities` lists the identity with a UUID subject.
3. The new account's userid is the realm username.
4. A mapped group appears in the user's Plone group membership.
5. The audit log has an `authenticated` entry.

If groups never arrive, go back to step 3—that is the cause almost every time.

## Known quirks

- **The issuer is the realm URL.** Using the server root gives a 404 on discovery.
- **Groups need a mapper.** Verified absent by default.
- **Full group path changes the name.** `/site-editors` rather than `site-editors`.
- **Roles are not groups.** `realm_access.roles` is absent from the `id_token` by default.
- **A renamed username keeps its old userid.** The sign-in still works; the Plone userid does not follow.

## Related

- {doc}`generic-oidc`—the driver this one is built on
- {doc}`/reference/shipped-drivers`—the `keycloak` driver's defaults
- {doc}`../map-provider-groups`—the group map and revocation
- {doc}`../troubleshoot`—"Groups not granted after login"

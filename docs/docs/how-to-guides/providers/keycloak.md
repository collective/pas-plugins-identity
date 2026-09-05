---
myst:
  html_meta:
    "description": "Add Keycloak sign-in to a Plone site, including group membership."
    "property=og:description": "Add Keycloak sign-in to a Plone site, including group membership."
    "property=og:title": "Provider recipe: Keycloak"
---

(how-to-provider-keycloak)=

# Keycloak

Sign in with accounts from a Keycloak realm, and honour its groups.

Keycloak is a standard OpenID Connect provider, so this uses the
`oidc-generic` driver.

```{note}
Verified on 2026-09-05 against Keycloak **26.0** running in Docker. The claim
shapes in step 5 were read out of a real `id_token`, not from documentation.
```

## 1. What you need from Keycloak

| | |
|---|---|
| Issuer | `https://kc.example.com/realms/<realm>` |
| Client ID | the client you create below |
| Client secret | from the client's **Credentials** tab |

The issuer is the **realm** URL, not the server root. A Keycloak server hosts
many realms and each is its own issuer. Confirm it:

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
2. Add a provider and choose **OpenID Connect** (`oidc-generic`).
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
| `preferred_username` | `dana` | |
| `name` | `Dana Example` | normalized to `fullname` by this package |

**`email_verified` is a proper boolean in a default Keycloak.** You do not need
**This provider sends verification flags as text** unless your realm has been
customized to send a string. Turn it on only if you have established that yours
does—see {doc}`../link-accounts-by-email`.

## 6. Set the trust switches

On the **Accounts** tab:

| Field | Guidance |
|---|---|
| Trust this provider's email verification | On if the realm requires address verification at sign-up. Keycloak's `email_verified` means what this package means by it. |
| Attach to an existing account with the same verified email | Needs the switch above |
| Let this provider create accounts | Off if membership is decided in Plone |

## 7. Map the groups

On the **Groups** tab:

1. Leave **Groups arrive in the claim** as `groups`.
2. Add one row per Keycloak group you want to honour, pointing at a local group id.

An unmapped Keycloak group grants nothing here and is never created. See
{doc}`../map-provider-groups`.

## Verify

1. `/login` shows the button, and signing in returns you signed in.
2. `/identities` lists the identity with a UUID subject.
3. A mapped group appears in the user's Plone group membership.
4. The audit log has an `authenticated` entry.

If groups never arrive, go back to step 3—that is the cause almost every time.

## Known quirks

- **The issuer is the realm URL.** Using the server root gives a 404 on discovery.
- **Groups need a mapper.** Verified absent by default.
- **Full group path changes the name.** `/site-editors` rather than `site-editors`.
- **Roles are not groups.** `realm_access.roles` is absent from the `id_token` by default.

## Related

- {doc}`generic-oidc`—the same driver, generally
- {doc}`../map-provider-groups`—the group map and revocation
- {doc}`../troubleshoot`—"Groups not granted after login"

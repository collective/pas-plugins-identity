---
myst:
  html_meta:
    "description": "Add Microsoft Entra ID sign-in to a Plone site."
    "property=og:description": "Add Microsoft Entra ID sign-in to a Plone site."
    "property=og:title": "Provider recipe: Microsoft Entra ID"
---

(how-to-provider-microsoft-entra)=

# Microsoft Entra ID

Sign in with accounts from a Microsoft Entra ID tenant, formerly Azure AD.

Entra is a standard OpenID Connect provider, so this uses the `oidc-generic`
driver.

```{warning}
**Provider-side steps are not verified.** The Plone side below is read from this
package's source and is accurate. The Entra portal steps have not been walked
through against a live tenant. Follow
[Microsoft's own OpenID Connect documentation](https://learn.microsoft.com/en-us/entra/identity-platform/v2-protocols-oidc)
for the portal, and use the tables here for Plone.
```

## 1. What you need from Entra

| | |
|---|---|
| Issuer | `https://login.microsoftonline.com/<tenant-id>/v2.0` |
| Client ID | the application (client) ID |
| Client secret | from **Certificates & secrets** |

Confirm the issuer before configuring it:

```shell
curl -s https://login.microsoftonline.com/<tenant-id>/v2.0/.well-known/openid-configuration | jq .issuer
```

Register the redirect URI on the app registration, as a **Web** platform:

```text
https://www.example.com/login-identity
```

## 2. Add the provider

1. Open the **Identity providers** control panel.
2. Add a provider and choose **OpenID Connect** (`oidc-generic`).
3. On the **Settings** tab:

   | Field | Value |
   |---|---|
   | Title | your organization's name |
   | Issuer | from step 1, including the `/v2.0` |
   | Client ID | from step 1 |
   | Client secret | from step 1 |
   | Scope | leave empty for `openid email profile` |

4. Save, then **Test connection**.

## 3. Email verification—read this before switching anything on

```{warning}
**Entra does not send `email_verified`.**

An absent claim is not a `true`, so this package treats every address from Entra
as unverified. Turning on **Trust this provider's email verification** changes
nothing, and turning on **Attach to an existing account with the same verified
email** then never fires, because there is no verified address to match on.

The symptom is silence: sign-in works and linking never happens.
```

If you need accounts linked by address for an Entra tenant, that is a decision to
make deliberately and not one this package can make from the claims. The safe
arrangement is to turn off account creation and add the accounts yourself, so
each match is a human decision.

## 4. Groups need configuration in the app manifest

Entra sends no `groups` claim until you ask for one, in the app registration's
**Token configuration** or in the manifest's `groupMembershipClaims`.

Two things to know once you do:

- **Group ids arrive, not names.** Entra sends object GUIDs by default, so the
  left-hand side of your group map is a GUID unless the tenant is configured to
  emit group names.
- **Large group counts are truncated.** Past a limit Entra replaces the claim
  with a link to fetch groups from Microsoft Graph, which this package does not
  follow. A user in many groups may arrive with none.

Set **Groups arrive in the claim** to `groups` once it is emitted, and map the
ids you care about—see {doc}`../map-provider-groups`.

## Verify

1. `/login` shows the button, and signing in returns you signed in.
2. `/identities` lists the identity.
3. The audit log has an `authenticated` entry.
4. If you configured groups, a mapped group appears in the user's membership.

## Known quirks

- **No `email_verified`.** See step 3. This is the one that surprises people.
- **The `/v2.0` suffix is part of the issuer.** Leaving it off gives you the v1
  endpoint, whose tokens differ.
- **Group claims are GUIDs, and are truncated in bulk.** See step 4.

## Related

- {doc}`generic-oidc`—the same driver, generally
- {doc}`/concepts/email-verification`—why an absent claim is not a `true`
- {doc}`../control-account-creation`—the safer arrangement for Entra

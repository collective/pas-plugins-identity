---
myst:
  html_meta:
    "description": "Add any OpenID Connect provider to a Plone site with the generic OIDC driver."
    "property=og:description": "Add any OpenID Connect provider to a Plone site with the generic OIDC driver."
    "property=og:title": "Provider recipe: any OpenID Connect provider"
---

(how-to-provider-generic-oidc)=

# Any OpenID Connect provider

The `oidc-generic` driver works with any provider that publishes a discovery
document. Okta, Auth0, Authentik, Zitadel, Keycloak, ORCID, your organization's
own server.

```{note}
The Plone side of this recipe was verified against the demo stack on 2026-09-05.
The provider side depends on which provider you use.
```

## 1. Check the provider is usable

Fetch its discovery document before configuring anything:

```shell
curl -s https://id.example.com/.well-known/openid-configuration | jq
```

You need four things in the response:

| Field | Why |
|---|---|
| `issuer` | must equal the URL you will configure, exactly |
| `authorization_endpoint` | where the browser is sent |
| `token_endpoint` | where this site exchanges the code |
| `jwks_uri` | where the signing keys come from |

If that URL 404s, the provider is not an OpenID Connect provider and this driver
will not work with it. If it returns something and `issuer` differs from the URL
you fetched, configure the value of `issuer`, not the URL you typed.

## 2. Register this site with the provider

In the provider's own console, create an application or client with:

| | |
|---|---|
| Redirect URI | `https://www.example.com/login-identity` |
| Grant type | authorization code |
| Response type | code |

Note the client ID and client secret it gives you.

## 3. Add the provider

1. Open the **Identity providers** control panel.
2. Add a provider and choose **OpenID Connect** (`oidc-generic`).
3. On the **Settings** tab:

   | Field | Value |
   |---|---|
   | Title | what the button should say |
   | Issuer | the `issuer` value from step 1 |
   | Client ID | from step 2 |
   | Client secret | from step 2 |
   | Scope | leave empty for the default `openid email profile` |

4. Save, then use **Test connection**.

## 4. Set the trust switches

On the **Accounts** tab. This driver ships with **everything off**, because a
generic provider is one whose sign-up rules this package cannot know.

| Field | Guidance |
|---|---|
| Trust this provider's email verification | On only if you know it refuses to call an address verified until the account has answered mail at it |
| Attach to an existing account with the same verified email | Needs the switch above |
| Let this provider create accounts | Off if membership is decided here |
| This provider sends verification flags as text | Only if step 5 says so |

```{warning}
A provider that marks addresses verified according to weaker rules than yours is
an account takeover waiting to happen: somebody registers there with an address
belonging to one of your users, and this site hands them the account.
See {doc}`/concepts/email-verification`.
```

## 5. Check how it sends `email_verified`

Some providers send the string `"true"` rather than the boolean `true`.

If linking by email never fires even though both switches are on, this is almost
certainly why. Turn on **This provider sends verification flags as text**.

The symptom is that nothing visibly goes wrong: sign-in works, every address
arrives unverified, and no error says so.

## 6. Groups, if the provider sends them

On the **Groups** tab, set **Groups arrive in the claim** to the claim your
provider uses. `groups` is the default. Use a dotted path for a provider that
nests them, such as `realm_access.roles`.

Then map the ones that mean something here—see {doc}`../map-provider-groups`.

## Verify

1. Open `/login`. The button is there.
2. Sign in. You are sent to the provider and returned signed in.
3. `/identities` lists the identity.
4. The audit log has an `authenticated` entry.

If any step fails, {doc}`../troubleshoot` is organized by exactly these symptoms.

## Related

- {doc}`keycloak`, {doc}`microsoft-entra`—the same driver, with provider-specific notes
- {doc}`/reference/claims`—what this package does with what arrives
- {doc}`/concepts/email-verification`—the whole trust rule

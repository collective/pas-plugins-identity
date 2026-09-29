---
myst:
  html_meta:
    "description": "Let another Plone site sign its users in against a Plone site running the server layer."
    "property=og:description": "Let another Plone site sign its users in against a Plone site running the server layer."
    "property=og:title": "Client recipe: another Plone site"
---

(how-to-client-another-plone-site)=

# Another Plone site

Let another Plone site sign its users in with accounts from your site.

The other site needs this package's core layer and its Volto add-on. It
connects with the **Plone site** driver, and
{doc}`/how-to-guides/providers/another-plone-site` is its half of this setup.

```{note}
Verified against the demo stack on 2026-09-05.
{doc}`/tutorials/federation-demo` builds exactly this, end to end, in Docker.
```

The examples use `https://id.example.org` as your site, the issuer, and
`https://www.example.com` as the other site.

## 1. Register the client

<!-- source: backend/src/pas/plugins/identity/core/drivers/identity.py, default_scope -->

Follow {doc}`/how-to-guides/server/register-an-oauth-client` with:

| Field | Value |
|---|---|
| Redirect URI | `https://www.example.com/login-identity` |
| Grant | Authorization code |
| Scope | `openid`, `email`, `profile`, `address` |
| Secret | Yes. A Plone site is a confidential client |

The redirect URI is the other site's **frontend** URL plus the callback path
from its **Identity providers** control panel, where `/login-identity` is the
default.

The scope is the driver's default. `address` carries the profile's location
field across.

Capture the client secret from the response. It is shown once.

## 2. Hand over three values

Give whoever runs the other site:

| Value | Is |
|---|---|
| Issuer | `https://id.example.org` |
| Client ID | From step 1 |
| Client secret | From step 1 |

They add the provider by following {doc}`/how-to-guides/providers/another-plone-site`.
The driver reads everything else from your discovery document.

## Verify

1. On the other site, the provider's **Test connection** action reports the
   discovery document it found.
2. Its `/login` offers your site's button.
3. Signing in there brings you to your site, which asks you to approve the
   other site once, and returns you there signed in.

## Known quirks

- **The issuer must resolve from both places.** A browser follows it to sign
  in, and the other site's server fetches discovery from it. In containers
  those are often different networks.
- **Groups cross only where the other site maps them.** It receives the
  `groups` claim with the `profile` scope, and an unmapped group grants
  nothing there. See {doc}`/how-to-guides/accounts/map-provider-groups`.

## Related

- {doc}`/how-to-guides/providers/another-plone-site`—the other site's half of this setup
- {doc}`/tutorials/federation-demo`—both halves, running, in Docker
- {doc}`/how-to-guides/server/index`—the other client recipes, and what every client needs

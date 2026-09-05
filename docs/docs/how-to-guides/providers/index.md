---
myst:
  html_meta:
    "description": "Step-by-step recipes for each identity provider pas.plugins.identity can talk to."
    "property=og:description": "Step-by-step recipes for each identity provider pas.plugins.identity can talk to."
    "property=og:title": "Provider recipes"
---

(how-to-providers)=

# Provider recipes

One page per provider, each with the same shape: what to get from the provider,
which driver to choose, what to type in the form, and how to tell that it worked.

Do {doc}`../install` and {doc}`../install-the-frontend` first.

## Pick a recipe

| Provider | Driver | Recipe |
|---|---|---|
| Another Plone site | `plone-identity` | {doc}`another-plone-site` |
| Any OpenID Connect provider | `oidc-generic` | {doc}`generic-oidc` |
| Emailed magic link | `email` | {doc}`magic-link` |
| Keycloak | `oidc-generic` | {doc}`keycloak` |
| GitHub | `github` | {doc}`github` |
| Google | `google` | {doc}`google` |
| Microsoft Entra ID | `oidc-generic` | {doc}`microsoft-entra` |

For anything not listed, use {doc}`generic-oidc`: any provider that publishes a
discovery document works with it, and the recipe says what to check first.

## The redirect URI, once

Every provider asks for a redirect URI, and it is the same value for all of them:

```text
https://www.example.com/login-identity
```

That is your **frontend** base URL plus the callback path from the **Identity
providers** control panel. `/login-identity` is the default, and the route the
Volto add-on registers.

Two mistakes account for most `redirect_uri_mismatch` failures:

- Using the backend's URL. The redirect goes to the frontend.
- A trailing slash, or `http` where the provider has `https`. Providers match
  this string exactly.

## Verification status

Provider user interfaces change, and a recipe that claims to be current when it
is not is worse than one that says it is unverified.

| Recipe | Provider-side steps |
|---|---|
| {doc}`another-plone-site` | verified against the demo stack, 2026-09-05 |
| {doc}`generic-oidc` | verified against the demo stack, 2026-09-05 |
| {doc}`magic-link` | verified against the demo stack, 2026-09-05 |
| {doc}`keycloak` | verified against Keycloak 26.0, 2026-09-05 |
| {doc}`github` | **not verified** |
| {doc}`google` | **not verified** |
| {doc}`microsoft-entra` | **not verified** |

An unverified recipe keeps its provider-side steps short and links to the
provider's own documentation, which is the part that stays current. The Plone
side of every recipe is read from this package's source and is accurate.

## Related

- {doc}`/reference/shipped-drivers`—every driver and its defaults
- {doc}`/reference/provider-form`—every form field, by tab
- {doc}`../troubleshoot`—when a sign-in does not work

```{toctree}
:maxdepth: 1
:hidden: true

another-plone-site
generic-oidc
magic-link
keycloak
github
google
microsoft-entra
```

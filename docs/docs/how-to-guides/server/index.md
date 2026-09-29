---
myst:
  html_meta:
    "description": "Let other applications sign their users in against a Plone site running the server layer."
    "property=og:description": "Let other applications sign their users in against a Plone site running the server layer."
    "property=og:title": "Act as an identity provider"
---

(how-to-clients)=

# Act as an identity provider

Let other applications sign their users in with accounts from your Plone site.
This needs the `[server]` layer.

| Guide | Does |
|---|---|
| {doc}`register-an-oauth-client` | Registers an application, and rotates its secret and the signing keys |

## Related

- {doc}`/reference/claims`—every scope and the claims it releases
- {doc}`/reference/endpoints`—the server layer's full surface
- {doc}`/how-to-guides/providers/index`—the other direction, signing in *to* this site

```{toctree}
:maxdepth: 1
:hidden: true

register-an-oauth-client
```

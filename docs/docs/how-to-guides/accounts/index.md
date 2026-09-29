---
myst:
  html_meta:
    "description": "Decide what an identity provider may do on your site: link existing accounts, create new ones, and grant groups."
    "property=og:description": "Decide what an identity provider may do on your site: link existing accounts, create new ones, and grant groups."
    "property=og:title": "Decide what a provider may do"
---

# Decide what a provider may do

What a provider may do on your site, one decision per guide.

| Guide | Decides |
|---|---|
| {doc}`link-accounts-by-email` | Whether a sign-in attaches to an existing account with the same verified email |
| {doc}`control-account-creation` | Whether a provider may create accounts at all |
| {doc}`map-provider-groups` | Which of a provider's groups grant a group here, and who may sign in |

## Related

- {doc}`/how-to-guides/providers/configure-a-provider`—the settings every provider shares
- {doc}`/reference/provider-form`—every field on the provider form, by tab
- {doc}`/concepts/identities`—why an account and an identity are two things

```{toctree}
:maxdepth: 1
:hidden: true

link-accounts-by-email
control-account-creation
map-provider-groups
```

---
myst:
  html_meta:
    "description": "Move a site from pas.plugins.authomatic or pas.plugins.oidc to pas.plugins.identity."
    "property=og:description": "Move a site from pas.plugins.authomatic or pas.plugins.oidc to pas.plugins.identity."
    "property=og:title": "Migrate from other plugins"
---

# Migrate from other plugins

Move a site that signs people in with another PAS plugin to this package,
keeping its users and their external identities.

| From | Guide |
|---|---|
| `pas.plugins.authomatic` | {doc}`from-authomatic` |
| `pas.plugins.oidc` | {doc}`from-oidc` |

Both migrations are dry runs by default, can be run again safely, and report
what they would do before they do it.

## Related

- {doc}`/reference/migration-reports`—every field of a migration report
- {doc}`/concepts/identities`—what the migrations are mapping onto

```{toctree}
:maxdepth: 1
:hidden: true

from-authomatic
from-oidc
```

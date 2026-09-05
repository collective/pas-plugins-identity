---
myst:
  html_meta:
    "description": "Task-oriented directions for installing, configuring, and extending pas.plugins.identity."
    "property=og:description": "Task-oriented directions for installing, configuring, and extending pas.plugins.identity."
    "property=og:title": "How-to guides"
    "keywords": "Plone, pas.plugins.identity, how-to, install, configure, migrate, troubleshoot"
---

# How-to guides

How-to guides are directions that guide you through a problem or toward a result.
How-to guides are goal-oriented.

Each guide assumes you already know what you want.
If you want to understand why something works the way it does, read {doc}`/concepts/index` instead—and if you are new here, start with {doc}`/concepts/mental-model`.

## Getting a site running

Do these three in order.

```{toctree}
:maxdepth: 1

install
install-the-frontend
providers/index
```

Then {doc}`configure-a-provider` for the settings every provider shares.

```{toctree}
:maxdepth: 1

configure-a-provider
```

## Deciding what a provider may do

```{toctree}
:maxdepth: 1

link-accounts-by-email
control-account-creation
map-provider-groups
```

## When something is wrong

```{toctree}
:maxdepth: 1

troubleshoot
```

## Operating a site

```{toctree}
:maxdepth: 1

read-the-audit-log
review-a-user-account
enable-back-channel-logout
export-and-import-principals
upgrade
```

## Acting as an authorization server

```{toctree}
:maxdepth: 1

register-an-oauth-client
```

## Moving to this package

```{toctree}
:maxdepth: 1

migrate-from-authomatic
migrate-from-oidc
```

## Extending the package

```{toctree}
:maxdepth: 1

write-a-driver
```

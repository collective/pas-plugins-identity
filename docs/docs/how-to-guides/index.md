---
myst:
  html_meta:
    "description": "Task-oriented directions for installing, configuring, operating, and extending pas.plugins.identity."
    "property=og:description": "Task-oriented directions for installing, configuring, operating, and extending pas.plugins.identity."
    "property=og:title": "How-to guides"
    "keywords": "Plone, pas.plugins.identity, how-to, install, configure, migrate, troubleshoot"
---

# How-to guides

How-to guides are directions that guide you through a problem or toward a result.
How-to guides are goal-oriented.

Each guide assumes you already know what you want.
If you want to understand why something works the way it does, read {doc}`/concepts/index` instead—and if you are new here, start with {doc}`/concepts/mental-model`.

## Find a guide

To get a site running, work through {doc}`install/index` and then {doc}`providers/index`, in that order.

`````{grid} 1 1 2 2
:gutter: 3

````{grid-item-card} 📦 Install and upgrade
:link: install/index
:link-type: doc

Install the backend and the frontend, and upgrade an existing site.
````

````{grid-item-card} 🔑 Sign in with a provider
:link: providers/index
:link-type: doc

Let people sign in with Google, GitHub, Keycloak, another Plone site, or any OpenID Connect provider.
````

````{grid-item-card} ⚖️ Decide what a provider may do
:link: accounts/index
:link-type: doc

Link accounts by email, control account creation, and map a provider's groups.
````

````{grid-item-card} 🩺 Operate a site
:link: operate/index
:link-type: doc

Troubleshoot sign-in, read the audit log, review an account, enable back-channel logout, and move principals.
````

````{grid-item-card} 🪪 Act as an identity provider
:link: server/index
:link-type: doc

Let other applications sign their users in against your site.
````

````{grid-item-card} 🚚 Migrate from other plugins
:link: migrate/index
:link-type: doc

Move from `pas.plugins.authomatic` or `pas.plugins.oidc`.
````

````{grid-item-card} 🧩 Extend the package
:link: extend/index
:link-type: doc

Write drivers, profile enrichers, and claims, and extend the user catalog and profile pages.
````

`````

```{toctree}
:maxdepth: 2
:hidden: true

install/index
providers/index
accounts/index
operate/index
server/index
migrate/index
extend/index
```

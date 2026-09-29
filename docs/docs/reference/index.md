---
myst:
  html_meta:
    "description": "Endpoints, settings, events, claims, and shipped drivers for pas.plugins.identity."
    "property=og:description": "Endpoints, settings, events, claims, and shipped drivers for pas.plugins.identity."
    "property=og:title": "Reference"
    "keywords": "Plone, pas.plugins.identity, reference, API, endpoints, settings, claims"
---

# Reference

Reference guides are technical descriptions of the machinery and how to operate it.
Reference material is information-oriented.

Look things up here.
For directions toward a result, read {doc}`/how-to-guides/index`.
For the reasoning behind any of it, read {doc}`/concepts/index`.

## Writing Python against this package

`````{grid} 1 1 2 2
:gutter: 3

````{grid-item-card} 🐍 Python API
:link: python-api
:link-type: doc

One import path for the interfaces, events, content classes, and functions a downstream package needs.
````

`````

```{toctree}
:maxdepth: 1
:hidden: true

python-api
```

## Configuration

`````{grid} 1 1 2 2
:gutter: 3

````{grid-item-card} ⚙️ Settings
:link: settings
:link-type: doc

Every registry record the package reads, with type and default.
````

````{grid-item-card} 📝 The provider form
:link: provider-form
:link-type: doc

Every field on the provider form, by tab, and which drivers show it.
````

````{grid-item-card} 🔌 Shipped drivers
:link: shipped-drivers
:link-type: doc

The six drivers that ship with the package, their defaults, and the settings each one offers.
````

````{grid-item-card} 📦 Install profiles and upgrades
:link: install-profiles
:link-type: doc

Every GenericSetup profile the package ships, what it installs, and the upgrade situation.
````

`````

```{toctree}
:maxdepth: 1
:hidden: true

settings
provider-form
shipped-drivers
install-profiles
```

## Interfaces

`````{grid} 1 1 2 2
:gutter: 3

````{grid-item-card} 🌐 Endpoints
:link: endpoints
:link-type: doc

Every REST endpoint and browser view the package publishes.
````

````{grid-item-card} 🖥️ Frontend
:link: frontend
:link-type: doc

The routes, settings, and components the volto-identity add-on registers.
````

````{grid-item-card} 📣 Events
:link: events
:link-type: doc

The events the package fires, and the normalized claim keys they carry.
````

````{grid-item-card} 🏷️ Claims released by the server layer
:link: claims
:link-type: doc

Endpoints, scopes, and claims released when a Plone site acts as an authorization server.
````

````{grid-item-card} 📜 Driver contract
:link: driver-contract
:link-type: doc

The `IDriver` interface and the rules a driver must satisfy.
````

`````

```{toctree}
:maxdepth: 1
:hidden: true

endpoints
frontend
events
claims
driver-contract
```

## Data and storage

`````{grid} 1 1 2 2
:gutter: 3

````{grid-item-card} 🗒️ The audit log
:link: audit-log
:link-type: doc

Event names, endpoints, recorded fields, retention settings, and the sink interfaces.
````

````{grid-item-card} 👥 Users and groups as content
:link: user-content
:link-type: doc

Registry records, marker contracts, and plugin behavior for keeping users and groups as content.
````

````{grid-item-card} 🪪 Profiles and groups
:link: profiles-and-groups
:link-type: doc

The `UserProfile` and `UserGroup` content types: fields, workflow states, containers, the profile gate, and claims refresh.
````

````{grid-item-card} 📄 Principal documents
:link: principal-documents
:link-type: doc

The JSON format users, groups, and identities are exported as, and read back from.
````

````{grid-item-card} 📊 Migration reports
:link: migration-reports
:link-type: doc

Every field a migration report carries, and what each one means.
````

`````

```{toctree}
:maxdepth: 1
:hidden: true

audit-log
user-content
profiles-and-groups
principal-documents
migration-reports
```

## Security and support

`````{grid} 1 1 2 2
:gutter: 3

````{grid-item-card} 🔐 Permissions
:link: permissions
:link-type: doc

The permissions the package declares and the roles that hold them.
````

````{grid-item-card} 🛡️ Security guarantees
:link: security-guarantees
:link-type: doc

The security properties the test suite enforces, and what to know before deploying.
````

````{grid-item-card} 🧱 Stability
:link: stability
:link-type: doc

What is settled and what may still change before 1.0.0.
````

`````

```{toctree}
:maxdepth: 1
:hidden: true

permissions
security-guarantees
stability
```

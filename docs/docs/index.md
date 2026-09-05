---
myst:
  html_meta:
    "description": "Multi-provider external authentication for Plone, built on authlib."
    "property=og:description": "Multi-provider external authentication for Plone, built on authlib."
    "property=og:title": "pas.plugins.identity"
    "keywords": "Plone, authentication, OAuth, OpenID Connect, OIDC, authlib, single sign-on"
---

# pas.plugins.identity

Multi-provider external authentication for Plone, built on [authlib](https://authlib.org/).

```{warning}
**Alpha software.** The current release is `1.0.0a0`.
Endpoints, registry keys, and the driver contract may change without a migration path until 1.0.0.
Read {doc}`reference/stability` for what is settled and what is not.
```

One canonical Plone user id maps to many external identities for the same person.
GitHub, Google, any OpenID Connect provider, another Plone site, or an emailed magic link.
You get that mapping without running a separate identity broker, and the package never guesses it.

## Start here

New to the package? Read {doc}`concepts/mental-model` first.
It names the six things this package deals with, shows what a sign-in actually does, and points you at the right quadrant for your role.

Then, by what you came to do:

- **Run something today**—{doc}`tutorials/federation-demo` starts two Plone sites in Docker and signs in to one against the other.
- **Set it up for real**—{doc}`how-to-guides/install`, then {doc}`how-to-guides/install-the-frontend`, then a recipe from {doc}`how-to-guides/providers/index`.
- **Something is broken**—{doc}`how-to-guides/troubleshoot` is organized by symptom.

`````{grid} 1 1 2 2
:gutter: 3

````{grid-item-card} 🚀 Tutorials
:link: tutorials/index
:link-type: doc

Learn by doing.
Run two Plone sites and sign in to one against the other.
````

````{grid-item-card} 🧭 How-to guides
:link: how-to-guides/index
:link-type: doc

Install the package and the frontend, configure a provider, troubleshoot a failure, migrate from another add-on, write your own driver.
````

````{grid-item-card} 📖 Reference
:link: reference/index
:link-type: doc

Endpoints, settings, the provider form, the frontend surface, events, claims, permissions, and the drivers that ship with the package.
````

````{grid-item-card} 💡 Concepts
:link: concepts/index
:link-type: doc

The mental model, the threat model, and why the design works the way it does.
````

````{grid-item-card} 🎨 Storybook
:link: https://collective.github.io/pas-plugins-identity/storybook/

Every component the Volto add-on ships, rendered with its props. Built from
this repository and published beside these pages.
````
`````

## The two layers

The package installs as a core, with one optional layer beside it.

`pas.plugins.identity`
:   Sign in with one or more external providers, link and unlink identities, an audit log of authentication events, and a control panel.
    Users and groups are content: installing the add-on adds a `UserProfile` and a `UserGroup` content type, each with a workflow, a dedicated catalog, and PAS plugins that serve user properties, user enumeration, and group membership from that catalog.
    See {doc}`concepts/users-as-content` and {doc}`concepts/profiles-and-groups`.

`pas.plugins.identity[server]`
:   An OAuth 2.1 and OpenID Connect authorization server, so a Plone site can be the provider that other applications sign in against.
    See {doc}`reference/claims`.

Core never imports from the server layer, and CI enforces that boundary rather than leaving it to discipline.
So `pip install pas.plugins.identity` with no extras is a configuration that is tested rather than assumed.

There is a third extra, `[sql]`, which is not a layer.
It adds one audit sink that writes to a relational database, and installs no profile.
See {doc}`reference/audit-log`.

Read {doc}`concepts/layers` for what each layer buys you and what it costs.

## What you need

| | |
|---|---|
| Plone | 6.2 |
| Python | 3.12, 3.13, or 3.14 |
| Frontend | Volto, developed against 19.3.0 |

Sign-in requires the Volto frontend.
Classic UI is not supported for sign-in yet; support for it is intended.
See {doc}`reference/stability`.

```{seealso}
Report a security vulnerability privately, using the instructions in [SECURITY.md](https://github.com/collective/pas-plugins-identity/blob/main/SECURITY.md).
For the properties the test suite enforces, see {doc}`reference/security-guarantees`.
For the reasoning behind each guarantee, see {doc}`concepts/threat-model`.
```

```{toctree}
:caption: Tutorials
:maxdepth: 2
:hidden: true

tutorials/index
```

```{toctree}
:caption: How-to guides
:maxdepth: 2
:hidden: true

how-to-guides/index
```

```{toctree}
:caption: Reference
:maxdepth: 2
:hidden: true

reference/index
```

```{toctree}
:caption: Concepts
:maxdepth: 2
:hidden: true

concepts/index
```

```{toctree}
:caption: Appendices
:maxdepth: 2
:hidden: true

glossary
genindex
```

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

One canonical Plone user id maps to many external identities for the same person.
GitHub, Google, ORCID, a generic OpenID Connect provider, an emailed magic link.
You get that mapping without running a separate identity broker, and the package never guesses it.

Everything else here is arranged around that one idea.
To read about it first, start with {doc}`concepts/identities`.

`````{grid} 1 1 2 2
:gutter: 3

````{grid-item-card} Tutorials
:link: tutorials/index
:link-type: doc

Learn by doing.
Run two Plone sites and sign in to one against the other.
````

````{grid-item-card} How-to guides
:link: how-to-guides/index
:link-type: doc

Install the package, configure a provider, migrate from another add-on, write your own driver.
````

````{grid-item-card} Reference
:link: reference/index
:link-type: doc

Endpoints, settings, events, claims, and the drivers that ship with the package.
````

````{grid-item-card} Concepts
:link: concepts/index
:link-type: doc

Why the design works the way it does, and what it refuses to do.
````
`````

## The three layers

The package installs in three layers, and you choose how many.

`pas.plugins.identity`
:   Core.
    Sign in with one or more external providers, link and unlink identities, an audit log of authentication events, and a control panel.
    Core works on its own with no extras.

`pas.plugins.identity[content]`
:   Content-backed user profiles and groups.
    This layer adds a `Profile` content type with a workflow, a dedicated catalog, and PAS plugins that serve user properties, user enumeration, and group membership from that catalog.
    See {doc}`concepts/profiles-and-groups`.

`pas.plugins.identity[server]`
:   An OAuth 2.1 and OpenID Connect authorization server, so a Plone site can be the provider that other applications sign in against.
    See {doc}`reference/claims`.

Core never imports from either optional layer, and the two optional layers do not import from each other.
CI enforces that boundary rather than leaving it to discipline.
So `pip install pas.plugins.identity` with no extras is a configuration that is tested rather than assumed.

Read {doc}`concepts/layers` for what that buys you and what it costs.

```{seealso}
Report a security vulnerability privately, using the instructions in [SECURITY.md](https://github.com/collective/pas-plugins-identity/blob/main/SECURITY.md).
For the properties the test suite enforces, see {doc}`reference/security-guarantees`.
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

# pas.plugins.identity

Multi-provider external authentication for Plone, built on
[authlib](https://authlib.org/).

One canonical Plone user id maps to many external identities — GitHub, Google,
ORCID, a generic OIDC provider, an emailed magic link — for the same human,
without running a separate identity broker. That mapping, and the fact that it
is never guessed, is what the rest of this package is arranged around.

```{toctree}
:maxdepth: 2
:caption: Using it

install
providers
audit-log
profiles
migration
```

```{toctree}
:maxdepth: 2
:caption: Extending it

events
drivers
```

```{toctree}
:maxdepth: 1
:caption: About

security
```

## What is here and what is not

The package installs in three layers, and you choose how many.

`pas.plugins.identity`
: Core. Log in with one or more external providers, link and unlink
  identities, an audit log of authentication events, and a control panel.
  Works on its own with no extras.

`pas.plugins.identity[profile]`
: Content-backed user profiles and groups. Adds a `Profile` content type with
  a workflow, a dedicated catalog, and PAS plugins that serve user properties,
  user enumeration and group membership from that catalog. See
  {doc}`profiles`.

`pas.plugins.identity[server]`
: An OAuth 2.1 / OIDC authorization server, so a Plone site can be the
  provider other applications log in against. Not yet released.

Core never imports from either optional layer, and the two do not import from
each other. That is enforced in CI rather than left to discipline, so
`pip install pas.plugins.identity` with no extras is a configuration that is
tested rather than assumed.

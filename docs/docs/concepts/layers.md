---
myst:
  html_meta:
    "description": "Why pas.plugins.identity keeps its authorization server in a separate layer and enforces the boundary in CI."
    "property=og:description": "Why pas.plugins.identity keeps its authorization server in a separate layer and enforces the boundary in CI."
    "property=og:title": "About the two layers"
---

(concepts-layers)=

# About the two layers

The package ships as a core plus one optional extra.

`pas.plugins.identity`
:   Sign in with external providers, link and unlink identities, an audit log, a control panel, and the content types that users and groups are.

`pas.plugins.identity[server]`
:   An OAuth 2.1 and OpenID Connect authorization server.

Core never imports from the optional layer.

Each is switched on by its own GenericSetup profile, named after the package that declares it.

```text
pas.plugins.identity:default
pas.plugins.identity.server:default
```

The add-ons control panel lists both, so the server layer is installed and uninstalled where every other add-on is.
It shows no version beside that entry, because it is named after a package rather than a distribution and there is no package metadata to read.

## There used to be three

Content-backed users and groups were a third layer, `[content]`, with a profile of its own.
They are not any more, and the reason is worth stating because it is the argument against the rest of this page taken too far.

A layer earns its boundary when the combinations it creates are ones somebody actually wants and somebody actually tests.
`[content]` failed both halves.
Its dependency, `plone.app.dexterity`, ships with Plone, so nobody was ever spared anything by leaving it out.
What the option bought instead was a second configuration of every code path that touches a user: a login that minted a `source_users` row here and a content object there, a property map that wrote to one store or the other, an offered email address that was settled by a guess on one site and asked about on the other.
Every bug found in the last week of that arrangement was in the seam.

So the two halves merged, and what is left is one layer that has one behaviour.

The `[server]` boundary survives on the test the other one failed.
Its dependency is `cryptography`, which is compiled, and a site that is not an authorization server has a real reason not to carry it.

## Why the remaining boundary is more than tidiness

Two layers that import freely are one layer with two names.
The moment core reaches into the server layer for something convenient, `pip install pas.plugins.identity` with no extras stops working, and it stops working at import time on somebody else's site rather than in CI.

An add-on that ships extras is making a promise about what each combination does.
The only way to keep that promise is to test the combinations, and the only way to keep the combinations meaningfully separate is to forbid the imports that would collapse them.

## CI enforces it, because discipline does not

The boundary is a contract checked by import-linter, and it runs in CI.

That distinction matters more than it sounds.
A boundary maintained by intention degrades quietly.
Somebody needs a value from the other layer, writes the import, sees green tests, and merges.
The contract was never violated in a way anybody noticed until the day a site installed the package with no extras at all.

```{important}
import-linter reads function bodies.
Moving an import inside a function does not dodge the contract, and it should not, because a deferred import is still a dependency.
```

## What core does instead of importing

Core reaches the server layer through the component architecture, and through events.

Core fires `IExternalIdentityAuthenticated`, `IIdentityLinked` and `IUserClaimsRefreshed`.
Anything that wants to know a person signed in subscribes to them; nothing has to be imported in either direction.
The audit sink and the driver registry have the same shape: a package publishes a utility, and whatever wants it asks the registry.

## How the server layer avoids knowing about profiles

When the site acts as an authorization server, it releases claims about a user.
Those values usually live on a `UserProfile` content object, but not for every userid: an account created before this add-on was installed, and not signed in with since, has no Profile.

The server layer branches on neither.
It asks PAS for a user property.

The profile plugin serves a Profile's fields as a property sheet, through an `IPropertiesPlugin` registered above `mutable_properties`.
So the same call returns Profile-backed values where a Profile exists and stock values where one does not, and the server layer never learns which kind of user it is looking at.

That is what the contract buys.
Not just a cleaner dependency graph, but a server layer with no configuration branch in it at all.

## Where to go next

-   {doc}`users-as-content` for why a user is a content object at all.
-   {doc}`profiles-and-groups` for what is done with the fields a Profile owns.
-   {doc}`/reference/claims` for what the server layer releases.

---
myst:
  html_meta:
    "description": "Why pas.plugins.identity ships as three independent layers and enforces the boundary in CI."
    "property=og:description": "Why pas.plugins.identity ships as three independent layers and enforces the boundary in CI."
    "property=og:title": "About the three layers"
---

(concepts-layers)=

# About the three layers

The package ships as a core plus two optional extras.

`pas.plugins.identity`
:   Sign in with external providers, link and unlink identities, an audit log, and a control panel.

`pas.plugins.identity[content]`
:   Content-backed user profiles and groups.

`pas.plugins.identity[server]`
:   An OAuth 2.1 and OpenID Connect authorization server.

Core never imports from either optional layer.
The two optional layers never import from each other.

Each layer is switched on by its own GenericSetup profile, named after the package that declares it.

```text
pas.plugins.identity:default
pas.plugins.identity.content:default
pas.plugins.identity.server:default
```

The add-ons control panel lists all three, so a layer is installed and uninstalled where every other add-on is.
The two optional entries show no version, because they are named after packages rather than distributions and there is no package metadata to read.

## Why the boundary is more than tidiness

Three layers that import freely are one layer with three names.
The moment core reaches into the content layer for something convenient, `pip install pas.plugins.identity` with no extras stops working, and it stops working at import time on somebody else's site rather than in CI.

An add-on that ships extras is making a promise about what each combination does.
The only way to keep that promise is to test the combinations, and the only way to keep the combinations meaningfully separate is to forbid the imports that would collapse them.

## CI enforces it, because discipline does not

The boundary is a contract checked by import-linter, and it runs in CI.

That distinction matters more than it sounds.
A boundary maintained by intention degrades quietly.
Somebody needs a value from the other layer, writes the import, sees green tests, and merges.
The contract was never violated in a way anybody noticed until the day a site installed the package without the extra.

```{important}
import-linter reads function bodies.
Moving an import inside a function does not dodge the contract, and it should not, because a deferred import is still a dependency.
```

## What core does instead of importing

Core reaches the optional layers through the component architecture.

The content layer registers an `IProfileSupport` utility.
Core looks that utility up, and gets `None` on a site that never installed the extra.
No import crosses the boundary in either direction, and the branch is a lookup rather than a `try`/`except ImportError`.

The same shape appears in the audit sink and in the driver registry.
A layer publishes a utility, and anything that wants it asks the registry.

## How the server layer avoids knowing about profiles

This is the sharpest example, because the two layers are genuinely related.

When the site acts as an authorization server, it releases claims about a user.
On a site with the `[content]` extra, those values live on a `UserProfile` content object.
On a site without it, they live in `mutable_properties`.

The server layer branches on neither.
It asks PAS for a user property.

The content layer serves its fields as a property sheet, through an `IPropertiesPlugin` registered above `mutable_properties`.
So the same call returns Profile-backed values where a Profile exists and stock values where one does not, and the server layer never learns which site it is on.

That is what the contract buys.
Not just a cleaner dependency graph, but a server layer with no configuration branch in it at all.

## Where to go next

-   {doc}`profiles-and-groups` for what the content layer does with the fields it owns.
-   {doc}`/reference/claims` for what the server layer releases.

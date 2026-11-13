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

## Users as content is a profile, not a layer

<!-- source: backend/src/pas/plugins/identity/profiles.zcml -->
<!-- source: backend/src/pas/plugins/identity/core/pas/plugin.py -->

`pas.plugins.identity:default` is two profiles, and installs both.

```text
pas.plugins.identity:core          authentication, providers, the control panel
pas.plugins.identity:contenttypes  users and groups as content
```

The split is in what a site installs, not in what Python imports.
Both halves are one package with one set of dependencies, and every module is loaded on every site.
What differs is the site: the `contenttypes` profile marks the site root with `IUsersAsContent`, and the code that has to decide where a user lives reads that marker.

A site that installs `core` alone keeps its users where Plone keeps them without this add-on.
The identity plugin writes a federated user into `source_users`, with a password nobody knows, and writes the provider's claims into the member's properties.

That second configuration is a seam of exactly the kind the next section warns about, and it existed once before.
It earns its place this time because nobody pays for it by accident.
The add-ons control panel offers only `default`, which installs both halves, so a site gets the second configuration only by naming `core` in its own `metadata.xml`.
A test module, `tests/core/test_core_only_site.py`, drives that configuration through a real login, so the seam has tests of its own.

## What earns a boundary

Two, and not more, because a layer has to earn its boundary twice over.

Its dependency must be one a site has a real reason not to carry, and the
combinations it creates must be ones somebody actually wants and somebody
actually tests.

`[server]` passes both. `cryptography` is compiled, so a site that is not an
authorization server has something to gain by leaving it out, and the two
combinations—with the extra and without it—are the two a deployment
actually picks between.

An optional layer that fails either test is not a smaller install. It is a
second configuration of every code path it touches, and every one of those
seams is somewhere a bug can live that neither combination's tests reach.

## Why the remaining boundary is more than tidiness

Two layers that import freely are one layer with two names.
The moment core reaches into the server layer for something convenient, depending on `pas.plugins.identity` with no extras stops working, and it stops working at import time on somebody else's site rather than in CI.

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

The same call serves a site with no Profiles at all.
On a site that installed `core` alone, every user's properties come from `mutable_properties`, and the server layer asks exactly the same question.

## Where to go next

-   {doc}`users-as-content` for why a user is a content object at all.
-   {doc}`profiles-and-groups` for what is done with the fields a Profile owns.
-   {doc}`/reference/claims` for what the server layer releases.

---
myst:
  html_meta:
    "description": "Every GenericSetup profile the package ships, what it installs, and the upgrade situation."
    "property=og:description": "Every GenericSetup profile the package ships, what it installs, and the upgrade situation."
    "property=og:title": "Install profiles and upgrades"
---

(reference-install-profiles)=

# Install profiles and upgrades

<!-- source: backend/src/pas/plugins/identity/profiles.zcml -->
<!-- source: backend/src/pas/plugins/identity/server/profiles.zcml -->
<!-- source: backend/src/pas/plugins/identity/upgrades/configure.zcml -->

## Profiles

| Profile id | Title | Version | Depends on | In the add-ons control panel |
|---|---|---|---|---|
| `pas.plugins.identity:default` | Install | 1014 | `core`, `contenttypes` | Yes |
| `pas.plugins.identity:core` | Authentication | 1000 | `plone.restapi:default` | No |
| `pas.plugins.identity:contenttypes` | Users and groups as content | 1000 | `core`, `plone.app.dexterity:default` | No |
| `pas.plugins.identity:rebuild-catalog` | Rebuild the user catalog |—| `contenttypes` | No |
| `pas.plugins.identity:initial` | Example content |—| `contenttypes` | No |
| `pas.plugins.identity:uninstall` | Uninstall |—|—| No |
| `pas.plugins.identity.server:default` | Authorization server | 1002 | `default` | Yes |
| `pas.plugins.identity.server:uninstall` | Uninstall the authorization server |—|—| No |

All are `EXTENSION` profiles.

### `pas.plugins.identity:default`

Holds no files of its own.
Its `metadata.xml` names `core` and `contenttypes` as dependencies, so applying it applies both, in that order.
It is the profile the add-ons control panel installs, and the one a policy package normally depends on.

### `pas.plugins.identity:core`

<!-- source: backend/src/pas/plugins/identity/profiles/core/ -->

Authentication, without users as content:

- the **Identity providers** control panel
- the `identity` PAS plugin, for extraction, authentication, credentials reset, and adding users and groups
- the browser layer
- the `personal_tools` actions in the user menu
- the records of `IIdentitySettings` in {doc}`settings`
- the `pas.plugins.identity: Export Identity Providers` permission in {doc}`permissions`

A site with this profile alone keeps its users in `source_users` and `mutable_properties`.
See {doc}`user-content` for what the identity plugin writes there.

### `pas.plugins.identity:contenttypes`

<!-- source: backend/src/pas/plugins/identity/profiles/contenttypes/ -->
<!-- source: backend/src/pas/plugins/identity/setuphandlers/__init__.py -->

Users and groups as content:

- the `UserProfile`, `UserGroup` and `PrincipalsContainer` content types
- `user_profile_workflow` and `user_group_workflow`
- the versioning policies for the two principal types
- the user catalog the two types are filed in
- the `identity_profile` PAS plugin, at the top of `IPropertiesPlugin`
- the records of `IProfileSettings` in {doc}`settings`, and the type records pointed at this package's own types
- every other permission in {doc}`permissions`
- the `IUsersAsContent` marker on the site root

#### Import and export steps

Beside the steps GenericSetup and Plone already register, this profile carries
one of its own.

| Step | File | What it does |
|---|---|---|
| `identity-catalog` | `identity-catalog.xml` | The user catalog's lexicon, indexes and metadata columns |

It exists because GenericSetup's own `catalog` step resolves its target with
`queryUtility(ICatalogTool)`, which answers `portal_catalog` and has no notion
of a second catalog. The filename differs for the same reason: a `catalog.xml`
here would be read by that step and applied to the site catalog.

The step is additive and re-runnable, and it exports as well as imports. It does
not populate what it creates—see
{doc}`/how-to-guides/extend/add-a-catalog-index`.

### `pas.plugins.identity:rebuild-catalog`

Re-catalogs every principal and reports what it repaired.

Apply it when enumeration or group membership returns stale answers—typically
after a release that changed what the catalog stores. See
{doc}`/how-to-guides/install/upgrade`.

### `pas.plugins.identity.server:default`

The authorization server: the OAuth and OpenID Connect endpoints in
{doc}`endpoints`, the client registry, the signing keys, and the consent screen.

It is its own entry in the add-ons control panel, with its own install and
uninstall button. The panel shows no version beside it, because the entry is
named after a package rather than a distribution.

### The uninstall profiles

Every installable profile has a matching uninstall profile, and uninstalling is
tested: the test installs, uninstalls, and asserts the site still works with no
plugin, registry key, or tool left behind.

`pas.plugins.identity:uninstall` removes both halves, whichever of them the site
has. Uninstalling removes the catalog, the content types and the workflows,
removes the `IUsersAsContent` marker, and forgets the `core` and `contenttypes`
profiles, so the next install applies them again. It leaves every `UserProfile`
object and its data exactly where it is.

## Upgrades

<!-- source: backend/src/pas/plugins/identity/upgrades/configure.zcml -->
<!-- source: backend/src/pas/plugins/identity/server/upgrades/configure.zcml -->

`pas.plugins.identity:default` is at version 1014. `upgrades/` holds one package
per version, each registering the steps that take a site to it, and
`portal_setup` offers them to a site installed against an earlier release.
`pas.plugins.identity.server:default` is at 1002, with its steps laid out the
same way in `server/upgrades/`.
{doc}`/how-to-guides/install/upgrade` lists what each step does.

Every step up to 1014 belongs to `default`. `core` and `contenttypes` start at
1000 and have no steps yet.

| Profile | Where its upgrades are offered |
|---|---|
| `default` | The add-ons control panel, and the {guilabel}`Upgrades` tab of `portal_setup` |
| `core`, `contenttypes` | The {guilabel}`Upgrades` tab of `portal_setup` |

The add-ons control panel upgrades a product's `default` profile and no other.
A release that adds a step to `core` or `contenttypes` therefore also adds a
step to `default` that upgrades both, so a site with the whole add-on keeps
upgrading from the control panel.

An upgrade step is for what a reapplied profile cannot carry. Everything else—a
registry record, a content type, a workflow, a plugin—reaches an existing site
**only if the profile is reapplied**.

This is what the alpha status means in practice. See {doc}`stability` for what
that implies, and {doc}`/how-to-guides/install/upgrade` for the procedure.

## Related

- {doc}`/how-to-guides/install/backend`—applying these
- {doc}`/how-to-guides/install/upgrade`—reapplying them
- {doc}`settings`—the records the install profiles write
- {doc}`permissions`—the role map each of them installs
- {doc}`user-content`—where users live with and without `contenttypes`
- {doc}`/concepts/layers`—why users as content is a profile of its own

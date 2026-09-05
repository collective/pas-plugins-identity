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

| Profile id | Title | Version |
|---|---|---|
| `pas.plugins.identity:default` | Install | 1000 |
| `pas.plugins.identity:rebuild-catalog` | Rebuild the user catalog |—|
| `pas.plugins.identity:uninstall` | Uninstall |—|
| `pas.plugins.identity.server:default` | Authorization server | 1000 |
| `pas.plugins.identity.server:uninstall` | Uninstall the authorization server |—|

All are `EXTENSION` profiles.

### `pas.plugins.identity:default`

One profile installs everything the core layer needs:

- the **Identity providers** control panel
- the `identity` PAS plugin, for extraction, authentication and credentials reset
- the `identity_profile` PAS plugin, at the top of `IPropertiesPlugin`
- the `UserProfile` and `UserGroup` content types
- `user_profile_workflow` and the group workflow
- the user catalog the two types are filed in
- the registry records in {doc}`settings`, pointed at this package's own types
- the permissions and rolemap in {doc}`permissions`

### `pas.plugins.identity:rebuild-catalog`

Re-catalogs every principal and reports what it repaired.

Apply it when enumeration or group membership returns stale answers—typically
after a release that changed what the catalog stores. See
{doc}`/how-to-guides/upgrade`.

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

Uninstalling removes the catalog, the content types and the workflows. It leaves
every `UserProfile` object and its data exactly where it is.

## Upgrades

```{important}
**There are no upgrade steps.**

`upgrades/configure.zcml` contains a commented-out example and nothing else. Both
installable profiles are at version 1000, and `portal_setup` will never offer to
upgrade this add-on.
```

A change to a registry record, a content type, a workflow or a plugin reaches an
existing site **only if the profile is reapplied**.

This is what the alpha status means in practice. See {doc}`stability` for what
that implies, and {doc}`/how-to-guides/upgrade` for the procedure.

### The one known migration

Users and groups as content used to be a separate `[content]` extra with a
profile of its own, merged into `pas.plugins.identity:default`. A site installed
before the merge needs the add-on reinstalled; nothing does it automatically.

## Related

- {doc}`/how-to-guides/install`—applying these
- {doc}`/how-to-guides/upgrade`—reapplying them
- {doc}`settings`—the records the install profile writes
- {doc}`permissions`—the rolemap it installs

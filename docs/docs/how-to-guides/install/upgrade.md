---
myst:
  html_meta:
    "description": "Take a new release of pas.plugins.identity into an existing Plone site."
    "property=og:description": "Take a new release of pas.plugins.identity into an existing Plone site."
    "property=og:title": "Upgrade"
---

(how-to-upgrade)=

# Upgrade

Take a new release into a site that already has this add-on.

<!-- source: backend/src/pas/plugins/identity/profiles/default/metadata.xml -->
<!-- source: backend/src/pas/plugins/identity/profiles/core/metadata.xml -->
<!-- source: backend/src/pas/plugins/identity/profiles/contenttypes/metadata.xml -->
<!-- source: backend/src/pas/plugins/identity/upgrades/ -->
<!-- source: backend/src/pas/plugins/identity/server/profiles/default/metadata.xml -->
<!-- source: backend/src/pas/plugins/identity/server/upgrades/ -->

`pas.plugins.identity:default` is at profile version **1014** and declares
upgrade steps, so `portal_setup` offers them to a site installed against an
earlier release.

| To | Does |
|---|---|
| 1001 | Lets a group hold a group: rewrites the allowed content types on the `UserGroup` FTI. |
| 1002 | Moves the profile's fields onto behaviors, in the FTI a site installed before them still has. |
| 1003 | Adds the `sortable_title` index to the identity catalog and reindexes `SearchableText` in the site catalog. |
| 1004 | Removes property map rows naming a field no login writes, and logs each one. |
| 1005 | Adds the global roles behavior to the group type, and applies its Manager-only permission to every group already in the site. |
| 1006 | Holds the Export Identity Providers permission to Manager alone, without acquisition. |
| 1007 | Creates the `confirm_email_at_first_login` setting, keeping every existing setting's value, and adds the `email_confirmation_pending` column to the identity catalog. |
| 1008 | Adds the `missing_fields` column to the identity catalog and reindexes every profile into it, so a profile gate explains a hold with the same list the profile itself counted. |
| 1009 | Adds Plone's `image_scales` column to the identity catalog and reindexes every profile into it, so `@users` builds a profile's picture URL without loading the profile. |
| 1010 | Activates `identity_profile` for `IUserIntrospection`, so `api.user.get_users()` and `listMembers()` include users who have a profile and no `source_users` account. |
| 1011 | Guards the login and group memberships of a profile with View Account Details, and maps it onto every profile already in the site. |
| 1012 | Creates the `client_ip_headers` setting, empty, keeping every existing setting's value. |
| 1013 | Adds the `personal_tools` actions that Volto's user menu is built from: Profile, Preferences, Sign-in methods and Site Setup. |
| 1014 | Records `pas.plugins.identity:core` and `pas.plugins.identity:contenttypes` as installed, and marks the site as keeping its users as content. Imports nothing: a site installed before the split already has everything both profiles install. |

`pas.plugins.identity:core` and `pas.plugins.identity:contenttypes` are at
profile version **1000**, and have no upgrade steps yet.

`pas.plugins.identity.server:default` is at profile version **1002**.

| To | Does |
|---|---|
| 1001 | Adds an empty `allowed_groups` to every registered OAuth client, so each one keeps admitting everybody until an operator restricts it. A registration that already has the key keeps its value. |
| 1002 | Adds Applications to the `personal_tools` actions, before Site Setup. Run it after the core profile's 1013. |

```{warning}
An upgrade step covers what a profile cannot carry on its own—a persistent
object written at install, or a value only a walk of the site can compute.
Everything else reaches a site by **reapplying the profiles**, which is step 4
below and is not optional.

This is what alpha means here. See {doc}`/reference/stability`.
```

## Before you upgrade

1. Back up the database. This is an alpha with no migration path; the ability to
   go back is the migration path.
2. Read `CHANGES.md` for the release you are taking.
3. Do it on a copy first.

## The general procedure

1. Update the requirement and reinstall the distribution.
2. Restart the Plone instance. ZCML changes do not take effect until it restarts.
3. Run the upgrade steps the add-ons control panel offers for the add-on.

4. Reapply the two profiles that hold the add-on's files, in this order:

   ```text
   pas.plugins.identity:core
   pas.plugins.identity:contenttypes
   ```

   Either from `portal_setup`, or by uninstalling and installing the add-on in
   the add-ons control panel. A site installed with `core` alone reapplies
   `core` only.

   Reapplying `pas.plugins.identity:default` is not the same thing. It holds no
   files of its own, and GenericSetup upgrades a dependency that is already
   installed rather than applying it again.

5. If the site runs the authorization server, reapply its profile too:

   ```text
   pas.plugins.identity.server:default
   ```

6. Check the four items under "Verify" in {doc}`/how-to-guides/install/backend`.

Reapplying a profile is safe for your data: it rewrites configuration, and leaves
every `UserProfile` and `UserGroup` object where it is.

## After a change to user or group metadata

Some releases change what the user catalog stores. When that happens, the
catalog holds values from the old shape until it is rebuilt.

Apply the rebuild profile:

```text
pas.plugins.identity:rebuild-catalog
```

It re-catalogs every principal and reports what it repaired. Run it when
enumeration or group membership returns stale answers after an upgrade.

## Verify

- The add-ons control panel lists the add-on, and the server layer separately if
  you use it.
- `acl_users` has both `identity` and `identity_profile`, or only `identity`
  on a site installed with `core` alone.
- The **Identity providers** control panel lists your providers, with their
  secrets intact.
- A sign-in through each provider still works, and the audit log records it.

Secrets are stored in the registry and survive a profile reapplication. If one is
missing, see {doc}`/concepts/secrets`.

## Next steps

- {doc}`/reference/stability`—what is settled and what is not
- {doc}`/reference/install-profiles`—every profile id and what it installs
- {doc}`/how-to-guides/operate/troubleshoot`—if the site looks installed and the control panel is empty

---
myst:
  html_meta:
    "description": "Take a new release of pas.plugins.identity into an existing Plone site."
    "property=og:description": "Take a new release of pas.plugins.identity into an existing Plone site."
    "property=og:title": "How to upgrade"
---

(how-to-upgrade)=

# How to upgrade

Take a new release into a site that already has this add-on.

<!-- source: backend/src/pas/plugins/identity/profiles/default/metadata.xml -->
<!-- source: backend/src/pas/plugins/identity/upgrades/ -->

`pas.plugins.identity:default` is at profile version **1007** and declares
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

`pas.plugins.identity.server:default` is at 1000 and declares none.

```{warning}
An upgrade step covers what a profile cannot carry on its own—a persistent
object written at install, or a value only a walk of the site can compute.
Everything else reaches a site by **reapplying the profile**, which is step 3
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
3. Reapply the profile:

   ```text
   pas.plugins.identity:default
   ```

   Either from `portal_setup`, or by uninstalling and installing the add-on in
   the add-ons control panel.

4. If the site runs the authorization server, reapply its profile too:

   ```text
   pas.plugins.identity.server:default
   ```

5. Check the four items under "Verify" in {doc}`install`.

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
- `acl_users` has both `identity` and `identity_profile`.
- The **Identity providers** control panel lists your providers, with their
  secrets intact.
- A sign-in through each provider still works, and the audit log records it.

Secrets are stored in the registry and survive a profile reapplication. If one is
missing, see {doc}`/concepts/secrets`.

## Next steps

- {doc}`/reference/stability`—what is settled and what is not
- {doc}`/reference/install-profiles`—every profile id and what it installs
- {doc}`troubleshoot`—if the site looks installed and the control panel is empty

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

```{warning}
**There are no GenericSetup upgrade steps in this release.**

Both installable profiles are at version 1000 and declare no upgrades. Nothing
in `portal_setup` will offer to upgrade this add-on, and a change to a registry
record, a content type, or a plugin reaches an existing site **only if you
reinstall**.

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

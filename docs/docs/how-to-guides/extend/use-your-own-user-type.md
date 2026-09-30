---
myst:
  html_meta:
    "description": "Keep a site's users as a content type of its own, created, catalogued and enumerated by pas.plugins.identity in place of UserProfile."
    "property=og:description": "Keep a site's users as a content type of its own, created, catalogued and enumerated by pas.plugins.identity in place of UserProfile."
    "property=og:title": "Use your own user type"
---

# Use your own user type

Make this package keep your site's users as a content type of your own—a
`Person`, say—instead of `UserProfile`.

Once the steps below are done, the package handles your type the way it handles
`UserProfile`. A first login creates it, `api.user.create` creates it, the user
catalog files it, and user enumeration, group membership, `@group-members`, the
catalog rebuild, the export and the consistency check all read it. No
`UserProfile` is created beside it.

## Before you start

- A Plone add-on of your own, with a GenericSetup profile that depends on
  `pas.plugins.identity:default`. See {doc}`/how-to-guides/install/backend`.
- Your content type, as a Dexterity type in that profile.

## Steps

<!-- source: backend/src/pas/plugins/identity/core/principal_types.py -->
<!-- source: backend/src/pas/plugins/identity/core/profiles.py, ensure_profile -->

1. Declare a marker that makes your type both a user and a Profile, in your
   package's `interfaces.py`:

   ```python
   from pas.plugins.identity.core.interfaces import IUserContent
   from pas.plugins.identity.core.interfaces import IUserProfile


   class IIdentityUser(IUserContent, IUserProfile):
       """A content type whose objects are this site's users."""
   ```

   `IUserContent` is what lets the package create your type when somebody adds a
   user. `IUserProfile` is what the user catalog's indexers and subscribers are
   registered for. A type that provides only `IUserContent` is created by
   `api.user.create` but is never created at login and never catalogued.

2. Register it as a behavior, in your package's `configure.zcml`:

   ```xml
   <plone:behavior
       name="mysite.identity_user"
       title="Site user"
       description="Objects of this type are the site's users."
       provides=".interfaces.IIdentityUser"
       />
   ```

   With no `factory`, the `provides` interface is also the marker applied to
   every object of the type.

3. Enable that behavior on your type, together with the three behaviors
   `UserProfile` gets its fields from, in your type's FTI:

   ```xml
   <property name="behaviors" purge="false">
     <element value="mysite.identity_user" />
     <element value="pas.plugins.identity.profile_details" />
     <element value="pas.plugins.identity.email_addresses" />
     <element value="pas.plugins.identity.group_membership" />
   </property>
   ```

   The user catalog reads its columns from these fields. See
   {doc}`/reference/profiles-and-groups` for what each one adds.

4. Bind the Profile workflow to your type, in your profile's `workflows.xml`:

   ```xml
   <object name="portal_workflow" meta_type="Plone Workflow Tool">
     <bindings>
       <type type_id="Person">
         <bound-workflow workflow_id="user_profile_workflow" />
       </type>
     </bindings>
   </object>
   ```

   A workflow of your own also works, provided the states your users sit in are
   listed in {guilabel}`Enumeration-active states`. A user in any other state is
   not found by user enumeration.

5. Allow your type in the principals container, in
   `profiles/default/types/PrincipalsContainer.xml`:

   ```xml
   <object name="PrincipalsContainer" meta_type="Dexterity FTI">
     <property name="allowed_content_types" purge="false">
       <element value="Person" />
     </property>
   </object>
   ```

6. Name your type in the registry, in `profiles/default/registry.xml`:

   ```xml
   <registry>
     <record name="pas.plugins.identity.user_content_type">
       <value>Person</value>
     </record>
   </registry>
   ```

   Installing `pas.plugins.identity` fills this record with `UserProfile` only
   when it is empty, so your profile's value survives a reinstall and a change
   to the container settings.

7. Optionally, keep groups in Plone's own `source_groups` rather than as
   content. Empty the group record in the same file:

   ```xml
   <record name="pas.plugins.identity.group_content_type">
     <value></value>
   </record>
   ```

   Adding a group then creates a `source_groups` group. Reads that look for
   group content look for `UserGroup` and find none.

8. Install your profile, or apply it to an existing site.

## Verify

1. Sign in with a provider as a user who has never signed in before.
2. Open the principals container. It holds a `Person` for that user, and no
   `UserProfile`.
3. Open {guilabel}`Site Setup` › {guilabel}`Users` and search for the user.
   They are listed.

## Known quirks

- The Volto add-on registers its profile view for `UserProfile` and its group
  view for `UserGroup`, by portal type. Your type renders with whatever view
  your own add-on registers for it.
- Objects of your type that existed before your profile was applied are not in
  the user catalog. Apply `pas.plugins.identity:rebuild-catalog` once to file
  them.

```{note}
The marker, the behavior, the workflow, the container and the record are
exercised together by `backend/tests/core/test_own_user_type.py`, which
registers them in Python. The ZCML and XML files above are the GenericSetup
spelling of the same configuration and are not run by the test suite.
```

## Related

- {doc}`/reference/user-content`—the records and the marker contracts
- {doc}`/reference/profiles-and-groups`—the fields `UserProfile` is built from
- {doc}`/concepts/users-as-content`—why a user is content here

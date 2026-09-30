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
- Your content type, as a Dexterity type in that profile. It needs no Python:
  every marker and field this package reads comes from behaviors it ships.

## Steps

<!-- source: backend/src/pas/plugins/identity/core/principal_types.py -->
<!-- source: backend/src/pas/plugins/identity/core/profiles.py, ensure_profile -->

<!-- source: backend/src/pas/plugins/identity/core/behaviors/configure.zcml -->

1. Enable {guilabel}`Site user` on your type, together with the three behaviors
   `UserProfile` gets its fields from, in your type's FTI:

   ```xml
   <property name="behaviors" purge="false">
     <element value="pas.plugins.identity.principal_user" />
     <element value="pas.plugins.identity.profile_details" />
     <element value="pas.plugins.identity.email_addresses" />
     <element value="pas.plugins.identity.group_membership" />
   </property>
   ```

   `pas.plugins.identity.principal_user` makes your type both a user, so the
   package creates it when somebody adds a user, and a Profile, so the user
   catalog files it. The other three supply the fields the catalog reads. See
   {doc}`/reference/profiles-and-groups` for what each one adds.

2. Bind the Profile workflow to your type, in your profile's `workflows.xml`:

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

3. Allow your type in the principals container, in
   `profiles/default/types/PrincipalsContainer.xml`:

   ```xml
   <object name="PrincipalsContainer" meta_type="Dexterity FTI">
     <property name="allowed_content_types" purge="false">
       <element value="Person" />
     </property>
   </object>
   ```

4. Name your type in the registry, in `profiles/default/registry.xml`:

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

5. Optionally, decide where groups go. Leave the group record alone to keep
   `UserGroup`, or change it in the same file:

   | To keep groups | Group record | Also |
   |---|---|---|
   | In Plone's own `source_groups` | `<value></value>` | Nothing |
   | As a type of your own | Your type's name | Steps 1 to 3 for that type, with `pas.plugins.identity.principal_group`, `pas.plugins.identity.group_membership` and `user_group_workflow` |

   With the record empty, adding a group creates a `source_groups` group, and
   reads that look for group content look for `UserGroup` and find none.

6. Install your profile, or apply it to an existing site.

```{warning}
Mark your type with the shipped behavior rather than with an interface of your
own that extends `IUserContent`. Registered as a behavior's `provides`, such an
interface stops Dexterity from answering the defaults of other behaviors'
`userid` and `login` fields. See {ref}`principal-behaviors`.
```

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
The behaviors, the workflow, the container and the records are exercised
together, for a user type and a group type, by
`backend/tests/core/principal_types/test_own_user_type.py`, which sets them up in Python. The
XML files above are the GenericSetup spelling of the same configuration and are
not run by the test suite.
```

## Related

- {doc}`/reference/user-content`—the records and the marker contracts
- {doc}`/reference/profiles-and-groups`—the fields `UserProfile` is built from
- {doc}`/concepts/users-as-content`—why a user is content here

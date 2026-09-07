---
myst:
  html_meta:
    "description": "The permissions pas.plugins.identity declares and the roles that hold them."
    "property=og:description": "The permissions pas.plugins.identity declares and the roles that hold them."
    "property=og:title": "Permissions"
---

(reference-permissions)=

# Permissions

The six permissions the package declares, and who holds them after a default
install.

<!-- source: backend/src/pas/plugins/identity/permissions.zcml -->
<!-- source: backend/src/pas/plugins/identity/profiles/default/rolemap.xml -->

| Permission id | Title | Roles site-wide |
|---|---|---|
| `pas.plugins.identity.userprofile.add` | Add User Profile | **nobody** |
| `pas.plugins.identity.usergroup.add` | Add User Group | **nobody** |
| `pas.plugins.identity.content.edit` | Edit Profile | Manager, Site Administrator |
| `pas.plugins.identity.content.editgroups` | Edit Profile Group Membership | Manager, Site Administrator |
| `pas.plugins.identity.content.editlogin` | Edit Profile Login | **Manager** |
| `pas.plugins.identity.content.view` | View Profile | Manager, Site Administrator |
| `pas.plugins.identity.content.viewpii` | View Personal Identifiable Information | Manager, Site Administrator |

Every one is declared with `acquire="False"`.

## Why the two add permissions are granted to nobody

That is deliberate, not an oversight.

Both content types are addable in exactly one place: the container the registry
names for them, where the package grants the permission to Manager and Site
Administrator **locally**. Granting it site-wide as well would make every folder
in the site a place a `UserProfile` can be created, which is the thing being
prevented.

## Why `acquire="False"` matters even with no roles listed

A permission nobody mentions is not a permission nobody has. Zope falls back to
whatever the object acquires, so the answer would change with where the folder
happens to be. Stating the permission with no roles pins it.

## The field permissions

`content.edit`, `content.editgroups`, `content.editlogin`, `content.view` and
`content.viewpii` are field permissions declared on the Profile schema and on
its behaviors. Each is also managed by `user_profile_workflow`, which decides
who may read and write a Profile in each of its states.

The rolemap entries above are the **site-wide floor** for anywhere the workflow
does not reach.

### Group membership is its own permission

`content.editgroups` is separate from `content.edit` and is **never granted to
the profile's owner, in any state**.

`group_ids` decides which groups a user is in, so writing it is granting yourself
roles.

### A login is its own permission, and it depends where you ask

`content.editlogin` is separate from `content.edit`, and it is the one
permission in this table whose answer differs between a Profile and the folder
Profiles are filed in.

| Asked about | Who holds it | Which form asks |
|---|---|---|
| A `UserProfile` | Manager | the edit form |
| The container | Manager, Site Administrator | the add form |

That is what "a Manager may change a login **after** the account exists" is made
of. `plone.autoform` checks a field's write permission against the form's
context, which is the container on an add form and the object on an edit form,
so the two grants answer two different questions.

`login` is half of the case-folded index user enumeration queries. Rewriting it
moves an account away from every sign-in, every Sharing entry written against
the old name, and every provider that maps a user by it.

The machine paths that mint an account are unaffected: `doAddUser` elevates to
Manager and writes the field through the Dexterity factory, which does not
consult a field permission at all.

### Personal information is its own permission

`content.viewpii` is separate from `content.view` so a site can let members find
each other without publishing everybody's email address.

The workflow never grants it to `Member`, in any state.

## Permissions this package uses but does not declare

| Permission | Used by |
|---|---|
| `Manage portal` | the provider and client control panels, the audit log, driver listing, key rotation |
| `Manage users` | `@user-account`, and `@group-members` unless the caller is in the group |

See {doc}`endpoints` for which endpoint enforces which.

## Related

- {doc}`user-content`—the content types these protect
- {doc}`profiles-and-groups`—the workflow that grants them per state
- {doc}`security-guarantees`—the properties the test suite enforces

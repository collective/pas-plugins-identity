---
myst:
  html_meta:
    "description": "Registry records, marker contracts, and plugin behavior for keeping users and groups as content."
    "property=og:description": "Registry records, marker contracts, and plugin behavior for keeping users and groups as content."
    "property=og:title": "Users and groups as content"
---

(reference-user-content)=

# Users and groups as content

The mechanism that lets a Dexterity type *be* a user.

For why it is built this way, read {doc}`/concepts/users-as-content`. For the
types this package ships on top of it, read {doc}`profiles-and-groups`.

## Registry records

<!-- source: backend/src/pas/plugins/identity/core/pas/plugin.py -->
<!-- source: backend/src/pas/plugins/identity/core/principal_types.py -->
<!-- source: backend/src/pas/plugins/identity/core/subscribers/principals.py -->

Four records control the mechanism. All four are empty in the schema, which
means the feature is off and Plone's own plugins do the work.

| Record | Names |
|---|---|
| `pas.plugins.identity.user_content_type` | Portal type created when somebody adds a user. Must provide `IUserContent`. |
| `pas.plugins.identity.user_container_path` | Where those objects are created, relative to the site root. |
| `pas.plugins.identity.group_content_type` | Portal type created when somebody adds a group. Must provide `IGroupContent`. |
| `pas.plugins.identity.group_container_path` | Where those objects are created, relative to the site root. |

Both records of a pair must be set. A type with nowhere to go would fail at the
moment somebody adds a user, which is the worst time to discover a configuration
gap.

None of the four is on the settings form, and a save through the control panel
never writes them.

| Records | Written by | When |
|---|---|---|
| The two paths | A subscriber, from the container records | At install, and whenever a container record changes |
| The two types | The install handler, `UserProfile` and `UserGroup` | At install, and only into a record that is empty |

So moving the container in the control panel needs no reinstall, and a type a
site names in its own GenericSetup profile stays named. See
{doc}`/how-to-guides/extend/use-your-own-user-type`.

What an empty type record means depends on who reads it.

| Reader | Empty user or group type record |
|---|---|
| Adding a user or a group | Declines. `source_users` or `source_groups` does the work. |
| Everything that finds, lists, catalogues, exports or checks principals | Reads as `UserProfile` or `UserGroup` |

## The marker contracts

<!-- source: backend/src/pas/plugins/identity/core/interfaces.py -->

| Interface | Attributes it promises | Declared on the interface | Object's id in its container must equal |
|---|---|---|---|
| `IUserContent` | `userid`, `login`, `group_ids` | `userid`, `login` | `userid` |
| `IGroupContent` | `group_id`, `group_ids` | `group_id` | `group_id` |

| Attribute | Meaning |
|---|---|
| `userid` | The canonical Plone userid. Assigned once, never changed. |
| `login` | The name the user signs in with. |
| `group_id` | The canonical group id. Assigned once, never changed. |
| `group_ids` | On a user, the groups it belongs to. On a group, the groups it is nested inside, in addition to the group it is filed in. |

`group_ids` is supplied by the `pas.plugins.identity.group_membership` behavior.
**Neither interface declares it as an `Attribute`, deliberately.** Dexterity
answers a missing attribute from the schema's field default and finds the type's
own schema first, so an inherited `Attribute` would shadow the behavior's field.

`IGroupContent` declares no members accessor. Membership is named by each user's
`group_ids` and is read from there.

(principal-behaviors)=

### Marking a type of your own

<!-- source: backend/src/pas/plugins/identity/core/behaviors/principal.py -->
<!-- source: backend/src/pas/plugins/identity/core/behaviors/configure.zcml -->

Two behaviors give a type of your own both markers it needs.

| Behavior | Title | Marker applied | Which is |
|---|---|---|---|
| `pas.plugins.identity.principal_user` | Site user | `IPrincipalUser` | `IUserContent` and `IUserProfile` |
| `pas.plugins.identity.principal_group` | Site group | `IPrincipalGroup` | `IGroupContent` and `IUserGroup` |

Both live in `pas.plugins.identity.core.behaviors.principal`. Each has a
factory, and its `provides` interface declares nothing: the markers arrive as
the behavior's `marker` instead.

| Marked with | Dexterity's default for another behavior's `login` field |
|---|---|
| A shipped behavior above | Answered |
| An interface extending `IUserContent`, registered as a behavior's `provides` | `AttributeError`: the lookup reads `default` off `IUserContent.login` and stops there |

The same applies to `userid`, and to `group_id` on a group type.

### A group's global roles

`global_roles` on a group is supplied by the
`pas.plugins.identity.global_roles` behavior—the site-wide roles every member
of the group holds, the same ones the groups control panel sets.

**Nothing is stored on the content object**, and that is the design rather than
an omission. The behavior has a factory: every read asks `portal_groups` and
every write goes to it, so the field and the control panel cannot disagree.
A stored copy would be a second source of truth, and the moment anybody used
the control panel the two would differ with no way to tell which was right.

Because it stores nothing, read it by adapting rather than as an attribute:

```python
from pas.plugins.identity.core.behaviors.roles import IGlobalRoles

IGlobalRoles(group).global_roles            # ('Editor',)
IGlobalRoles(group).global_roles = ('Editor', 'Reviewer')
```

`getattr(group, 'global_roles')` would answer with a shadow attribute nothing
else consults. The export and import paths adapt for the same reason.

Writing it grants roles, so it carries `content.editroles`, which is granted to
**Manager alone**. See {doc}`permissions`.

A layer that stores membership some other way should implement
`IGroupManagement` itself rather than claim `IUserContent`.

Providing `IUserContent` does not make a type a credential store. See
{ref}`credential-storage`.

## When the plugin declines

The plugin returns false, and the stock plugin acts instead, in **all** of these
cases.

| Case | Logged? |
|---|---|
| The content type record is empty | no |
| The container path record is empty | no |
| The container path does not resolve to an object | warning |
| The named portal type is not a Dexterity type | warning |
| The named type does not provide the required marker | warning |
| The named type's schema or class fails to load | warning |

A type provides the marker when any of these does:

| Route | Example |
|---|---|
| The type's schema | `UserProfile`, whose schema extends `IUserContent` |
| A behavior's schema, or its marker | `pas.plugins.identity.principal_user`; see {ref}`principal-behaviors` |
| The content class | `<class><implements interface="…" /></class>` in ZCML |

Declining is the protocol rather than an error: `ZODBUserManager.doAddUser`
returns false on a duplicate id for the same reason. An unset record logs nothing
because unset is the default.

## Plugin ordering

The plugin must be registered **first** for both `IUserAdderPlugin` and
`IGroupManagement`. Both interfaces are walked until a plugin returns true, and
`source_users` and `source_groups` never decline—so registered below either of
them, this plugin is never reached.

Installing the package moves it to the top of both interfaces.

```{warning}
Reordering PAS plugins so this one sits below `source_users` or `source_groups`
switches the feature off. **No error is raised and nothing is logged.** Users and
groups are created as stock records again, and existing content-backed ones are
left where they are.
```

## Which plugin does what

| Plugin | Does |
|---|---|
| `identity` | Creates user and group objects, and authenticates. |
| `identity_profile` | Enumerates them, serves their properties, and deletes them. |

Installing the package installs both. One without the other gives you a user that
cannot be found: PAS looks a principal back up immediately after adding it.

<!-- source: backend/src/pas/plugins/identity/core/profiles.py, ensure_profile -->

`identity_profile` enumerates whatever type the records name, provided its
objects are filed in the user catalog: a user object has to provide
`IUserProfile` as well as `IUserContent`, and a group object `IUserGroup` as
well as `IGroupContent`.

A login asks the type for `IUserContent`, the same question the adder asks, and
then asks the object it created for `IUserProfile`.

| The user type | Created at login | Created by `api.user.create` | Enumerated by `identity_profile` |
|---|---|---|---|
| Provides `IUserContent` and `IUserProfile` | yes | yes | yes |
| Provides `IUserContent`, and a subscriber marks its objects `IUserProfile` when added | yes | yes | the marked objects |
| Provides `IUserContent`, and the object created is not marked | no: the object is removed again, and logged | yes, and fails at `setMemberProperties` unless another plugin enumerates it | no |
| Provides `IUserContent`, and is not allowed in the principals container | no, and logged | in the container the user container path record names, when that container allows it | no |
| Does not provide `IUserContent` | no, and logged | no: `source_users` adds the user | no |

```{important}
A user type whose objects are not filed in the user catalog is yours to create at
login and yours to enumerate. See {doc}`/how-to-guides/extend/use-your-own-user-type`.
```

(credential-storage)=

## Credential storage

By default the password of a user created this way is written to `source_users`,
not to the content object.

To keep the credential elsewhere, register an adapter from your content type to
`ICredentialStorage`:

| Method | Returns |
|---|---|
| `set_password(password)` | Nothing. Stores a password, hashed. |
| `check_password(password)` | Whether a password matches the stored one. False when nothing is stored. |

When the adaptation succeeds, core writes nothing to `source_users`.

| Situation | Result |
|---|---|
| An empty password | Never stored anywhere. |
| An externally authenticated user | No `source_users` account. The content object is the record they are. |
| Nothing claims the login | The login still succeeds. The principal exists as an identity and nothing else, and a warning names the type that was not created. |

A subscriber to `IExternalIdentityAuthenticated` creates the object—this
package's own, or yours. The plugin writes nothing itself.

```{warning}
**Never store a credential in a Dexterity field.** A field is serialized by
`plone.restapi`, exported by GenericSetup, indexed by the catalog, and
snapshotted by versioning. An annotation is invisible to the first three by
construction.

Versioning is the exception: CMFEditions copies annotations into a snapshot, so
the package registers a modifier that keeps the hash out of the version
repository, and a superseded password is not recoverable from a profile's
history.

The password behavior this package ships keeps a hash in an annotation for this
reason.
```

## Deleting a user

`api.user.delete` removes the content object, through `IUserManagement` on the
`identity_profile` plugin. The users listing offers the button because the plugin
also provides `IDeleteCapability`.

| Deleted with the account | Left behind |
|---|---|
| The content object | The identity records |
| Local roles, revoked by Plone and not restored by a later sign-in | The audit entries |

A login through an identity whose account is gone **recreates the object** and
logs a warning naming the userid.

```{warning}
Deleting a user does not erase everything the site holds about them.

The identity record keeps a snapshot of the claims the provider last sent, which
typically includes an address and a name. The audit entries keep the login
history, with the IP address and user agent as well on a site that has switched
that on. Both are keyed to a userid that no longer resolves to anybody, and
neither is reachable through `@users`.

A deployment with an erasure obligation has to remove them deliberately: unlink
the identities in the {guilabel}`Identities` panel **before** deleting the user,
which also drops the store's record of them.
```

## Refusals

| Operation | Result | Reason |
|---|---|---|
| A group inside itself | `addPrincipalToGroup` returns false | It would grant nothing, and the edit form would show a row nobody can account for. A group inside a *different* group is supported. |
| Choosing a container at creation time | Not accepted | The registry records decide. `doAddUser` takes a login and a password only, and `@users` POST accepts no container. |
| `updateGroup`, `setRolesForGroup` | Return false | Declared by `IGroupManagement` and never called by PlonePAS's group tool, which edits a group through the group object and routes roles to a role manager. Returning false beats reporting a success that did nothing. |
| `doChangeUser` | Raises `RuntimeError` | The error PlonePAS expects from a plugin that cannot set a password. See {ref}`credential-storage`. |

## Related

- {doc}`/concepts/users-as-content`—why a user is content here
- {doc}`profiles-and-groups`—the two types this package ships
- {doc}`settings`—the four records, with their defaults
- {doc}`/how-to-guides/extend/use-your-own-user-type`—a site's own type, in place of `UserProfile`
- {doc}`permissions`—what protects the objects

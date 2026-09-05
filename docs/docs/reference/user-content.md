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

Four records control the mechanism. All four are empty by default, which means
the feature is off and Plone's own plugins do the work.

| Record | Names |
|---|---|
| `pas.plugins.identity.user_content_type` | Portal type created when somebody adds a user. Must provide `IUserContent`. |
| `pas.plugins.identity.user_container_path` | Where those objects are created, relative to the site root. |
| `pas.plugins.identity.group_content_type` | Portal type created when somebody adds a group. Must provide `IGroupContent`. |
| `pas.plugins.identity.group_container_path` | Where those objects are created, relative to the site root. |

Both records of a pair must be set. A type with nowhere to go would fail at the
moment somebody adds a user, which is the worst time to discover a configuration
gap.

Edit them in {menuselection}`Site Setup --> Identity`.

```{note}
Installing the package sets all four and keeps them pointed at its own types and
container. It derives them from the container settings through a subscriber, so
moving the container in the control panel does not require a reinstall. See
{doc}`settings`.
```

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
| `group_ids` | On a user, the groups it belongs to. On a group, the groups it is nested inside. |

`group_ids` is supplied by the `pas.plugins.identity.group_membership` behavior.
**Neither interface declares it as an `Attribute`, deliberately.** Dexterity
answers a missing attribute from the schema's field default and finds the type's
own schema first, so an inherited `Attribute` would shadow the behavior's field.

`IGroupContent` declares no members accessor. Membership is named by each user's
`group_ids` and is read from there.

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
| The named type's schema does not provide the required marker | warning |
| The named type's schema fails to load | warning |

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

```{important}
If you point the records at a content type of your own, make sure something on
the site enumerates it. `UserProfile` and `UserGroup` are enumerated by the
plugin this package installs; another type is your responsibility.
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
- {doc}`permissions`—what protects the objects

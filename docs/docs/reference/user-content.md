---
myst:
  html_meta:
    "description": "Registry records, marker contracts, and plugin behavior for keeping users and groups as content."
    "property=og:description": "Registry records, marker contracts, and plugin behavior for keeping users and groups as content."
    "property=og:title": "Users and groups as content reference"
---

(reference-user-content)=

# Users and groups as content reference

This page describes the core mechanism.
For why it is built this way, read {doc}`/concepts/users-as-content`.
For the content types this package ships, read {doc}`/reference/profiles`.

## Registry records

Four records control the mechanism.
All four are empty by default, which means the feature is off and Plone's own plugins do the work.

`pas.plugins.identity.user_content_type`
:   Portal type created when somebody adds a user.
    The type must provide `IUserContent`.
    A type that does not is refused, and no object is created.

`pas.plugins.identity.user_container_path`
:   Where those objects are created, as a path relative to the site root.
    Required alongside the type.

`pas.plugins.identity.group_content_type`
:   Portal type created when somebody adds a group.
    The type must provide `IGroupContent`.

`pas.plugins.identity.group_container_path`
:   Where those objects are created, as a path relative to the site root.
    Required alongside the type.

Both records of a pair must be set.
A type with nowhere to go would fail at the moment somebody adds a user, which is the worst time to discover a configuration gap.

You can edit all four in {menuselection}`Site Setup --> Identity`.

```{note}
Installing the add-on sets all four for you and keeps them pointed at its own types and container.
It derives them from the container settings through a subscriber, so moving the container in the control panel does not require a reinstall.
```

## The `IUserContent` contract

A Dexterity type providing `IUserContent` must supply three attributes.

`userid`
:   The canonical Plone userid.
    Assigned once and never changed.

`login`
:   The name the user signs in with.

`group_ids`
:   Ids of the groups the user belongs to.

The object's id within its container must equal `userid`.

Providing `IUserContent` does not make a type a credential store.
See [Credential storage](#credential-storage).

## The `IGroupContent` contract

A Dexterity type providing `IGroupContent` must supply one attribute.

`group_id`
:   The canonical group id.
    Assigned once and never changed.

The object's id within its container must equal `group_id`.

`IGroupContent` declares no members accessor.
Membership is named by each user's `group_ids` and is read from there.

## When the plugin declines

The plugin returns false, and the stock plugin acts instead, in all of these cases.

- The content type record is empty.
- The container path record is empty.
- The container path does not resolve to an object.
- The named portal type is not a Dexterity type.
- The named type's schema does not provide the required marker.
- The named type's schema fails to load.

Declining is the protocol rather than an error.
`ZODBUserManager.doAddUser` returns false on a duplicate id for the same reason.

A record that names something the site cannot use logs a warning.
An unset record does not, because unset is the default and the overwhelmingly common case.

## Plugin ordering

The plugin must be registered **first** for both `IUserAdderPlugin` and `IGroupManagement`.

Both interfaces are walked until a plugin returns true, and `source_users` and `source_groups` never decline.
Registered below either of them, this plugin is never reached.

Installing the add-on moves the plugin to the top of both interfaces.

```{warning}
Reordering PAS plugins so that this plugin sits below `source_users` or `source_groups` switches the feature off.
No error is raised and no message is logged.
Users and groups are created as stock records again, and existing content-backed ones are left where they are.
```

(credential-storage)=

## Credential storage

By default the password of a user created this way is written to `source_users`, not to the content object.

To keep the credential elsewhere, register an adapter from your content type to `ICredentialStorage`.

`set_password(password)`
:   Store a password, hashed.

`check_password(password)`
:   Return whether a password matches the stored one.
    Returns false when nothing is stored.

When the adaptation succeeds, core writes nothing to `source_users`.

An empty password is never stored anywhere.
An externally authenticated user has no password, and a blank one is not a credential.

Nor does an externally authenticated user get a `source_users` account of their own.
The content object is the record they are, and a subscriber to `IExternalIdentityAuthenticated` creates it: this package's own, or yours.
The plugin writes nothing itself.
If nothing claims the login, it still succeeds and the principal exists as an identity and as nothing else; a warning is logged naming the type that was not created, because nothing here can create it for you.

```{warning}
Never store a credential in a Dexterity field.
A field is serialized by `plone.restapi`, exported by GenericSetup, indexed by the catalog, and snapshotted by versioning. An annotation is invisible to the first three by construction. Versioning is the exception: CMFEditions copies annotations into a snapshot, so the add-on registers a modifier that keeps the hash out of the version repository, and a superseded password is not recoverable from a Profile's history.
The password behavior this package ships keeps a hash in an annotation for this reason.
```

## Which plugin does what

The `identity` plugin creates user and group objects, and authenticates.
The `identity_profile` plugin enumerates them, serves their properties, and deletes them.

Answering "which users match this?" without waking every object requires a catalog, and so does deciding whether a user is one this plugin holds, so both live with the plugin that owns the catalog.
PAS looks a principal back up immediately after adding it, so the two halves are not independent: one plugin without the other gives you a user that cannot be found.
Installing the add-on installs both.

```{important}
If you point these records at a content type of your own, make sure something on the site enumerates it.
`UserProfile` and `UserGroup` are enumerated by the plugin this package installs; another type is your responsibility.
```

## Deleting a user

`api.user.delete` removes the content object, through `IUserManagement` on the `identity_profile` plugin.
The users listing offers the button because the plugin also provides `IDeleteCapability` and says it can.

The identity records are deliberately left behind.
An identity outliving an account is by design, because it is what lets the same person sign back in under the same userid, so removing one is a separate decision an operator makes in the {guilabel}`Identities` panel.
A login through an identity whose account is gone recreates the object and logs a warning naming the userid, so the case is reported rather than silent.

The audit entries are left behind for the same reason: they are the record of how an account was used, and discarding it on deletion would mean an operator investigating an incident loses exactly the accounts worth investigating.

```{warning}
Deleting a user therefore does not erase everything the site holds about them.
The identity record keeps a snapshot of the claims the provider last sent, which typically includes an address and a name.
The audit entries keep the login history, with the IP address and user agent as well on a site that has switched that on.
Both are keyed to a userid that no longer resolves to anybody, and neither is reachable through `@users`.

A deployment with an erasure obligation has to remove them deliberately: unlink the identities in the {guilabel}`Identities` panel *before* deleting the user, which also drops the store's record of them.
Local roles are revoked by Plone on deletion and are not restored by a later sign-in, so this is a data-retention question rather than an access one.
```

## Refusals

The following are refused rather than supported.

A group inside itself
:   `addPrincipalToGroup` returns false when the principal and the group are the same id.
    It would grant nothing and mean nothing, and the edit form would show a row nobody can account for.
    A group inside a *different* group is supported; see {doc}`/concepts/profiles-and-groups`.

A container chosen at creation time
:   The registry records decide where objects are created.
    `doAddUser` accepts a login and a password only, and `@users` POST accepts no container.

`updateGroup` and `setRolesForGroup`
:   Declared by `IGroupManagement` and never called by PlonePAS's group tool, which edits a group through the group object and routes roles to a role manager.
    Both return false rather than reporting a success that did nothing.

`doChangeUser`
:   Declared by `IUserManagement`, and refused with the `RuntimeError` PlonePAS expects from a plugin that cannot set a password.
    Where a credential lives is a separate question with a separate answer; see {ref}`credential-storage`.

```{seealso}
{doc}`/concepts/users-as-content`
{doc}`/reference/profiles`
```

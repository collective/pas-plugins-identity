---
myst:
  html_meta:
    "description": "How core lets a site keep its users and groups as content without knowing what content."
    "property=og:description": "How core lets a site keep its users and groups as content without knowing what content."
    "property=og:title": "About users as content"
---

(concepts-users-as-content)=

# About users as content

Plone keeps users in `source_users` and groups in `source_groups`, as records in a BTree.

A site that wants a member directory, an editable profile page, or a reviewable group wants those to be content instead.
Core makes that possible without ever knowing what the content is.

The `[content]` extra is one answer to that question, and the reason the mechanism exists.
It is not the only permitted answer, which is why the mechanism lives in core and the content types do not.
For what the extra itself does with it, read {doc}`/concepts/profiles-and-groups`.

## Core declares the contract, a layer provides it

`IUserContent` and `IGroupContent` are markers that a Dexterity type provides.

Core declares them and creates objects of a type it has never heard of.
A layer implements them on a type it owns.
That is the direction every extension point in this package runs in, and here it is the only direction that works: core has to create a user on a site whose content types were written after core was.

A user type promises `userid`, `login`, and `group_ids`.
A group type promises `group_id`.
Core reads nothing else, so the rest of the schema belongs entirely to the layer.

## The object's id is the identifier

For both types, the object's id within its container *is* the `userid` or the `group_id`.

That is what lets core resolve a user in a single traversal rather than a search.
It is not a constraint invented for the interface.
An opaque userid never changes, so the object never has to be renamed, and a rename is the one operation that strands a URL somebody bookmarked.

This single promise is what several later refusals rest on.

## Working by declining

Core implements the `IUserAdderPlugin` interface from PAS and the `IGroupManagement` interface from PlonePAS.

Both of those interfaces are walked plugin by plugin until one returns true.
So both halves of this feature work by *declining*: with no content type configured, which is every site until somebody says otherwise, the plugin returns false and `source_users` or `source_groups` does the job exactly as it always did.

Nothing about a site that has not set the records changes.
That is the whole reason the interfaces are activated on install rather than lazily, because activating them lazily would mean reinstalling the add-on after setting a registry record, which is the kind of step nobody remembers and nothing reports.

## Being asked first is load-bearing

A plugin that declines has to be asked before a plugin that never declines.

`source_users` and `source_groups` always succeed.
Registered below either of them, this plugin is never reached, and nothing reports it: the site simply keeps creating stock users while every test that calls the plugin directly stays green.
So install moves the plugin to the top of both interfaces, for the same reason the `[content]` layer sits at the top of `IPropertiesPlugin`.

This is the failure mode the design is most exposed to, and it is silent in both directions.
The test suite therefore asserts the plugin's *position*, not merely that it is registered.

```{note}
Ordering here is behavior, not tidiness.
If you reorder plugins in {menuselection}`Site Setup --> Users and Groups --> PAS plugins`, moving this plugin below `source_users` switches the feature off without any error.
```

## The credential is not a field

A user created this way gets a content object, and a password that lives somewhere else.

A Dexterity field holding a credential is serialized by `plone.restapi`, exported by GenericSetup, indexed by the catalog, and kept in every version snapshot.
Those are four separate disclosure paths, and each one has to be remembered separately by everyone who ever touches the schema.
So the content object is the record a user *is*, and `source_users` stays the credential store.

A user added through the ordinary API therefore ends up as somebody who can actually sign in, with the password where Plone has always kept one.

An externally authenticated user gets no `source_users` account at all.
They have no password to store, and the content object is already the record they are: the plugin enumerates it, and a site that opted into {ref}`credential-storage` authenticates against it.
A row beside it would be a second record of the same person, kept in step by nothing.
On a site that has *not* configured user content, the `source_users` account is still created for them, because there it is the only record they have.

A site that would rather keep the credential with the rest of the user opts into `ICredentialStorage`, takes on those four questions deliberately, and core then has nothing to delegate.
The `[content]` extra ships that as an opt-in behavior which keeps a hash in an annotation rather than in a field.

## Where a user is created is a setting, not a parameter

Two registry records name the content type and the container for users, and two more do the same for groups.

They are settings and nothing else.
There is no way to ask for a user in a particular container at creation time, and that is deliberate rather than unfinished.

`doAddUser` receives a login and a password, and nothing more.
The same method is reached from `api.user.create`, from the join form, and from the first login of an externally authenticated user.
Three of those four callers have no request to read a container from, so a per-request container would be honored on one path and silently ignored on the others.

The deeper reason is the single-traversal promise.
If users can live in more than one container, `container.get(userid)` no longer knows which container to ask, and every lookup becomes a scan or needs a second record saying where each user went.

To move where users are created, change the records.
Everything created afterward goes to the new container, and the catalog is not scoped to any container, so what is already there keeps working.

## Membership lives on the member

`group_ids` is a field on the user, and a group carries no list of its members.

`getGroupsForPrincipal` runs on every permission check that touches a local role.
Listing a group's members does not.
Keeping membership on the member makes the hot question a single metadata read, and leaves the cold question to a catalog query in whichever layer owns enumeration.

`IGroupContent` therefore has no members accessor, and will not grow one.
An accessor would be a second copy of the same fact, and the two would drift the first time anything wrote to one without the other.

Group nesting is refused for a related reason.
A group whose members are groups makes `getGroupsForPrincipal` recursive, and a recursive answer computed from catalog metadata stops being a single lookup.
That is the property the whole design rests on, so nesting is refused rather than stored and answered slowly.

## Core creates, but does not enumerate

Core can make a user.
It cannot answer which users match a search, because doing so without waking every object needs a catalog, and core does not ship one.

The two are not independent.
PAS looks a principal straight back up after adding it, so a site that sets the records without also running a layer that enumerates gets a user that cannot be found.

```{important}
Do not point the registry records at a content type unless something on the site enumerates that type.
The `[content]` extra does this for you, and points the records at itself.
```

```{seealso}
{doc}`/reference/user-content` for the records and the contracts.
{doc}`/concepts/profiles-and-groups` for what the `[content]` extra builds on top.
{doc}`/concepts/layers` for why core declares an interface an extra provides.
```

---
myst:
  html_meta:
    "description": "Why users and groups are content objects here, and how the plugin creates one without knowing what type it is."
    "property=og:description": "Why users and groups are content objects here, and how the plugin creates one without knowing what type it is."
    "property=og:title": "About users as content"
---

(concepts-users-as-content)=

# About users as content

Plone keeps users in `source_users` and groups in `source_groups`, as records in a BTree.

A site that wants a member directory, an editable profile page, or a reviewable group wants those to be content instead.
This package makes them content, on every site that installs it, and the `UserProfile` and `UserGroup` types it ships are what a user and a group are here.

It was an option while this package was being built, a `[content]` extra with a profile of its own, and the option created two of every code path that touches a user.
It was merged away before the first release, so no site ever had to choose.
For what is done with the fields a Profile owns, read {doc}`/concepts/profiles-and-groups`.

What survived the merge is the *indirection*: the plugin that creates a user still does not name the type it creates.

## The contract is declared, not assumed

`IUserContent` and `IGroupContent` are markers that a Dexterity type provides.

The plugin creates objects of whatever type the registry names, having checked only that the type claims the marker.
`UserProfile` and `UserGroup` claim it, and installing the add-on points the records at them, so nothing has to be configured.
A site with a user type of its own points the records somewhere else and keeps everything below.

A user type promises `userid`, `login`, and `group_ids`.
A group type promises `group_id`.
The plugin reads nothing else, so the rest of the schema is the type's own business.

## The object's id is the identifier

For both types, the object's id within its container *is* the `userid` or the `group_id`.

That is what lets the plugin resolve a user in a single traversal rather than a search.
It is not a constraint invented for the interface.
An opaque userid never changes, so the object never has to be renamed, and a rename is the one operation that strands a URL somebody bookmarked.

This single promise is what several later refusals rest on.

## Working by declining

The identity plugin implements the `IUserAdderPlugin` interface from PAS and the `IGroupManagement` interface from PlonePAS.

Both of those interfaces are walked plugin by plugin until one returns true.
So both halves of this feature work by *declining*, and declining is what happens when a site has pointed the records at a type that is not a user.
That is a mistake in the settings rather than a mode, and `source_users` or `source_groups` then does the job exactly as it did before this add-on existed.
It is the right failure: an operator who mistyped a portal type gets stock Plone rather than an error page.

## Being asked first is load-bearing

A plugin that declines has to be asked before a plugin that never declines.

`source_users` and `source_groups` always succeed.
Registered below either of them, this plugin is never reached, and nothing reports it: the site simply keeps creating stock users while every test that calls the plugin directly stays green.
So install moves the plugin to the top of both interfaces, for the same reason the profile plugin sits at the top of `IPropertiesPlugin`.

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
A row beside it would be a second record of the same person, kept in step by nothing, turning up in {menuselection}`acl_users --> source_users --> Users`, and outliving the object it shadows.

A site that would rather keep the credential with the rest of the user opts into `ICredentialStorage`, takes on those four questions deliberately, and the plugin then has nothing to delegate.
The package ships that as an opt-in behavior which keeps a hash in an annotation rather than in a field.

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
Keeping membership on the member makes the hot question a single metadata read, and leaves the cold question to a catalog query.

`IGroupContent` therefore has no members accessor, and will not grow one.
An accessor would be a second copy of the same fact, and the two would drift the first time anything wrote to one without the other.

A group can be a member of a group, and that is the same fact stored the same way.
A group carries `group_ids` as well, naming the groups it is nested inside, so everybody in the inner group is in the outer one.

The answer is closed over on the way out rather than stored expanded.
That walk is over the group graph, which grows with the number of teams rather than the number of people, and the whole of it is one catalog query.
See {doc}`profiles-and-groups` for what happens to a cycle and to a deactivated group.

## Creating and enumerating are two plugins

One plugin creates a user; a second one answers which users match a search.
Answering that without waking every object needs a catalog, which is why it is a separate plugin over a separate tool.

The two are not independent.
PAS looks a principal straight back up after adding it, so a site with the first plugin and not the second gets a user that cannot be found.

Installing the add-on installs both, which is exactly why they stopped being two profiles.

```{important}
If you point the registry records at a content type of your own, make sure something on the site enumerates that type.
`UserProfile` is enumerated by the plugin this package installs; another type is your responsibility.
```

## Why not `Products.membrane`

`Products.membrane` solves a similar problem, and has been doing so far longer than this package has existed.

Its published compatibility matrix lists Plone 6.0 and 6.1, not 6.2.
That is a fact about the current release rather than a judgement, and it may well change.

The other reason is narrower, and it is the property this page is about: serving user properties and enumeration without waking a content object.
That has to be something the package can assert about its own code on every CI run, and it does, with a test that counts ZODB object activations and requires zero.

Membrane does wake them, and it is worth being precise about where.
`MembranePropertyManager.getPropertiesForUser` collects property providers through `findMembraneUserAspect`, which adapts `brain._unrestrictedGetObject()`.
Answering a property lookup therefore loads the content object, one per matching brain.
The plugin inherits `OFS.Cache.Cacheable`, but that path never calls it, so nothing caches in front of the load.
Its *user enumeration* is not affected: that goes through `findImplementations`, which stays on the brains.

This is architecture rather than oversight.
Membrane's property values live on the content object and are read through an adapter on it, so a brain genuinely cannot answer.
This package copies the values it serves into catalog metadata instead, which is what lets a brain answer and what the zero-wake test measures.
The trade is real in both directions: metadata has to be kept honest, and the package ships a consistency check and a rebuild step precisely because of that.

```{note}
Verified against `Products.membrane` 7.0.1.dev0 (`plugins/propertymanager.py`, `utils.py`) by reading the source rather than by measurement.
Membrane is not a dependency here, and its compatibility matrix would make it awkward to install alongside.
Membrane's *design* is nonetheless where this one comes from, and the resemblance is not accidental.
```

```{seealso}
{doc}`/reference/user-content` for the records and the contracts.
{doc}`/concepts/profiles-and-groups` for what is built on top.
{doc}`/concepts/layers` for why the authorization server is still a layer of its own.
```


## Where to go next

-   {doc}`/reference/user-content` for the records, the marker contracts and the refusals.
-   {doc}`profiles-and-groups` for the two types this package builds on the mechanism.
-   {doc}`layers` for the boundary that lets core create a type it has never heard of.

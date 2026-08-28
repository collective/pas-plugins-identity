---
myst:
  html_meta:
    "description": "Content types, workflow states, registry records, and maintenance steps in the content layer."
    "property=og:description": "Content types, workflow states, registry records, and maintenance steps in the content layer."
    "property=og:title": "Profiles and groups reference"
---

(reference-profiles)=

# Profiles and groups reference

This page describes the `[content]` extra.

For why the layer is built this way, see {doc}`/concepts/profiles-and-groups`.

## Content types

`UserProfile`
:   Carries the PAS property sheet -- full name, email, home page, biography, and location -- plus a picture in the `image` field.
    It also carries `userid`, `login`, and `group_ids`, which are what make the object a user rather than a page about one.
    `userid` is displayed and never editable on the edit form: an edit detaching a `UserProfile` from its identity is not an edit anybody means to make.
    Governed by a three-state workflow.

`UserGroup`
:   A group.
    Membership is not stored here.
    It is stored on each `UserProfile`, in the `group_ids` field.

## Profile workflow states

`incomplete`
:   Freshly created and not filled in.
    Still enumerable, so the account works and is merely sparse.

`complete`
:   The user has filled it in.
    Visible to authenticated members, which is what makes a member search useful.

`deactivated`
:   Excluded from enumeration and from property lookup.
    The `UserProfile` and its data are kept.

Which states count as active is a registry setting.

```{mermaid}
stateDiagram-v2
    direction LR
    [*] --> incomplete
    incomplete --> complete: complete
    complete --> incomplete: reopen
    incomplete --> deactivated: deactivate
    complete --> deactivated: deactivate
    deactivated --> incomplete: reactivate
```

`complete` and `reopen` are guarded by `Modify portal content`, so the user themselves can make both.
`deactivate` and `reactivate` are guarded by `Manage users`, so they cannot.

Reactivating returns a profile to `incomplete` rather than to `complete`.
Whatever made an account worth deactivating is worth looking at again before it is enumerated.

### What the states mean

`incomplete` means the profile is missing information the site requires of it.
`complete` means it is not.

Nothing asks a user to press a button.
The add-on moves a profile between the two states itself, whenever the profile is written to and whenever its owner signs in.

A provider is not obliged to send anything.
A bare OIDC provider may release nothing beyond `sub`, a magic link knows only the address it was sent to, and a provider that sends an address is not obliged to say whether anyone checked it.
So a profile minted at first login is routinely missing something, and the site has to be able to insist.

`deactivated` is never entered or left by any of this.
That state is a decision about an account, and "nothing is missing" is not an argument against it.

### Which fields are required

```text
pas.plugins.identity.required_profile_fields
```

Empty, which is how it ships, means the fields the profile type itself marks required.
That is `login`, `email` and `fullname` for the type in this package, and the right answer for a site running its own user type or a behavior that adds a field.

Set it to name fields explicitly:

```text
('email', 'fullname', 'location')
```

A field counts as filled when it holds something other than `None`, an empty string, whitespace, or an empty collection.
`0` and `False` are answers somebody gave, and are not missing.

A field named here does not have to be required on the type.
`@types/UserProfile` reports the site's required fields alongside the type's, so the edit form asks for everything the flow insists on.
Without that the two would disagree in the worst direction: the flow would hold the profile incomplete while the form accepted a save without the field, and the user would be asked again for something they had already tried to give.

The record only ever adds.
A field the type marks required stays required whatever the record says, because the type is the one that cannot store an empty value.

### What happens while a profile is incomplete

Every page its owner asks for is answered with a redirect to its edit form.

```text
pas.plugins.identity.enforce_required_profile_fields
```

On, which is how it ships.
Turn it off to make an incomplete profile a suggestion rather than a gate.

Two things are never held, and both exist so that a required field nobody can supply cannot lock the site:

Managers and site administrators
:   Somebody has to be able to reach the settings that would undo the requirement, and it cannot be somebody who has to get past the gate first.

The profile itself
:   Its edit form, its widgets, and its save. Redirecting the target of the redirect is a loop no configuration escapes.

Three other things pass through, for reasons that are about the request rather than about the user:

-   Requests `plone.restapi` answers. Volto fetches the edit form over the API, so gating those would break the page the user is being sent to. The frontend does its own routing.
-   Anything that is not a browser asking for a page. Only `GET` for `text/html` is a navigation; a gate on every request is a gate on every stylesheet.
-   Signing out. A user who would rather leave than fill the form in may.
-   The OAuth authorization endpoints, `@@oauth-*`. `@@oauth-authorize` is a browser view answering `text/html`, so it looks exactly like a page; redirecting it strands a visitor who was sent to authorize an application, and the relying party that sent them receives neither a code nor an error.

Name any other view that must not be interrupted:

```text
pas.plugins.identity.gate_exempt_paths
```

Matched against the last segment of the path, like the built-in exemptions.
This is for a browser-based flow another add-on publishes, which would otherwise be interrupted halfway.

### Authorizing another application

The authorization endpoint enforces this itself, rather than relying on the gate.

A federated sign-in touches only exempt routes, so the gate never fires during one: the browser goes to `@@oauth-authorize`, to a login page, to the callback, and to the consent screen, and every one of those has to stay reachable.
That left the enforcement with nothing to enforce.
A user could complete a whole federation with a profile the site had declared incomplete, and the relying party received an account missing the same field.

So `@@oauth-authorize` pauses the request at the profile's edit form and passes the authorization request along as `return_url`, resuming it once the profile is complete.
The client is told nothing in the meantime; the request is paused, exactly as it is while the user signs in.
With `prompt=none`, where the specification forbids interacting with the user, the client is told `interaction_required` instead.

This is the provider's decision to make and nobody else's: a relying party cannot enforce what the provider requires, and should not have to.
Turning `enforce_required_profile_fields` off turns this off with it.

## Group states

A group has two states.

Deactivating one stops it being enumerated and stops it granting membership, without deleting it and without editing a single `UserProfile`.
Reactivating restores exactly the membership it had.

A `UserProfile` naming a group that no longer exists grants nothing, and the consistency check reports it.

```{mermaid}
stateDiagram-v2
    direction LR
    [*] --> active
    active --> deactivated: deactivate
    deactivated --> active: reactivate
```

Both transitions are guarded by `Manage users`.

## Where profiles are stored

Four registry records name the container: its parent path, id, title, and content type.

A project that keeps member data under `/intranet/people` sets four values.
A project happy with `/identity-profiles` sets none.

The catalog is not scoped to that container.
It indexes a `UserProfile` wherever the object actually is, so reorganizing content is not a deauthentication.

## Where profiles may be created

Only in that container.

Each type has its own add permission, and `rolemap.xml` grants both to no role at all.
What makes either type addable anywhere is a local grant on the container itself, which the add-on writes when it creates the folder, when it installs into a site where the folder already exists, and when a folder appears at the configured path.

```text
pas.plugins.identity: Add User Profile
pas.plugins.identity: Add User Group
```

So nobody can create a `UserProfile` in an ordinary folder, or paste one into it, and that includes a `Manager`.
Neither type appears in the add menu anywhere else.

To file principals somewhere else as well, grant the permission on that folder.
That is a deliberate act on a folder you chose, which is the difference between this and granting it site-wide.

The two permissions are separate so that a site filing groups apart from users can open each container to one kind only.

## Permissions on a profile

Group membership is the exception, and it has a permission of its own:

```text
pas.plugins.identity: Edit Profile Group Membership
```

`group_ids` decides which groups a user is in, and therefore which roles they hold, so writing it on your own profile is granting yourself those roles.
It is granted to `Manager` and `Site Administrator`, in every workflow state, and never to the profile's owner.
Every other field uses the ordinary edit permission, which the owner does hold: filling in your own name is self-service, and promoting yourself is not.

A user gets `Owner` on their own `UserProfile`, and nothing on anybody else's.
The role is computed by a local role provider rather than assigned when the profile is created, so there is nothing to keep in step.

In Plone, `Owner` is the role that says an object belongs to a user, and it is the role the sharing tab and every other add-on already understand.

It also carries more than editing.
Stock Plone grants `Owner` sixteen permissions with acquisition on, and the workflow states the ones that matter so they stop at the site administrator:

```text
Delete objects
Add portal content
Add portal folders
Manage properties
Modify constrain types
Modify view template
Undo changes
View management screens
```

`Delete objects` is the one to keep in mind.
A user deleting their own `UserProfile` would break their account while their sign-in kept working.

## Endpoints

| Endpoint | Returns |
| --- | --- |
| `GET @my-profile` | Where the current user's `UserProfile` is, and what state it is in. |

The frontend uses `@my-profile` to send a new user to their profile once and never ask again.

## Claims refresh rules

On every sign-in, the provider's claims refresh the fields the provider still owns, and only those.

The rule is one comparison.
The `UserProfile` remembers what the provider last wrote, and the provider may write a field only while the current value still equals that.

| Situation | Written? |
| --- | --- |
| Fresh `UserProfile`, nothing written yet | Yes |
| Provider changed the claim since the last sign-in | Yes |
| The user edited the field | No |
| The user cleared the field | No |
| An administrator typed the value in by hand | No |

The login name is never synced.
It is half of the case-folded index that user enumeration queries, and a provider renaming somebody must not silently move their account.

## Provider avatars

Off by default.

When enabled, a changed `picture_url` claim is fetched over HTTPS during claims sync and stored as the user's portrait.

```{warning}
Read {doc}`/concepts/profiles-and-groups` before enabling this.
`picture_url` is a claim, and at many providers a claim is whatever the user typed.
Turning it into a server-side fetch makes the sign-in path a request forger.
```

When enabled, the fetch is HTTPS-only, short-timeout, size-capped by counting bytes off the stream, and refused unless the server claims an image content type.

## Maintenance

The consistency check
:   Reports drift and repairs nothing.
    It reports entries missing, entries whose object is gone, brains that disagree with their object, duplicate user ids or login names, and `UserProfile` objects naming groups that do not exist.

The rebuild step
:   Repairs and reports nothing.
    It is a GenericSetup import step you can re-run whenever the check finds something.

They are kept apart so that the check can be scheduled read-only.

## Limits in version 1

```{note}
Group nesting is out of scope.
A group whose members are groups makes `getGroupsForPrincipal` recursive, and a recursive answer computed from brains stops being a single lookup.
So it is refused rather than stored.
```

## Managing membership

Membership is stored in the `group_ids` field of each `UserProfile`.

Two paths write it, and they reach the same place.

`api.group.add_user` and `api.group.remove_user`
:   The ordinary Plone API, and the {guilabel}`Users and Groups` control panel that calls it.
    These reach the identity plugin through PlonePAS's group tool.

Editing the `UserProfile`
:   The `Groups` field on the edit form.

Removing a group does not edit a single `UserProfile`.
A `UserProfile` naming a group that no longer exists grants nothing, and the consistency check reports it.
Recreating the group restores exactly the membership it had.

```{note}
Adding a group to a group is refused.
See {ref}`reference-user-content` for why.
```

## Coexistence with the stock plugins

`source_users`, `source_groups`, and `auto_group` keep working.

A user known to both this layer and `source_users` appears once in a search, because both return the same canonical user id and every consumer merges on it.
Group memberships are the union, with no duplicates.

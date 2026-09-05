---
myst:
  html_meta:
    "description": "The UserProfile and UserGroup content types: fields, workflow states, containers, the profile gate, and claims refresh."
    "property=og:description": "The UserProfile and UserGroup content types: fields, workflow states, containers, the profile gate, and claims refresh."
    "property=og:title": "Profiles and groups"
---

(reference-profiles-and-groups)=

# Profiles and groups

The `UserProfile` and `UserGroup` content types, and the rules that govern them.

For the reasoning behind any of it, read {doc}`/concepts/profiles-and-groups`.
For the contract a site's own types must meet instead, read {doc}`user-content`.

## The two types

<!-- source: backend/src/pas/plugins/identity/core/contents/profile.py -->
<!-- source: backend/src/pas/plugins/identity/core/contents/group.py -->
<!-- source: backend/src/pas/plugins/identity/profiles/default/types/ -->

| | `UserProfile` | `UserGroup` |
|---|---|---|
| Portal type | `UserProfile` | `UserGroup` |
| Schema | `IUserProfileSchema` | `IUserGroupSchema` |
| Marker it provides | `IUserContent` | `IGroupContent` |
| Workflow | `user_profile_workflow` | `user_group_workflow` |
| Identifier | the object's id in its container **is** the userid | the object's id **is** the group id |
| Membership | `group_ids`, from the `pas.plugins.identity.group_membership` behavior | the same field, naming the groups this group is nested inside |

Neither type declares `group_ids`. Both enable the behavior, which is what lets a
site's own user type gain membership without declaring the field, its
vocabulary, and its two permissions a second time.

A `UserGroup` does not store its own members. Membership is stored on each
member.

### `UserProfile` fields

| Field | Type | Required | Read permission | Write permission |
|---|---|---|---|---|
| `login` | `TextLine` | yes | View Profile | Edit Profile |
| `fullname` | `TextLine` | yes | View Profile | Edit Profile |
| `emails` | `Tuple` of `Email` | yes | View PII | Edit Profile |
| `email` | `Email` | no, **read-only** | View PII | — |
| `home_page` | `TextLine` | no | View Profile | Edit Profile |
| `description` | `Text` | no | View Profile | Edit Profile |
| `location` | `TextLine` | no | View Profile | Edit Profile |
| `image` | `NamedBlobImage` | no | View Profile | Edit Profile |
| `group_ids` | from the behavior | no | View Profile | **Edit Profile Group Membership** |

Permission titles are shortened here; see {doc}`permissions` for the ids.

### `UserGroup` fields

| Field | Type | Required |
|---|---|---|
| `title` | `TextLine` | yes |
| `description` | `Text` | no |
| `group_ids` | from the behavior | no |

## Addresses

`emails` is an ordered tuple and is the required field. `email` is derived from
it and read-only:

> the first **verified** address, or the first address at all when none is
> verified.

| Rule | Behaviour |
|---|---|
| What counts as verified | This site holds an `email` identity for the address. |
| What creates one | A magic link, or a login through a provider the operator marked as trusting. |
| A provider asserting `email_verified` | Nothing, unless that provider is marked as trusted here. |
| Writing `email` | Moves that address to the front of `emails`. It does not replace a field. |
| Writing an empty `email` | Ignored. |
| Where `email` is served from | Catalog metadata. Confirming or removing an email identity updates the owner's catalog entry. |
| `email` on the edit form | Absent. `plone.restapi` omits a read-only field from a type's edit schema; it is still serialized with the content. |

See {doc}`/concepts/email-verification`.

### What a login writes

| Event | Effect on `emails` |
|---|---|
| First login | Every address the provider reports, in the provider's order: primary first, then the ones it says it verified. |
| A later login | **Appends** only addresses no provider has offered before. |
| An address you deleted | Stays deleted. |
| The order you chose | Not rearranged. |
| A provider changing your address | The new one is added beside the old. |

Which address stands for a person is that order, so choosing one is moving it to
the front. The edit form's list does that, and so does {guilabel}`Make preferred`
on the {guilabel}`Sign-in methods` page. A verified address still wins over an
unverified one above it, because that is what `email` is derived from.

## Workflow

<!-- source: backend/src/pas/plugins/identity/profiles/default/workflows/ -->

### Profile states

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

| State | Meaning | Enumerated? |
|---|---|---|
| `incomplete` | Missing information the site requires. The initial state. | yes |
| `complete` | Nothing required is missing. | yes |
| `deactivated` | Excluded from enumeration and from property lookup. The object and its data are kept. | no |

Which states count is `profile_enumeration_states`, `('incomplete', 'complete')`
by default. See {doc}`settings`.

| Transition | To | Guarded by | So the user themselves… |
|---|---|---|---|
| `complete` | `complete` | `Modify portal content` | can make it |
| `reopen` | `incomplete` | `Modify portal content` | can make it |
| `deactivate` | `deactivated` | `Manage users` | cannot |
| `reactivate` | **`incomplete`** | `Manage users` | cannot |

Reactivating returns a profile to `incomplete`, never to `complete`.

Nothing asks a user to press a button: the package moves a profile between
`incomplete` and `complete` itself, whenever the profile is written to and
whenever its owner signs in. `deactivated` is never entered or left by that.

### Who holds what, per state

Every permission is mapped with `acquired="False"` in every state.

| Permission | `incomplete` | `complete` | `deactivated` |
|---|---|---|---|
| `View` | Manager, Site Administrator, Owner | + **Member** | Manager, Site Administrator |
| `Access contents information` | Manager, Site Administrator, Owner | + **Member** | Manager, Site Administrator |
| `Modify portal content` | Manager, Site Administrator, Owner | same | Manager, Site Administrator |
| Edit Profile | Manager, Site Administrator, Owner | same | Manager, Site Administrator |
| View Profile | Manager, Site Administrator, Owner | + **Member** | Manager, Site Administrator |
| View PII | Manager, Site Administrator, Owner | same | Manager, Site Administrator |
| Edit Profile Group Membership | Manager, Site Administrator | same | same |
| `Delete objects` | Manager, Site Administrator | same | same |
| `Add portal content` | Manager, Site Administrator | same | same |
| `Add portal folders` | Manager, Site Administrator | same | same |
| `Manage properties` | Manager, Site Administrator | same | same |
| `Modify constrain types` | Manager, Site Administrator | same | same |
| `Modify view template` | Manager, Site Administrator | same | same |
| `Undo changes` | Manager, Site Administrator | same | same |
| `View management screens` | Manager, Site Administrator | same | same |

Two things to read off this table:

- **`Owner` never holds `Delete objects`**, in any state. Stock Plone would grant
  it with acquisition on; the workflow states it and stops it at the site
  administrator.
- **`Owner` never holds Edit Profile Group Membership**, in any state. Writing
  `group_ids` is granting yourself roles.

A user gets `Owner` on their own `UserProfile` and nothing on anybody else's. The
role is computed by a local role provider rather than assigned at creation.

### Group states

```{mermaid}
stateDiagram-v2
    direction LR
    [*] --> active
    active --> deactivated: deactivate
    deactivated --> active: reactivate
```

| State | `View` and `Access contents information` | Enumerated, and grants membership? |
|---|---|---|
| `active` | Manager, Site Administrator, Member | yes |
| `deactivated` | Manager, Site Administrator | no |

`Modify portal content` and `Delete objects` are Manager and Site Administrator
in both states. Both transitions are guarded by `Manage users`.

Deactivating a group stops it being enumerated and stops it granting membership,
without deleting it and without editing a single `UserProfile`. Reactivating
restores exactly the membership it had.

Which states count is `group_enumeration_states`, `('active',)` by default.

## Where principals are stored

<!-- source: backend/src/pas/plugins/identity/core/container.py -->

Eight registry records: parent path, id, title and content type, for profiles
and again for groups. The group records default to the profile container's, so a
site filing principals together sets none of them. See {doc}`settings`.

The catalog is **not** scoped to the container. It indexes a `UserProfile`
wherever the object actually is, so reorganizing content is not a
deauthentication.

### Where principals may be created

Only in that container.

Each type has its own add permission, and `rolemap.xml` grants both to **no role
at all**:

```text
pas.plugins.identity.userprofile.add
pas.plugins.identity.usergroup.add
```

What makes either type addable is a **local** grant on the container itself,
which the package writes when it creates the folder, when it installs into a site
where the folder already exists, and when a folder appears at the configured
path.

So nobody creates a `UserProfile` in an ordinary folder or pastes one into it,
and that includes a `Manager`. Neither type appears in the add menu anywhere
else. To file principals somewhere else as well, grant the permission on that
folder.

The two permissions are separate so that a site filing groups apart from users
can open each container to one kind only.

## The profile gate

<!-- source: backend/src/pas/plugins/identity/core/subscribers/gate.py -->

While a profile is incomplete, every page its owner asks for is answered with a
redirect to its edit form. Subscribed to `IPubAfterTraversalEvent`.

Controlled by `enforce_required_profile_fields`, on by default.

### What counts as complete

`required_profile_fields` names the fields. Empty, which is how it ships, means
the fields the profile type itself marks required: `login`, `emails` and
`fullname` for the type in this package.

| Value | Counts as filled? |
|---|---|
| `None` | no |
| `''` or whitespace | no |
| an empty collection | no |
| `0` | **yes** |
| `False` | **yes** |

The record only ever **adds**. A field the type marks required stays required
whatever the record says.

A field named here need not be required on the type: `@types/UserProfile` reports
the site's required fields alongside the type's, so the edit form asks for
everything the flow insists on.

### What is never gated

The checks run in this order, cheapest first, and the first match lets the
request through.

| # | Passes when | Why |
|---|---|---|
| 1 | The request is a `plone.restapi` request (`IAPIRequest`) | Volto fetches the edit form over the API. |
| 2 | It is not a `GET` for `text/html` | A gate on every request is a gate on every stylesheet. |
| 3 | There is no Plone site yet | Nothing to answer for. |
| 4 | The user is anonymous | The gate is about a profile's owner. |
| 5 | The last path segment is exempt | See the two lists below. |
| 6 | The user holds `Manager` or `Site Administrator` | A required field nobody can supply must not lock the site. |
| 7 | The gate is switched off | `enforce_required_profile_fields`. |
| 8 | The user has no incomplete profile | Nothing to hold them for. |
| 9 | The profile is already in the traversed path | Its edit form, its widgets, its save. Redirecting the target is a loop. |

Exempt path segments:

```text
login   @@login   login_form   require_login   @@require_login
logout  @@logout  logged_out
```

Exempt prefixes:

```text
@@oauth-
```

Name any other view that must not be interrupted in `gate_exempt_paths`, matched
against the last segment of the path.

### Authorizing another application

A federated sign-in touches only exempt routes, so the gate never fires during
one. `@@oauth-authorize` therefore enforces completeness itself: it pauses the
request at the profile's edit form and passes the authorization request along as
`return_url`, resuming it once the profile is complete.

The client is told nothing meanwhile; the request is paused, exactly as it is
while the user signs in. With `prompt=none`, where the specification forbids
interacting with the user, the client is told `interaction_required` instead.

Turning `enforce_required_profile_fields` off turns this off with it.

## Claims refresh

On every sign-in the provider's claims refresh the fields that provider still
owns, and only those. The rule is one comparison: the `UserProfile` remembers
what the provider last wrote, and the provider may write a field only while the
current value still equals that.

| Situation | Written? |
|---|---|
| Fresh `UserProfile`, nothing written yet | yes |
| The provider changed the claim since the last sign-in | yes |
| The user edited the field | no |
| The user cleared the field | no |
| An administrator typed the value in by hand | no |

`login` is **never** synced. It is half of the case-folded index that user
enumeration queries.

## Provider avatars

Off by default: `sync_portraits`.

When on, a changed `picture_url` claim is fetched during claims sync and stored
as the user's portrait.

| Guard | Value |
|---|---|
| Scheme | HTTPS only |
| Timeout | `portrait_timeout`, `5` seconds |
| Size cap | `portrait_max_bytes`, 2 MiB, counted off the stream |
| Content type | Refused unless the server claims an image |

```{warning}
Read {doc}`/concepts/profiles-and-groups` before enabling this. `picture_url` is
a claim, and at many providers a claim is whatever the user typed. Turning it
into a server-side fetch makes the sign-in path a request forger.
```

## Membership

Membership is stored in `group_ids` on each member. Two paths write it, and they
reach the same place.

| Path | Notes |
|---|---|
| `api.group.add_user` / `api.group.remove_user` | The ordinary Plone API, and the {guilabel}`Users and Groups` control panel that calls it. Reaches the plugin through PlonePAS's group tool. |
| Editing the `UserProfile` | The {guilabel}`Groups` field on the edit form. Needs Edit Profile Group Membership. |

| Situation | Result |
|---|---|
| A group is deleted | No `UserProfile` is edited. Members naming it grant nothing. |
| The group is recreated | Exactly the membership it had. |
| A `UserProfile` names a group that does not exist | Grants nothing; the consistency check reports it. |
| A group inside a group | Allowed. `api.group.add_user(groupname='staff', username='developers')` writes the edge on `developers`. |
| A group inside itself | Refused. |
| An inactive group | Grants nothing and passes nothing through. |

Nesting is closed over when the question is asked rather than stored expanded, so
removing an edge takes effect everywhere at once.

## Maintenance

| Step | Does | Does not |
|---|---|---|
| The consistency check | Reports drift | Repair anything |
| `pas.plugins.identity:rebuild-catalog` | Repairs | Report anything |

They are kept apart so the check can be scheduled read-only. The check reports
catalog entries missing, entries whose object is gone, brains that disagree with
their object, duplicate user ids or login names, and `UserProfile` objects naming
groups that do not exist.

## Coexistence with the stock plugins

`source_users`, `source_groups` and `auto_group` keep working.

A user known to both this package and `source_users` appears **once** in a
search, because both return the same canonical user id and every consumer merges
on it. Group memberships are the union, with no duplicates.

## Related

- {doc}`/concepts/profiles-and-groups`—why membership lives on the member
- {doc}`user-content`—the contract a site's own types must meet
- {doc}`settings`—every record named on this page
- {doc}`permissions`—the permission ids and their site-wide floor
- {doc}`endpoints`—`@my-profile`, `@group-members` and `@user-account`

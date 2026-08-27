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

`Profile`
:   Carries the PAS property sheet -- full name, email, home page, biography, and location -- plus a picture in the `image` field.
    It also carries `userid`, `login`, and `group_ids`, which are what make the object a user rather than a page about one.
    `userid` is displayed and never editable on the edit form: an edit detaching a `Profile` from its identity is not an edit anybody means to make.
    Governed by a three-state workflow.

`IdentityGroup`
:   A group.
    Membership is not stored here.
    It is stored on each `Profile`, in the `group_ids` field.

## Profile workflow states

`incomplete`
:   Freshly created and not filled in.
    Still enumerable, so the account works and is merely sparse.

`complete`
:   The user has filled it in.
    Visible to authenticated members, which is what makes a member search useful.

`deactivated`
:   Excluded from enumeration and from property lookup.
    The `Profile` and its data are kept.

Which states count as active is a registry setting.

## Group states

A group has two states.

Deactivating one stops it being enumerated and stops it granting membership, without deleting it and without editing a single `Profile`.
Reactivating restores exactly the membership it had.

A `Profile` naming a group that no longer exists grants nothing, and the consistency check reports it.

## Where profiles are stored

Four registry records name the container: its parent path, id, title, and content type.

A project that keeps member data under `/intranet/people` sets four values.
A project happy with `/identity-profiles` sets none.

The catalog is not scoped to that container.
It indexes a `Profile` wherever the object actually is, so reorganizing content is not a deauthentication.

## Permissions on a profile

A user gets `Editor` on their own `Profile`, and nothing on anybody else's.

Not `Owner`.
`Owner` carries the right to delete, and a user deleting their own `Profile` would break their account while their sign-in kept working.

## Endpoints

| Endpoint | Returns |
| --- | --- |
| `GET @my-profile` | Where the current user's `Profile` is, and what state it is in. |

The frontend uses `@my-profile` to send a new user to their profile once and never ask again.

## Claims refresh rules

On every sign-in, the provider's claims refresh the fields the provider still owns, and only those.

The rule is one comparison.
The `Profile` remembers what the provider last wrote, and the provider may write a field only while the current value still equals that.

| Situation | Written? |
| --- | --- |
| Fresh `Profile`, nothing written yet | Yes |
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
    It reports entries missing, entries whose object is gone, brains that disagree with their object, duplicate user ids or login names, and `Profile` objects naming groups that do not exist.

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

Membership is stored in the `group_ids` field of each `Profile`.

Two paths write it, and they reach the same place.

`api.group.add_user` and `api.group.remove_user`
:   The ordinary Plone API, and the {guilabel}`Users and Groups` control panel that calls it.
    These reach the identity plugin through PlonePAS's group tool.

Editing the `Profile`
:   The `Groups` field on the edit form.

Removing a group does not edit a single `Profile`.
A `Profile` naming a group that no longer exists grants nothing, and the consistency check reports it.
Recreating the group restores exactly the membership it had.

```{note}
Adding a group to a group is refused.
See {ref}`reference-user-content` for why.
```

## Coexistence with the stock plugins

`source_users`, `source_groups`, and `auto_group` keep working.

A user known to both this layer and `source_users` appears once in a search, because both return the same canonical user id and every consumer merges on it.
Group memberships are the union, with no duplicates.

# Profiles and groups

*The `[profile]` extra.*

Plone's stock user storage keeps properties in a BTree and knows nothing about
workflow, permissions or the catalog. That is fine until you want a member
directory, an editable profile page, or a group whose membership somebody can
review. This extra backs users with content instead — while keeping the thing
that usually goes wrong when people try that from going wrong.

## The thing that usually goes wrong

User enumeration and property lookup run constantly, on paths where waking a
content object is unacceptable: rendering a Sharing tab, resolving a local
role, listing who is in a group. An implementation that loads a content object
to answer "what is this user's full name" turns every listing into a storm of
object loads.

So nothing here does. Properties, user enumeration, group membership and group
listings are all served from catalog metadata, and the test suite asserts it
rather than claiming it: it patches ZODB's object activation, runs the whole
surface, and requires the count of woken `Profile` objects to be zero — having
first proved the objects were ghosts and that the counter registers a real
load.

## What you get

A `Profile` content type carrying exactly the PAS property sheet — full name,
email, home page, biography, location — and a three-state workflow.

`incomplete`
: Freshly created and not filled in. Still enumerable: the account works, it
  is just sparse.

`complete`
: The user has filled it in. Visible to authenticated members, which is what
  makes a member search useful.

`deactivated`
: Excluded from enumeration and from property lookup. The Profile and its data
  are kept.

Which states count as active is a registry setting.

## Where Profiles live

Wherever you say. The container's parent path, id, title and content type are
four registry records, so a project that keeps member data under
`/intranet/people` sets four values and a project happy with
`/identity-profiles` sets none.

The catalog is **not** scoped to that container. It indexes a Profile wherever
it actually is, so reorganising content is not a deauthentication.

## First login

The first time somebody authenticates, a Profile is minted for them in
`incomplete`, seeded from the provider's claims. `GET @my-profile` reports
where it is and what state it is in, which is what the frontend uses to send a
new user to their profile once and never ask again.

A user gets `Editor` on their own Profile and nothing on anybody else's. Not
`Owner`: Owner carries "may delete", and a user deleting their own Profile
would break their account while their login kept working.

## Claims refresh

On every login the provider's claims refresh the fields it still owns — and
only those.

The rule is one comparison: **the Profile remembers what the provider last
wrote, and the provider may write a field only while the current value still
equals that.**

| Situation | Written? |
| --- | --- |
| Fresh Profile, nothing written yet | yes |
| Provider changed the claim since last login | yes |
| The user edited the field | no |
| The user **cleared** the field | no |
| An administrator typed the value in by hand | no |

The last two rows are the ones a flag-per-field design tends to get wrong.
Clearing a field is an edit, and a value that reappears at the next login is
indistinguishable from a bug.

The login name is never synced. It is half of the case-folded index user
enumeration queries, and a provider renaming somebody should not silently move
their account.

## Groups

An `IdentityGroup` content type, and a `group_ids` field on each Profile.

Membership lives on the **Profile**, not as a list on the group, because that
is the direction Plone asks questions in. `getGroupsForPrincipal` runs on
every permission check that touches a local role; `getGroupMembers` runs when
somebody opens a listing. Keeping membership on the member makes the hot
question a single metadata read.

Groups have two states. Deactivating one stops it being enumerated and stops
it granting membership — without deleting it and without editing a single
Profile. Reactivating restores exactly the membership it had.

A Profile naming a group that no longer exists grants nothing, and the
consistency check reports it.

:::{note}
There is no write API for group membership in v1. Membership changes by
editing a Profile and by nothing else. Group nesting is also out of scope: a
group whose members are groups makes `getGroupsForPrincipal` recursive, and a
recursive answer computed from brains stops being a single lookup.
:::

## Coexistence with the stock plugins

`source_users`, `source_groups` and `auto_group` keep working. A user known to
both this layer and `source_users` appears once in a search, because both
return the same canonical user id and every consumer merges on it. Group
memberships are the union, with no duplicates.

## Keeping the catalog honest

A dedicated catalog is a second copy of the truth, and a second copy drifts.

The **consistency check** reports drift and repairs nothing: entries missing,
entries whose object is gone, brains that disagree with their object,
duplicate user ids or login names, and Profiles naming groups that do not
exist.

The **rebuild step** repairs and reports nothing. It is a GenericSetup import
step you can re-run whenever the check finds something.

They are kept apart so that the check can be scheduled read-only, and so the
test suite can assert against findings rather than against whatever a repair
happened to leave behind. A randomized churn test creates, edits, transitions,
renames, moves and deletes Profiles and Groups, running the check after
*every* step — because a bug that self-corrects two operations later is still
a window in which enumeration served the wrong answer.

## Provider avatars

Off by default. When enabled, a changed `picture_url` claim is fetched over
HTTPS during claims sync and stored as the user's portrait.

:::{warning}
Read this before enabling it. `picture_url` is a claim, and at many providers
a claim is whatever the user typed. Turning it into a server-side fetch makes
the login path a request forger: a user who points their avatar at an address
only your backend can reach gets your backend to fetch it, and reads the
result off their own portrait.

When enabled the fetch is HTTPS-only, short-timeout, size-capped by counting
bytes off the stream, and refused unless the server claims an image content
type. None of that makes fetching a user-supplied URL safe — a hostile URL can
still name a public host that resolves to an internal address — which is why
there is a switch rather than a longer list of guards.
:::

## Why not Products.membrane

`Products.membrane` solves a similar problem and has been doing so for much
longer. Two reasons this package does not build on it.

Its compatibility matrix lists Plone 6.0 and 6.1, not 6.2. That is a fact
about the current release, not a judgement.

And the zero-wake property above is the whole point of this design, so it has
to be something this package can assert about its own code on every CI run.

We make no claim here about whether membrane wakes content objects to answer
these questions. We have not measured it, and an unmeasured claim about
somebody else's package does not belong in documentation.

Membrane's *design* is nonetheless where this one comes from, and the
resemblance is not accidental.

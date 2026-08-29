---
myst:
  html_meta:
    "description": "Why the content layer backs users with content without ever waking a content object."
    "property=og:description": "Why the content layer backs users with content without ever waking a content object."
    "property=og:title": "About profiles and groups"
---

(concepts-profiles-and-groups)=

# About profiles and groups

Plone's stock user storage keeps properties in a BTree and knows nothing about workflow, permissions, or the catalog.

That is fine until you want a member directory, an editable profile page, or a group whose membership somebody can review.
This package backs users with content instead, while keeping the thing that usually goes wrong from going wrong.

For the states, records, and endpoints, see {doc}`/reference/profiles`.
For the mechanism underneath, see {doc}`/concepts/users-as-content`.

## The thing that usually goes wrong

User enumeration and property lookup run constantly, on paths where waking a content object is unacceptable.
Rendering a Sharing tab.
Resolving a local role.
Listing who is in a group.

An implementation that loads a content object to answer "what is this user's full name" turns every listing into a storm of object loads.
It works in development, where there are eleven users, and it collapses on a site with eleven thousand.

## So nothing here wakes one

Properties, user enumeration, group membership, and group listings are all served from catalog metadata.

The test suite asserts that rather than claiming it.
It patches ZODB's object activation, exercises the whole surface, and requires the count of woken `UserProfile` objects to be zero.
It first proves the objects were ghosts and that the counter registers a real load, because a zero from a broken counter is not evidence.

This is the property the whole layer is arranged around, and it is why the layer looks more elaborate than adding a content type.

## Membership lives on the member

An `UserGroup` does not hold a list of its members.
Each `UserProfile` holds a `group_ids` field naming the groups it belongs to.

That is backwards from how people draw groups, and it is the direction Plone asks questions in.

`getGroupsForPrincipal` runs on every permission check that touches a local role.
`getGroupMembers` runs when somebody opens a listing.
The first is hot and the second is not, so keeping membership on the member makes the hot question a single metadata read and the cold question a catalog query.

Group nesting would break this.
A group whose members are groups makes `getGroupsForPrincipal` recursive, and a recursive answer computed from brains stops being a single lookup.
So it is out of scope rather than slow.

## A provider can grant membership, and take it back

Group membership is one of the things a provider can assert, and it is the only one that has to be *revoked* rather than merely refreshed.
A name that stops arriving is a name Plone keeps; a group that stops arriving has to stop granting.

So every sign-in reconciles the groups a provider maps, and the reconciliation is fenced.
Each identity carries the local group ids its own provider granted, and a sign-in adds what is newly granted and removes only what that same provider granted before.

That fence is what makes the feature safe to leave running.
Without it, a sign-in would write one provider's answer over the whole of a member's `group_ids`, erasing every group an administrator granted by hand and every group a second provider granted, silently, at the moment somebody logged in.

Membership is written through the group tool rather than to any store of this package's own, so it lands wherever the site keeps membership: `group_ids` on a `UserProfile` where users are content, and `source_groups` where they are not.
`getGroupsForPrincipal` stays the single metadata read described above.

See {doc}`federation` for the provider's half, and {doc}`/how-to-guides/configure-a-provider` for the map itself.

## Claims refresh, and why clearing a field is an edit

On every sign-in, the provider's claims refresh the fields the provider still owns.

The rule is one comparison.
The `UserProfile` remembers what the provider last wrote, and the provider may write a field only while the current value still equals that.

A flag-per-field design gets two cases wrong, and they are the two that matter.

An administrator typing a value in by hand looks, to a flag, like a field nobody has claimed.
And a user clearing a field looks like an empty field waiting to be filled.
Under the comparison rule, both are edits, because both changed the value away from what the provider wrote.

A value the user deleted that reappears at the next sign-in is indistinguishable from a bug, and it is the complaint this rule exists to prevent.

The login name is never synced at all.
It is half of the case-folded index that user enumeration queries, and a provider renaming somebody should not silently move their account.

## Provider avatars are a request forger

Fetching `picture_url` looks like a convenience, and it is a server-side fetch of a URL the user controls.

At many providers, `picture_url` is whatever the user typed.
A user who points their avatar at an address only your backend can reach gets your backend to fetch it, and then reads the result off their own portrait.
That is server-side request forgery with a rendering step attached.

When enabled, the fetch is HTTPS-only, short-timeout, size-capped by counting bytes off the stream, and refused unless the server claims an image content type.

None of that makes fetching a user-supplied URL safe.
A hostile URL can still name a public host that resolves to an internal address.
Which is why there is a switch, defaulting to off, rather than a longer list of guards.

## A second copy of the truth drifts

A dedicated catalog is a second copy of the truth, and second copies drift.

The add-on ships two tools, kept deliberately apart.
The consistency check reports drift and repairs nothing.
The rebuild step repairs and reports nothing.

Separating them lets the check run read-only on a schedule, and lets the test suite assert against findings rather than against whatever a repair happened to leave behind.

A randomized churn test creates, edits, transitions, renames, moves, and deletes profiles and groups, running the check after every step.
Not at the end, after every step, because a bug that self-corrects two operations later is still a window in which enumeration served the wrong answer.

## Why not Products.membrane

`Products.membrane` solves a similar problem and has been doing so for much longer.
Two reasons this package does not build on it.

Its compatibility matrix lists Plone 6.0 and 6.1, not 6.2.
That is a fact about the current release, not a judgment.

And the zero-wake property above is the whole point of this design, so it has to be something this package can assert about its own code on every CI run.

Membrane does wake content objects, and it is worth being precise about where.
`MembranePropertyManager.getPropertiesForUser` collects property providers through `findMembraneUserAspect`, which adapts `brain._unrestrictedGetObject()`.
So answering a property lookup loads the content object, one per matching brain.
The plugin inherits `OFS.Cache.Cacheable`, but that path never calls it, so there is no cache in front of the load.
Membrane's user enumeration is not affected: that goes through `findImplementations`, which stays on the brains.

This is architecture, not oversight.
Membrane's property values live on the content object and are read through an adapter on it, so a brain genuinely cannot answer.
This package copies the values it serves into catalog metadata instead, which is what lets a brain answer and what the zero-wake test measures.

The trade is real in both directions.
Metadata has to be kept honest, and that is why this package ships a consistency check and a rebuild step at all.

```{note}
Verified against `Products.membrane` 7.0.1.dev0, in `plugins/propertymanager.py` and `utils.py`, by reading the source rather than by measurement.
Membrane is not a dependency here, and its compatibility matrix would make it awkward to install alongside.
Membrane's design is nonetheless where this one comes from, and the resemblance is not accidental.
```

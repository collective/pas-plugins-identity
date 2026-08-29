---
myst:
  html_meta:
    "description": "Why one Plone user id maps to many external identities, and why the mapping is never guessed."
    "property=og:description": "Why one Plone user id maps to many external identities, and why the mapping is never guessed."
    "property=og:title": "About identities and user ids"
---

(concepts-identities)=

# About identities and user ids

Everything in this package hangs off one relationship: one canonical Plone user id, many external identities, all belonging to the same person.

An external identity is a pair.
The provider it came from, and that provider's own identifier for the person, which OpenID Connect calls the subject.
GitHub's subject for you and Google's subject for you are different strings that mean nothing to each other, and the package stores both against the same Plone user id.

That is the whole idea.
The rest of the design follows from taking it seriously.

## The user id is opaque, and that is not an accident

On accounts this package creates, the Plone user id is a `uuid4` hex string.
It is not the email address, not the provider's subject, and not the login name.

Every one of those alternatives is something that changes.
People change employers and lose an address.
Providers reassign usernames.
A site that keys content ownership on an email address discovers the problem at the moment somebody's address changes, which is also the moment the change is hardest to undo.

A `sub` claim looks more stable, and for one provider it is.
But the whole point of this package is that a person may have several, and a user id derived from one of them is a user id that says the first provider you happened to use is the real one.

So the id is minted once, from randomness, and nothing rewrites it.
The cost is that the id means nothing to a human, which is why the `preferred_username` claim exists and why the control panel shows names rather than ids.

## The mapping is never guessed

The package knows that two identities belong to one person only when it was told so.
It never infers it.

The tempting inference is by email address.
Two identities reporting the same address are probably the same person, and often they are.
Automatic linking by email exists for exactly that, and it is off by default.

When you turn it on, it matches only against an address this site holds as verified -- proved by a magic link, or vouched for by a provider the operator trusts -- and it also needs the provider now asserting the address to be one of those trusted providers.
A provider nobody marked cannot link on its own word, whatever it claims.
See {doc}`email-verification` for the two switches and why the second one is not decoration.

## A collision is an error, not a merge

If an external identity is already linked to one user id, the package will not attach it to another.
It raises instead.

The alternative would be a merge, and merging two accounts means deciding what happens to two sets of content ownership, two sets of local roles, and two sets of group memberships.
There is no answer to that a package can pick on a site's behalf.
Merging is out of scope, and being loud about the collision is the substitute.

## Unlinking your last way in is refused

A user with one linked identity and no password who unlinks it has locked themselves out, silently, by clicking a button labeled {guilabel}`Unlink`.

So the package refuses, unless the account has a verified email identity or a real password.
This is the one place where the package overrides what the user asked for, and it does it because the alternative is unrecoverable by the user.

## Where to go next

-   {doc}`/reference/events` lists the events fired when an identity is created, linked, or unlinked.
-   {doc}`layers` explains how the optional server layer attaches to this core without importing it in the wrong direction.

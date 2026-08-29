---
myst:
  html_meta:
    "description": "What email_verified asserts in pas.plugins.identity, and why a provider's word is not enough."
    "property=og:description": "What email_verified asserts in pas.plugins.identity, and why a provider's word is not enough."
    "property=og:title": "About email verification"
---

(concepts-email-verification)=

# About email verification

`email_verified` is the claim a relying party is most likely to link accounts on, which makes it worth being exact about what it asserts.

In this package it asserts one thing.
The user proved the address to this site, by following a link this site sent to it.

It does not mean an upstream provider said the address was verified.

## Why a provider's word is not enough

Consider automatic linking by email, with a provider's claim accepted at face value.

Somebody registers at a permissive provider using an address that belongs to you.
That provider marks the address verified according to whatever its own rules are, or does not mark it at all and sends a truthy-looking value anyway.
The attacker signs in here, the package matches the address to your account, and they are you.

The attack needs no access to your mail, no password, and no interaction with you.
It needs a provider whose verification is weaker than this site assumed.

So the package assumes nothing about any provider's verification and does its own.
A magic link sent from here, followed from here, is proof that whoever is signing in reads mail at that address.
Nothing else is.

## Only a literal `True` counts

Several providers send the string `"true"`.
Several send `1`.
Both are truthy in Python, and both would pass a casual check.

Drivers must normalize `email_verified` to a boolean, and the linking code compares against `True` itself rather than testing truthiness.
A forged unverified address that happens to read as truthy is an account takeover, so the comparison is deliberately unforgiving.

## The same asymmetry, exported

When the site acts as an authorization server, it releases `email_verified` under the same rule.

`true` means this site verified the address with a magic link.
It does not mean the user's provider verified it.

So a user who signed in with Google and never used a magic link here gets `email_verified: false`, even though Google verified the address.

That surprises people, and it is correct.
An authorization server that passed a provider's word along as its own would export exactly the problem described above to every relying party downstream, and each of those relying parties would believe the claim came from a site that checked.
A relying party that wants to trust Google should trust Google directly.

## The one place this is relaxed

Nowhere.

Automatic linking is off by default, and turning it on does not lower the bar.
It changes what happens when the bar is met.

## Only your own addresses

The proof a magic link produces is proof of control over whatever address the link was sent to, and nothing more.

That makes the question of *which* addresses a site will send one to a security question rather than a convenience.
A free-text box asking for an address and mailing a link to it verifies any mailbox somebody can reach, including one they have momentary access to -- and a verified address is exactly what automatic linking attaches a new provider account to.

So the addresses this site will verify are the ones already listed on your profile.
`POST @identities` for the email provider refuses an address that is not among them, and the {guilabel}`Sign-in methods` page offers your addresses with a {guilabel}`Verify` button rather than a box to type one into.

Naming an address on your profile first is what turns it into a claim somebody can see and an administrator can audit, rather than a value that only ever existed inside one request.

A caller with no profile is not held to this.
That is a site not keeping users as content, or an account that predates this add-on, and neither has a list to name an address on.

## Where to go next

-   {doc}`identities` for why the mapping is never guessed in the first place.
-   {doc}`/reference/shipped-drivers` for the magic-link driver that produces the proof.
-   {doc}`/reference/security-guarantees` for the tests that hold this in place.

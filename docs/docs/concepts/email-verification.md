---
myst:
  html_meta:
    "description": "What email_verified asserts in pas.plugins.identity, and who decides whether a provider's word counts."
    "property=og:description": "What email_verified asserts in pas.plugins.identity, and who decides whether a provider's word counts."
    "property=og:title": "About email verification"
---

(concepts-email-verification)=

# About email verification

`email_verified` is the claim a relying party is most likely to link accounts on, which makes it worth being exact about what it asserts.

In this package it asserts one thing.
This site holds the address as proved for that user.

There are two ways an address gets there, and the second one is the operator's decision rather than the package's.

Somebody followed a link this site sent
:   A magic link, delivered to the address and clicked by whoever was signing in.
    Proof that they read mail there.

A provider the operator trusts vouched for it
:   Google and GitHub both verify an address before they will call it verified, and telling somebody who just signed in with Google to go and prove the address Google proved is a worse flow for no security.
    So a provider can carry that weight, if the operator says it does.

Both write the same thing: an `email` external identity whose subject is the address, owned by that user id.
There is one notion of verified and no second flag, so there is nothing for the two to disagree about.

## Why it is a switch and not a default

Consider automatic linking by email, with every provider's claim accepted at face value.

Somebody registers at a permissive provider using an address that belongs to you.
That provider marks the address verified according to whatever its own rules are, or does not mark it at all and sends a truthy-looking value anyway.
The attacker signs in here, the package matches the address to your account, and they are you.

The attack needs no access to your mail, no password, and no interaction with you.
It needs a provider whose verification is weaker than this site assumed.

That is why the package assumed nothing for a long time and did all its own proving.
What it assumes now is still nothing: {guilabel}`This provider's email verification counts` is off unless a driver knows the provider really checks, and an operator who disagrees can switch it either way.

The drivers that ship with it on are Google and GitHub.
Everything else -- a generic OpenID Connect provider, a peer running this same package, anything an integrator adds -- starts off.

## Two switches, and both are needed

Automatic linking is where a person signing in with a new provider ends up inside an account that already existed, so it asks for both.

{guilabel}`Attach to an existing account with the same verified email`
:   Whether to look for an account at all.

{guilabel}`This provider's email verification counts`
:   Whether *this* provider saying `email_verified` means anything.

The second one is not decoration.
The address being matched on is the one the provider just sent, so without it a provider nobody trusts could reach an account by asserting somebody else's address -- an address that some other, trusted route had verified.

Even with both on, the address has to already be verified here.
A provider cannot introduce an address and match on it in the same login.

## Only a literal `True` counts

Several providers send the string `"true"`.
Several send `1`.
Both are truthy in Python, and both would pass a casual check.

Drivers must normalize `email_verified` to a boolean, and every place that reads it compares against `True` itself rather than testing truthiness.
A forged unverified address that happens to read as truthy is an account takeover, so the comparison is deliberately unforgiving.

## What this site exports

When the site acts as an authorization server, it releases `email_verified` under the rule above.

`true` means this site holds the address as verified: proved by a magic link, or vouched for by a provider this site trusts.
It is not a provider's assertion passed straight through -- a provider nobody here trusts can send `email_verified` all day and this stays `false`.

So a relying party reading the claim is being told what this site believes, on the terms this site set.
Which is what a relying party can act on, and the reason the switch is per provider rather than a single site-wide "trust providers" checkbox.

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
-   {doc}`/reference/profiles` for the address list and how `email` is derived from it.
-   {doc}`/reference/shipped-drivers` for the magic-link driver that produces the proof.
-   {doc}`/reference/security-guarantees` for the tests that hold this in place.

---
myst:
  html_meta:
    "description": "Turn a provider's group membership into local Plone groups, and restrict who may sign in."
    "property=og:description": "Turn a provider's group membership into local Plone groups, and restrict who may sign in."
    "property=og:title": "How to map provider groups"
---

(how-to-map-provider-groups)=

# How to map provider groups

Let a provider grant local group membership, and decide which of its groups mean
anything here.

Nothing happens until you say so: the group map starts empty, and an empty map
grants nothing.

## 1. Tell the site where the groups arrive

On the provider's **Groups** tab, set {guilabel}`Groups arrive in the claim`.

| Provider | Claim |
|---|---|
| Keycloak | `groups`, once a Group Membership mapper exists |
| Okta | `groups` |
| Microsoft Entra ID | `groups`, once configured in the app manifest |
| A Plone site running the `server` layer | `groups` |
| GitHub, magic link | none—these drivers send no groups |

`groups` is the default. Use a dotted path for a provider that nests them, such
as `realm_access.roles`.

## 2. Map the groups you want

Fill in the group map: one row per provider-side group name, each pointing at a
local group id.

Three rules make this safe to leave running:

- **A name with no row grants nothing**, and no group is ever created. A group
  claim is whatever the provider's directory happens to be called, so minting
  local groups from it would let anyone who can name a group at the far end
  create one here.
- **A row pointing at a group this site does not have is skipped and logged.**
- **Every login reconciles**, so a membership revoked at the provider stops
  granting anything here without anyone editing the site.

A login only ever takes back what that same provider granted. The identity
record remembers each provider's own grant, so a group you granted by hand
survives every sign-in, and two providers cannot revoke each other's grants.

## 3. Optionally, restrict who may sign in

Leave {guilabel}`Only these groups may sign in` empty and anybody the provider
authenticates may sign in.

Name groups in it and a sign-in is refused unless the provider says the person is
in one of them.

An entry matches either a name the provider sends or a local group id the map
turns one into, so write the policy in whichever vocabulary is clearer. The cost
of accepting both is that an entry alone does not say which one it was read as,
which is why a refusal records both.

This is checked on every sign-in, not only the first. Somebody removed from the
group at the provider stops getting in, and an account created before you wrote
the policy is held to it like any other.

```{warning}
This needs a group claim.

A provider whose driver has no groups at all—GitHub, magic link—sends none,
so a list here refuses **everybody**. The log says so in as many words rather
than reporting a group mismatch, because the mistake is in the configuration
rather than in the directory.
```

The person refused is told only that the sign-in failed. Naming the group they
are missing would tell anyone who can reach the login page which groups matter
here. The reason goes to the audit trail, which needs `Manage portal` to read.

## Keep the provider, decide groups yourself

Switch off {guilabel}`Let this provider set group membership` to sign people in
with the provider while deciding membership here.

A site may trust a provider to say who somebody is without trusting it to say
what they may do, and group membership is usually what grants permissions.

Groups the provider already granted stay. Taking those away is a separate
decision, and one to make deliberately rather than at the next login.

It is per provider, so refusing one is not refusing all of them.

## Verify

1. Sign in with an account that is in a mapped group at the provider.
2. The local group appears in that user's membership.
3. Remove the account from the group at the provider, sign out, sign in again.
4. The local group is gone.
5. A group you granted by hand is still there.

## Taking grants back

```{note}
Clearing a map does **not** strip the groups it had granted.

Clearing is at least as likely to mean "I am rewriting this" as "revoke
everything", so a provider with an empty map touches no membership at all.

To take its grants back, empty the map's *values* rather than the map, and let
one login reconcile.
```

## Next steps

- {doc}`/concepts/profiles-and-groups`—why a group is content, and what that costs
- {doc}`/concepts/federation`—what one site may say about the members of another
- {doc}`troubleshoot`—"Groups not granted after login"

---
myst:
  html_meta:
    "description": "Attach a new sign-in to an account that already exists, by matching a verified email address."
    "property=og:description": "Attach a new sign-in to an account that already exists, by matching a verified email address."
    "property=og:title": "How to link accounts by email"
---

(how-to-link-accounts-by-email)=

# How to link accounts by email

Make somebody signing in with a new provider land on the account they already
have here, instead of getting a second one.

Three switches on the provider's **Accounts** tab do this, and they have to be
set in order.

## 1. Trust the provider's verification

Set {guilabel}`This provider's email verification counts`.

An address the provider says it verified is then recorded as verified here,
exactly as a magic link from this site would record one.

```{warning}
Switch this on only for a provider that really checks—one that refuses to call
an address verified until the account has answered mail at it.

A provider with weaker rules is an account takeover waiting to happen: somebody
registers there with an address belonging to one of your users, and this site
hands them the account.
```

`google` and `github` ship with it on. Every other driver ships with it off.

Turning it off later stops it verifying anything new. Addresses already recorded
as verified stay that way, because they are identities, and removing one is an
unlink rather than a configuration change.

## 2. Turn on matching

Set {guilabel}`Attach to an existing account with the same verified email`.

A person signing in with this provider for the first time is then attached to an
account that already exists, when an address the provider verified matches a
verified one here.

Every address the provider verified is tried, not only the first. They are tried
in order—for GitHub, the order its **Address preference** sets, see
{doc}`providers/github`—and the first one that belongs to an account decides.

This needs step 1 as well. The address being matched on is the one this provider
just sent, so a provider whose word the site does not take cannot reach an
account with it.

## 3. If nothing links, check how the flag arrives

Some providers send `email_verified` as the string `"true"` rather than as a
boolean. Oracle Access Manager does, and so do some customized Keycloak realms.

Set {guilabel}`This provider sends verification flags as text` for those.

```{note}
The symptom is that nothing visibly goes wrong.

Sign-in works, and only the linking silently does not: every address arrives
unverified, so the switch above it can never fire, and no error says so.

If verification is configured and never seems to take effect, look at what the
provider actually sends before looking anywhere else.
```

Leave it off unless you have established that this is what your provider does. A
default Keycloak sends a real boolean and does not need it.

## Verify

Sign in with the new provider, using an address that already belongs to an
account here.

- You land on the **existing** account, not a new one.
- `/identities` for that account lists both sign-in methods.
- The audit log has an `identity-linked` entry, and an `email-verified` one.

If a second account was created instead, one of the three switches is off, or the
address was not verified at the provider.

## When two addresses belong to two accounts

A provider can verify two addresses that this site holds for two different
accounts. The account holding the higher-ranked address is the one signed in to,
and the other account keeps its address.

The conflict is logged at `ERROR`, naming both accounts and both addresses. It
usually means one person has two accounts here, and merging them is a decision
for an operator.

An address held for an account that no longer exists is skipped with a warning,
and the next address is tried.

## When it refuses

A link that would attach an identity to a **different** account than the one it is
already on raises rather than merging. The audit log records `link-collision`.

Merging two accounts is not something this package will guess at. See
{doc}`/concepts/identities`.

## Next steps

- {doc}`control-account-creation`—the switch that decides what happens when no match is found
- {doc}`/concepts/email-verification`—the whole trust rule, and why an absent claim is not a `true`
- {doc}`troubleshoot`—"Existing account not matched by email"

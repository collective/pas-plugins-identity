---
myst:
  html_meta:
    "description": "Decide whether a provider may create Plone accounts, or only sign in people who already have one."
    "property=og:description": "Decide whether a provider may create Plone accounts, or only sign in people who already have one."
    "property=og:title": "How to control account creation"
---

(how-to-control-account-creation)=

# How to control account creation

Authenticate people against a provider while admitting only those who already
have an account here.

A site federating with a large directory usually does not want everybody who
*can* authenticate to *get* an account: membership is decided elsewhere, and the
provider only proves who somebody is.

## 1. Turn creation off

On the provider's **Accounts** tab, switch off
{guilabel}`Let this provider create accounts`.

## 2. Give it a way to find the existing account

An existing account is found by matching a verified address, so both switches
described in {doc}`link-accounts-by-email` have to be on as well.

Saving the combination without them is **refused**: with nothing to match on,
every sign-in through the provider would be turned away and nothing on the login
page would say why.

So the working combination is all three:

| Switch | Setting |
|---|---|
| Let this provider create accounts | off |
| Trust this provider's email verification | on |
| Attach to an existing account with the same verified email | on |

## 3. Add the accounts

Create the Plone accounts by whatever means you already use—by hand, from a
migration, or from an export. The address on each account has to be verified for
matching to reach it.

## Verify

1. Sign in with a provider account whose address matches an existing Plone
   account. You land on that account.
2. Sign in with a provider account whose address matches nothing. The sign-in is
   refused, and no account is created.
3. The audit log distinguishes the two: `authenticated` for the first,
   `signin-refused` for the second.

## What does not change

An identity that signed in before you switched it off keeps working. The switch
gates *creating* an account, not resolving one that already exists.

## Next steps

- {doc}`link-accounts-by-email`—the two switches this depends on
- {doc}`map-provider-groups`—restricting sign-in by group instead
- {doc}`troubleshoot`—"Account created when it should have linked to an existing one"

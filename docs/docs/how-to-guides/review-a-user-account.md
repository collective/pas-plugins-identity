---
myst:
  html_meta:
    "description": "See which providers a user signs in with, when they last authenticated, and which of their addresses this site verified."
    "property=og:description": "See which providers a user signs in with, when they last authenticated, and which of their addresses this site verified."
    "property=og:title": "How to review a user's account"
---

(how-to-review-a-user-account)=

# How to review a user's account

This guide shows you how to find out how one person signs in to your site, and when they last did.

Plone's own users control panel cannot answer either question.
It lists names, roles, and groups, and nothing about how somebody actually gets in.

## From the control panel

1.  Open the {guilabel}`Users` control panel.
2.  Find the person.
3.  Open the actions menu at the end of their row, and choose {guilabel}`Account`.

The panel that opens has three parts.

{guilabel}`Sign-in methods`
:   Every provider this person has linked, named rather than listed as an id, with when the link was made and when it last worked.
    An account with nothing here signs in with a password.

{guilabel}`Email addresses`
:   The addresses on their profile, and which of them this site verified.
    A verified address matters beyond mail: it is what automatic linking attaches a new provider account to.

{guilabel}`Recent activity`
:   The most recent authentication events for this person, from the audit log.

## From the API

```text
GET @user-account/<userid>
```

Needs `Manage users`, except when a caller asks about their own account.

Add `events` to ask for more or fewer recent entries:

```text
GET @user-account/<userid>?events=50
```

One user at a time, deliberately.
The audit log is bounded per user rather than globally, so folding either answer into the `@users` listing would read one bounded log per row on every page of it.

## Read a badge on a sign-in method

Two badges mean a login that will not work, and both are easy to cause by accident from the providers control panel.

{guilabel}`Disabled`
:   The provider exists and is switched off.
    Nobody can sign in or link through it, including this person.

{guilabel}`Not configured`
:   The provider was deleted while this identity was still stored against it.
    Nothing was deleted from the account: recreating the provider under the same id restores the login.

```{tip}
This is what a "my login stopped working" report usually turns out to be, and it is invisible everywhere else.
```

## Read "not in the retained log"

That is not the same as never signing in.

The audit log is bounded by both a per-user entry count and a retention period, so an account dormant longer than that period has had its entries dropped.
See {doc}`/reference/audit-log` for both settings.

## What this does not show

A password, in any form.
Nothing in this package can read one, and the audit log has never recorded credentials or tokens.

An IP address or a browser, unless you turned that on.
See {doc}`read-the-audit-log`.

## Next steps

-   {doc}`read-the-audit-log` to query the same events across the whole site.
-   {doc}`configure-a-provider` to re-enable or recreate a provider a badge is complaining about.
-   {doc}`troubleshoot` when the account looks right and the sign-in still fails.
-   {doc}`/reference/profiles-and-groups` for the endpoint's full answer.

---
myst:
  html_meta:
    "description": "Find the cause of a failed sign-in by symptom, using the audit log."
    "property=og:description": "Find the cause of a failed sign-in by symptom, using the audit log."
    "property=og:title": "How to troubleshoot sign-in"
---

(how-to-troubleshoot)=

# How to troubleshoot sign-in

Find what went wrong, by symptom.

## Start with the audit log

Before reading source or server logs, read the audit log. It records refusals as
well as successes, and it tells an unknown identity apart from a denied group and
a link collision.

Open **Identity providers → Audit log**, or `GET @audit-log`. Reading it needs
`Manage portal`. See {doc}`read-the-audit-log`.

The event name in the log is the fastest route into the table below.

| Event | Means |
|---|---|
| `authenticated` | a sign-in succeeded |
| `signin-refused` | the sign-in was refused; the entry carries the reason |
| `flow-refused` | the request was rejected before the provider was reached |
| `payload-rejected` | what came back from the provider did not validate |
| `link-refused` | an identity could not be attached |
| `link-collision` | the identity is already on a different account |
| `identity-linked` / `identity-unlinked` | a sign-in method was added or removed |
| `email-verified` | an address was recorded as verified |
| `claims-refreshed` | profile fields were updated from the provider |
| `magic-link-sent` / `magic-link-confirmed` / `magic-link-refused` | the magic-link flow |

## The login button for a provider does not appear

The login page is built from `@login-providers`, which returns only providers
that are **both** enabled and shown.

1. Open the **Identity providers** control panel.
2. Check {guilabel}`Enabled` **and** {guilabel}`Show on the login screen`.

An enabled provider that is not shown is still usable—it stays linkable from a
user's own sign-in methods page—it simply has no button.

If no provider at all appears and you configured one, check the frontend add-on
is registered: see {doc}`install-the-frontend`.

## The login page shows Volto's username and password form instead

The frontend add-on is not loaded. Check `volto.config.js` names
`@plone-collective/volto-identity`, and that the install linked it.

If you *want* both, that is `RAZZLE_IDENTITY_SHOW_PLONE_LOGIN=true`—see
{doc}`install-the-frontend`.

## Redirected to the provider, then `redirect_uri_mismatch`

The redirect URI registered with the provider does not match what this site sent.

The value this site sends is your **frontend** base URL plus the callback path
from the control panel, by default:

```text
https://www.example.com/login-identity
```

Check, in order:

1. You registered the **frontend** URL, not the backend's.
2. The scheme matches—`https` where the provider has `https`.
3. There is no trailing slash on one side and not the other.
4. The callback path in the control panel is what the frontend actually serves.

## The provider authenticates, and Plone says the sign-in failed

Read the audit log entry.

| Reason in the entry | Cause | Fix |
|---|---|---|
| a group restriction | the person is in none of the listed groups | {doc}`map-provider-groups` |
| account creation refused | no account matched and creation is off | {doc}`control-account-creation` |
| `payload-rejected` | the token or userinfo did not validate | check clock skew and the issuer value |

The person signing in is told only that it failed. Naming the reason on the login
page would tell anyone who can reach it which groups matter here.

## An account was created when it should have linked to an existing one

Linking by email needs three switches, and all three must be on. See
{doc}`link-accounts-by-email`.

The most common cause is the third: the provider sends `email_verified` as the
string `"true"`, so every address arrives unverified and matching never fires.

## An existing account is not matched by email

Check in this order:

1. The address on the Plone account is **verified**. An unverified address is not
   matched on.
2. The provider actually sent an address. GitHub does not, for a user whose
   address is private, unless the `user:email` scope was requested.
3. The provider sent `email_verified` as a boolean, not a string.
4. Both trust switches are on.

## Verification is configured and never takes effect

This is the string-boolean case, and it fails silently: sign-in works, every
address arrives unverified, and no error says so.

Turn on {guilabel}`This provider sends verification flags as text`.

A default Keycloak sends a real boolean and does not need it. Oracle Access
Manager, and some customized realms, do.

## Groups are not granted after login

In order:

1. **The provider is sending groups at all.** Keycloak sends none until a Group
   Membership mapper exists; Entra sends none until the app manifest asks.
   Verified for Keycloak 26—see {doc}`providers/keycloak`.
2. {guilabel}`Groups arrive in the claim` matches the claim name the provider uses.
3. The group map has a row for that provider-side name. An unmapped name grants
   nothing, by design.
4. The local group named on the right actually exists. A row pointing at a
   missing group is skipped and logged.
5. {guilabel}`Let this provider set group membership` is on.

## A group restriction refuses everybody

The driver sends no groups.

GitHub and the magic-link driver have no group claim at all, so a list under
{guilabel}`Only these groups may sign in` can never match. The log says so in as
many words rather than reporting a group mismatch.

## The client secret disappeared after saving the form

The form shows a stored secret as a mask, never as its value.

Clearing the field sends an empty string, which is a different instruction, and
it destroys the stored secret. To keep the stored secret, save with the mask
unchanged.

A GenericSetup export omits secrets, so it cannot restore one. Get a new secret
from the provider. See {doc}`/concepts/secrets`.

## Test connection succeeds and login still fails

**Test connection** fetches discovery and validates configuration. It does not
sign anybody in.

So it passing tells you the issuer and network are right, and says nothing about
the client secret, the redirect URI, or the trust switches. Those show up only in
a real sign-in, in the audit log.

## The magic link never arrives

1. The site's mail settings are filled in. `plone.api.portal.send_email` refuses
   to run while the **Mail** control panel is empty, and the failure does not
   mention mail.
2. Send a test message from the Mail control panel.
3. Check the rate limit—5 per hour per address and per IP by default.
4. The token is valid for at most 15 minutes whatever you configured.

The send endpoint answers identically whether or not the address has an account,
so a successful-looking response does not prove the address is known here.

## Back-channel logout returns 200 and the session persists

A logout token carrying only a `sid`, with no `sub`, cannot be resolved to a
session this site knows about.

See {doc}`enable-back-channel-logout`.

## Related

- {doc}`read-the-audit-log`—how to read what the log records
- {doc}`/reference/audit-log`—every event name and field
- {doc}`/reference/stability`—what may change between alpha releases

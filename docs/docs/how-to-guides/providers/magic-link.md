---
myst:
  html_meta:
    "description": "Let people sign in to Plone with an emailed single-use link, with no external provider."
    "property=og:description": "Let people sign in to Plone with an emailed single-use link, with no external provider."
    "property=og:title": "Provider recipe: magic link"
---

(how-to-provider-magic-link)=

# Emailed magic link

Sign people in with a single-use link sent to their address. There is no
external provider: this site mints and checks the token itself.

```{note}
Verified against the demo stack on 2026-09-05.
```

## 1. Check the site can send mail

This is the step that gets skipped, and it fails in a way that reads as a bug in
the login flow.

The site's mail settings must be filled in—**Mail** control panel, SMTP host
and "From" address. `plone.api.portal.send_email` refuses to run at all while
they are empty, so the magic-link endpoint fails before any mail is attempted,
and the error says nothing about mail.

Send a test message from the Mail control panel before continuing.

## 2. Add the provider

1. Open the **Identity providers** control panel.
2. Add a provider and choose **Email** (`email`).
3. On the **Settings** tab:

   | Field | Default | What it does |
   |---|---|---|
   | Title | | what the form is labelled |
   | Token lifetime (seconds) | `900` | how long a link stays usable |
   | Rate limit per hour | `5` | sends allowed per address and per IP each hour |

4. Set **Show on the login screen** on, so the form appears.
5. Save.

```{important}
The magic-link form appears on `/login` only when the `email` provider is
**shown on the login screen**, not merely enabled. The login page builds itself
from the providers `@login-providers` returns, and that endpoint filters on
exactly this flag.

An `email` provider that is enabled and hidden still verifies addresses and can
still be linked to an account. It just has no button.
```

There is no client ID and no secret. Nothing is registered anywhere.

## 3. Sign in

Open `/login` and use the email form. Enter an address, and a link arrives.

Following the link signs you in and burns the token.

## Verify

- The audit log has a `magic-link-sent` entry, then `magic-link-confirmed`.
- Following the same link twice fails the second time.
- `/identities` lists an identity for the address.

## What the token guarantees

| | |
|---|---|
| Lifetime | at most 15 minutes, whatever you configure |
| Reuse | burned server side after one use |
| Rate limit | per address **and** per IP |
| Enumeration | the send endpoint answers identically whether or not the address has an account |

The last one is the reason the endpoint never says "no such user": that answer
would turn the login page into a way to test which addresses have accounts here.

## Known quirks

- **Configured lifetime is a ceiling, not a promise.** Setting the token
  lifetime above 900 seconds does not extend it past 15 minutes.
- **There are no account or group settings.** `IEmailSettings` carries only the
  two fields above. No trust switch, no link-by-email switch, no account-creation
  switch, no group claim. An `email` provider always creates accounts.
- **Its verification is this site's own.** An address that answered a link from
  this site is verified by this site, which is the strongest form of the claim
  this package has—so there is nothing to decide whether to trust.

## Related

- {doc}`../link-accounts-by-email`—what a verified address then allows
- {doc}`/reference/audit-log`—the three magic-link event names
- {doc}`../troubleshoot`—when the link never arrives

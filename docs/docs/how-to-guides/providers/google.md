---
myst:
  html_meta:
    "description": "Add Google sign-in to a Plone site."
    "property=og:description": "Add Google sign-in to a Plone site."
    "property=og:title": "Provider recipe: Google"
---

(how-to-provider-google)=

# Google

Sign in with a Google account.

```{warning}
**Provider-side steps are not verified.** The Plone side below is read from this
package's source and is accurate. The Google Cloud console steps have not been
walked through against a live project, and that console changes often, so follow
[Google's own OpenID Connect documentation](https://developers.google.com/identity/openid-connect/openid-connect)
for the console and use the tables here for Plone.
```

## 1. What you need from Google

Create an OAuth 2.0 Client ID of type **Web application** in the Google Cloud
console, and note the client ID and client secret.

The authorized redirect URI is:

```text
https://www.example.com/login-identity
```

## 2. Add the provider

1. Open the **Identity providers** control panel.
2. Add a provider and choose **Google** (`google`).
3. On the **Settings** tab:

   | Field | Value |
   |---|---|
   | Title | `Google` |
   | Client ID | from step 1 |
   | Client secret | from step 1 |
   | Scope | leave empty for the default `openid email profile` |

4. Save, then **Test connection**.

There is no issuer field: the driver fixes the issuer at
`https://accounts.google.com` and discovers everything else from it.

## 3. The trust switches

On the **Accounts** tab.

**This driver ships with email verification trusted.** `google` and `github` are
the only two shipped drivers that do.

| Field | Default | Guidance |
|---|---|---|
| Trust this provider's email verification | **on** | Reasonable for consumer Google accounts |
| Attach to an existing account with the same verified email | off | Turn on to merge with existing accounts |
| Let this provider create accounts | on | Turn off to admit only people who already have an account |

```{warning}
A Google Workspace domain you do not control is not the same trust decision as
consumer Google. If someone else administers the domain, they decide who gets an
address in it, and therefore who reaches an account here by email matching.
```

## 4. Groups

**There is no Groups tab for a Google provider.** The `google` driver's settings
schema is `IOAuth2Settings`, which carries no group claim, no allowed-groups
list, and no sync switch. Google sends this package no groups it can read.

To restrict which Google accounts may sign in, turn off account creation and add
the accounts yourself. See {doc}`../control-account-creation`.

## Verify

1. `/login` shows the Google button.
2. Signing in returns you signed in.
3. `/identities` lists the identity; the subject is Google's `sub`.
4. The audit log has an `authenticated` entry.

## Known quirks

- **The subject is `sub`, not the email address.** A person who changes their
  Google address keeps their Plone account.
- **Unverified Google accounts exist.** Google sends `email_verified: false` for
  them, and this package then treats the address as unverified regardless of the
  trust switch. That is the switch working.

## Related

- {doc}`/reference/shipped-drivers`—the driver's exact defaults
- {doc}`../link-accounts-by-email`
- {doc}`../troubleshoot`

---
myst:
  html_meta:
    "description": "Add GitHub sign-in to a Plone site."
    "property=og:description": "Add GitHub sign-in to a Plone site."
    "property=og:title": "Provider recipe: GitHub"
---

(how-to-provider-github)=

# GitHub

Sign in with a GitHub account.

```{warning}
**Provider-side steps are not verified.** The Plone side of this recipe is read
from this package's source and is accurate; the GitHub console steps are written
from GitHub's documentation and have not been walked through against a live
account. Follow [GitHub's own OAuth app documentation](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app)
for the console, and use the table in step 2 for what to put in Plone.
```

GitHub is not an OpenID Connect provider. It has no discovery document, no
`id_token`, and no groups. The `github` driver exists because of that: it talks
to GitHub's own API rather than to a standard.

## 1. What you need from GitHub

Register an OAuth app and note the client ID and client secret.

The authorization callback URL is your frontend base URL plus the callback path:

```text
https://www.example.com/login-identity
```

## 2. Add the provider

1. Open the **Identity providers** control panel.
2. Add a provider and choose **GitHub** (`github`).
3. On the **Settings** tab:

   | Field | Value |
   |---|---|
   | Title | `GitHub` |
   | Client ID | from step 1 |
   | Client secret | from step 1 |
   | Scope | leave empty for the default `read:user user:email` |

4. Save.

There is no issuer field. GitHub's endpoints are fixed and built into the
package; there is nothing to discover.

## 3. The trust switches

On the **Accounts** tab.

**This driver ships with email verification trusted**, which is unusual here—
`github` and `google` are the only two that do. GitHub only reports an address as
verified once the account has answered mail at it, which is the standard this
package asks for.

| Field | Default | Guidance |
|---|---|---|
| Trust this provider's email verification | **on** | Reasonable to leave on |
| Attach to an existing account with the same verified email | off | Turn on to merge with existing accounts |
| Let this provider create accounts | on | Turn off if membership is decided here |

## 4. Groups

**There is no Groups tab for a GitHub provider.** `IGitHubSettings` extends
`IOAuth2Settings` and adds nothing, so there is no group claim to name and no
allowed-groups list to fill in. GitHub sends none.

To restrict sign-in with GitHub, do it another way: turn off account creation and
add the accounts yourself. See {doc}`../control-account-creation`.

## Verify

1. `/login` shows the GitHub button.
2. Signing in returns you to the site, signed in.
3. `/identities` lists the identity, and the subject is a GitHub numeric id.
4. The audit log has an `authenticated` entry.

## Known quirks

- **The user id is the numeric id, not the username.** The driver reads `id` then
  `node_id`. A person who renames their GitHub account keeps their Plone account.
- **A private email address may not arrive.** The `user:email` scope is in the
  default for that reason; a user whose address is private on GitHub still has it
  released to an app that asked for that scope. Without an address, linking by
  email cannot fire.

## Related

- {doc}`/reference/shipped-drivers`—the driver's exact defaults
- {doc}`../link-accounts-by-email`—what a trusted verified address allows
- {doc}`../troubleshoot`

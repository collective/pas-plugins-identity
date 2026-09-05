---
myst:
  html_meta:
    "description": "Sign in to one Plone site using accounts from another Plone site."
    "property=og:description": "Sign in to one Plone site using accounts from another Plone site."
    "property=og:title": "Provider recipe: another Plone site"
---

(how-to-provider-another-plone-site)=

# Another Plone site

Sign in to this site with accounts that live on a different Plone site.

The other site needs `pas.plugins.identity[server]` installed and acting as an
authorization server. This site needs only the core layer.

```{note}
Verified against the demo stack on 2026-09-05.
{doc}`/tutorials/federation-demo` builds exactly this, end to end, in Docker.
```

## 1. What you need from the other site

Ask whoever runs it for:

| | |
|---|---|
| Issuer URL | its base URL, for example `https://id.example.com` |
| Client ID | minted when they register your site |
| Client secret | shown **once**, when the client is created |

They create the client by following {doc}`../register-an-oauth-client`, giving
your redirect URI:

```text
https://www.example.com/login-identity
```

```{warning}
The client secret is displayed once, in the response that mints it.
It cannot be recovered afterwards. If it is lost, they rotate it and give you a new one.
```

## 2. Add the provider

1. Open the **Identity providers** control panel.
2. Add a provider and choose the **Plone site** driver (`plone-identity`).
3. On the **Settings** tab, fill in:

   | Field | Value |
   |---|---|
   | Title | what the button should say, for example `id.example.com` |
   | Issuer | the other site's base URL |
   | Client ID | from step 1 |
   | Client secret | from step 1 |
   | Scope | leave empty to use the driver's default |

   The default scope is `openid email profile address`. The `address` scope is
   what this driver adds over the generic OIDC one, because a Plone profile has a
   location field worth carrying across.

4. Save.

Everything else—the authorization endpoint, the token endpoint, the signing
keys—is fetched from `<issuer>/.well-known/openid-configuration` at runtime.
You do not configure any of it.

## 3. Test the connection

Use the **Test connection** action on the provider.

It fetches the discovery document, clearing the cache first, and reports what it
found. A failure here is a wrong issuer, a firewall, or a site that has not
applied the `server` profile.

## 4. Decide what the other site is allowed to mean

On the **Accounts** tab:

| Field | Set it to | Why |
|---|---|---|
| Trust this provider's email verification | on, if you run both sites | See {doc}`../link-accounts-by-email` |
| Attach to an existing account with the same verified email | on, to merge with existing accounts | Needs the switch above |
| Let this provider create accounts | on, unless membership is decided here | See {doc}`../control-account-creation` |

A Plone site running this package releases `email_verified: true` only for
addresses it has actually verified, so trusting it is reasonable when you run
both ends. Trusting a site you do not run is a decision about that site's
sign-up rules, not about this software.

## 5. Map its groups, if you want them

On the **Groups** tab, leave **Groups arrive in the claim** at `groups`—that is
what a Plone site running the `server` layer emits.

Then add one row per group you want to honour. See {doc}`../map-provider-groups`.

An unmapped group grants nothing and is never created here.

## 6. Sign in

Open `/login`. The provider's button is there.

Signing in sends you to the other site, which asks you to approve the request
once, and returns you here signed in.

## Verify

- `/identities` on this site lists the new identity, naming the provider.
- The audit log has an `authenticated` entry for it—see {doc}`../read-the-audit-log`.
- The user's profile carries the fullname, email and, if you mapped them, the
  website, description, location and portrait that came across.

## Known quirks

- **The issuer must resolve from both places.** Your browser follows it to sign
  in, and this site's server fetches discovery from it. In containers those are
  often different networks and the same URL has to work in both.
- **Consent is asked once** per user and client. To see it again, withdraw the
  application's access from `/applications` on the other site.

## Related

- {doc}`/tutorials/federation-demo`—this recipe, running, in Docker
- {doc}`/concepts/federation`—why the issuer is configured rather than derived
- {doc}`../register-an-oauth-client`—the other side of this setup

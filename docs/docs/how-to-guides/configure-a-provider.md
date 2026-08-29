---
myst:
  html_meta:
    "description": "Add, test, edit, and delete an identity provider from the Plone control panel."
    "property=og:description": "Add, test, edit, and delete an identity provider from the Plone control panel."
    "property=og:title": "How to configure a provider"
---

(how-to-configure-a-provider)=

# How to configure a provider

This guide shows you how to register an identity provider, test it, and remove it.

A provider is a configured instance of a driver.
The driver knows how to talk to a kind of service, and the provider record holds this site's credentials for one particular service.
Two GitHub organizations are two providers sharing one driver.

For the drivers you can choose from, see {doc}`/reference/shipped-drivers`.

## Add a provider

1.  Open the **Identity providers** control panel.
2.  Choose a driver.
3.  Fill in the form.

The form is generated from the driver's published schema, so a site that installs a third-party driver gets that driver's form with no frontend change.

Configuration lives in the registry, one record per setting, under `pas.plugins.identity.providers.<id>.<field>`.
A GenericSetup export therefore describes a site's providers field by field, and one setting can be changed without rewriting the rest.

## Decide whether it works, and whether it is advertised

Two switches, and they answer different questions.

{guilabel}`Enabled`
:   Whether the provider works at all.
    A disabled provider keeps its settings and its stored identities, and nobody can sign in or link through it.

{guilabel}`Show on the login screen`
:   Whether the login page offers a button for it.

An enabled provider that is not shown is still usable.
It stays linkable from a user's own {guilabel}`Sign-in methods` page, and an account already linked to it still signs in through it.

That is what a staff-only or invitation-only provider looks like: usable, and not advertised to everybody who reaches the login form.

```{note}
A provider configured before this setting existed reads back as shown.
Upgrading a site does not take its login buttons away.
```

## Give it a look

The {guilabel}`Style` tab decides how the button is drawn, and none of it changes what the provider does.

{guilabel}`Icon`
:   An SVG document, pasted as its source.
    Empty means no icon, and the button then shows the title alone rather than a placeholder every provider shares.

{guilabel}`Background colour` and {guilabel}`Foreground colour`
:   Hex values such as `#24292f`.
    Empty leaves the theme's own styling alone.

The icon is rendered *inside* the page rather than as an image, which is what lets a single-colour icon take the button's own text colour.
That is also why what you paste is sanitized as it is stored: only the shapes and attributes on a fixed list survive, no attribute may reference an address elsewhere, and a document that is not an SVG is refused rather than quietly emptied.

```{warning}
Sanitizing happens on save, not on render.
An icon that was refused was never stored, and an icon that was accepted is the version the site serves — not the version you pasted.
Check the button after saving.
```

## Test the connection

Each provider has a **Test connection** action.

It fetches the provider's discovery document, or validates the static configuration for drivers that have no discovery, and reports what it found.
It clears the discovery cache first, because a button that reports the answer from twelve hours ago is worse than no button at all.

## Change a secret, or keep it

The control panel serializes a stored client secret as a mask, never as its value.

-   To keep the stored secret, save the form with the mask unchanged.
-   To replace the secret, type the new one over the mask.

```{warning}
Do not clear the field to keep the existing secret.
Blanking it sends an empty string, which is a different instruction, and it destroys the stored secret.
```

A GenericSetup export omits secrets, so an export of your provider configuration is not enough to rebuild a working site.
The secrets have to travel separately, by whatever means your deployment already uses for secrets.

Read {doc}`/concepts/secrets` for why secrets behave differently here than they do when the site acts as an authorization server.

## Delete a provider

Deleting a provider removes its configuration.

It does **not** delete the identities linked through it.
Those are account data, and a configuration change is not an instruction to lock people out.
If you want the identities gone as well, remove them first.

## Decide whether the provider's email verification counts

Two switches on the provider's form, both off unless a driver knows better, and both about the same question: how far this site trusts what the provider says about an address.

{guilabel}`This provider's email verification counts`
:   Switch it on and an address the provider says it verified is recorded as verified here, exactly as a magic link from this site would record one.
    That address then satisfies automatic linking, and the site releases `email_verified: true` for it when it acts as an authorization server.
    Switch it on only for a provider that really checks.
    `google` and `github` ship with it on; every other driver ships with it off.

{guilabel}`Attach to an existing account with the same verified email`
:   Whether a person signing in with this provider for the first time is attached to an account that already exists, when the address matches a verified one.
    It needs the switch above as well: the address being matched on is the one this provider just sent, so a provider whose word the site does not take cannot reach an account with it.

```{warning}
A provider that marks addresses verified according to weaker rules than yours is an account takeover waiting to happen: somebody registers there with an address that belongs to one of your users, and this site hands them the account.
Turn the first switch on only where you know the provider refuses to call an address verified until the account has answered mail at it.

Turning it off later stops it verifying anything new; addresses already recorded as verified stay that way, because they are identities and removing one is an unlink rather than a configuration change.
```

See {doc}`/concepts/email-verification` for the whole rule.

## Configure magic-link sign-in

The `email` driver needs no external provider.
The site emails a signed, single-use token instead.

Add a provider using the `email` driver, and the sign-in option appears on the login page.

The token lives for at most fifteen minutes whatever you configure, and it is burned server-side after one use.
The send endpoint is rate limited per address and per IP, and answers identically whether or not the address belongs to an account.

## Map the provider's groups to local groups

A provider that asserts group membership can grant local groups.
Nothing happens until you say which of its groups mean something here: the group map starts empty, and an empty map grants nothing.

Set **Groups arrive in the claim** to the claim the provider puts them in.
`groups` is the default and what Keycloak, Okta, Entra, and a Plone site running this package's `[server]` layer all emit.
Use a dotted path for a provider that nests them, such as `realm_access.roles`.

Then fill in the group map: one row per provider-side group name, each pointing at a local group id.

Three rules make this safe to leave running.

A name with no row grants nothing, and no group is ever created.
A group claim is whatever the provider's own directory happens to be called, so minting local groups from it would let anyone who can name a group at the far end create one here.
A row pointing at a group this site does not have is skipped and logged.

Every login reconciles, so a membership revoked at the provider stops granting anything here without anyone editing the site.

A login only ever takes back what that same provider granted.
The identity record remembers each provider's own grant, so a group you granted by hand survives every sign-in, and two providers cannot revoke each other's grants.

```{note}
Clearing a map does **not** strip the groups it had granted.
Clearing is at least as likely to mean "I am rewriting this" as "revoke everything", so a provider with an empty map touches no membership at all.
To take its grants back, empty the map's *values* rather than the map, and let one login reconcile.
```

## Next steps

-   {doc}`enable-back-channel-logout`, so a sign-out at the provider ends the session here.
-   {doc}`/reference/audit-log`, to confirm that sign-ins are landing.

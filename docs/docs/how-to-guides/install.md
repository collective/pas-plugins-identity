---
myst:
  html_meta:
    "description": "Install pas.plugins.identity in a Plone site, decide whether you need the server extra, and verify the result."
    "property=og:description": "Install pas.plugins.identity in a Plone site, decide whether you need the server extra, and verify the result."
    "property=og:title": "How to install the package"
---

(how-to-install)=

# How to install the package

This guide shows you how to install `pas.plugins.identity` in a Plone site and confirm that it works.

## Requirements

Plone 6.2, and Python 3.12, 3.13, or 3.14.

## Install the backend

Install the package:

```shell
pip install pas.plugins.identity
```

Then install the add-on in your site, either through the add-ons control panel or by applying the `pas.plugins.identity:default` GenericSetup profile.

That one profile installs everything: the control panel, both PAS plugins, the `UserProfile` and `UserGroup` content types with their workflows, and the catalog they are filed in.
It also sets the four registry records described in {doc}`/reference/user-content` and points them at this package's own types, so there is nothing further to configure.

```{warning}
Users and groups as content used to be a separate `[content]` extra with a profile of its own, and it is not one any more.

A site that installed an earlier version has the old arrangement recorded in its database, and the merged profile is not applied to it by an upgrade step.
**Reinstall the add-on** — uninstall and install it again from the add-ons control panel, or apply `pas.plugins.identity:default` from `portal_setup`.

Until you do, the site looks installed and has no content types, no catalog and no profile plugin.
Reinstalling leaves every existing `UserProfile` where it is; see the note below.
```

If you want the site to act as an authorization server that other applications sign in against, install that extra and apply its profile:

```shell
pip install "pas.plugins.identity[server]"
```

```text
pas.plugins.identity.server:default
```

The server layer is its own entry in the add-ons control panel, with its own install and uninstall button.
The panel shows no version beside it, because the entry is named after a package rather than a distribution.

Every profile has a matching uninstall profile, and uninstalling is tested.
The test installs, uninstalls, and asserts that the site still works with no plugin, registry key, or tool left behind.

```{note}
Uninstalling removes the catalog, the content types, and the workflows.
It leaves every `UserProfile` object and its data exactly where it is.
Uninstalling an add-on is a configuration change, not an instruction to delete everyone's account data.
```

## Install the frontend

The Volto add-on ships from the same repository, as `@plone-collective/volto-identity`.

It provides `/login`, the callback route, `/identities` for managing your own sign-in methods, and the control panels.

## Set the login callback URL

Nothing signs in until you set this.

The callback URL is the frontend route that providers redirect back to, and it must match the redirect URI you register with every provider.
It is a route in the Volto frontend rather than a backend view, so the package cannot derive it from the portal URL.

Set it in the **Identity providers** control panel.

## Configure at least one provider

Nothing happens until a provider is configured.

Follow {doc}`configure-a-provider`.

## Verify the install

A working install has all four of these:

-   the `identity` plugin in `acl_users`, active for extraction, authentication, and credentials reset
-   the `identity_profile` plugin beside it, at the top of `IPropertiesPlugin`
-   at least one provider in the control panel, with a title and a driver
-   a callback URL that matches what the provider has registered

If the second one is missing, the site was installed by an earlier version and needs the add-on reinstalled.

If sign-in fails, read the audit log before you read the source.
The log records refusals as well as successes, and it tells an unknown identity apart from a denied group and a link collision.
See {doc}`read-the-audit-log`.

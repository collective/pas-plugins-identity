---
myst:
  html_meta:
    "description": "Install pas.plugins.identity in a Plone site, choose the extras you need, and verify the result."
    "property=og:description": "Install pas.plugins.identity in a Plone site, choose the extras you need, and verify the result."
    "property=og:title": "How to install the package"
---

(how-to-install)=

# How to install the package

This guide shows you how to install `pas.plugins.identity` in a Plone site and confirm that it works.

## Requirements

Plone 6.2, and Python 3.12, 3.13, or 3.14.

## Install the backend

Install the core layer:

```shell
pip install pas.plugins.identity
```

Then install the add-on in your site, either through the add-ons control panel or by applying the `pas.plugins.identity:default` GenericSetup profile.

If you want content-backed profiles and groups, install the extra as well.
It sets the four registry records described in {doc}`/reference/user-content` and points them at its own container, so there is nothing further to configure.

```shell
pip install "pas.plugins.identity[profile]"
```

Then apply its profile:

```text
pas.plugins.identity:profile
```

If you want the site to act as an authorization server that other applications sign in against, install that extra and apply its profile:

```shell
pip install "pas.plugins.identity[server]"
```

```text
pas.plugins.identity:server
```

Every profile has a matching uninstall profile, and uninstalling is tested.
The test installs, uninstalls, and asserts that the site still works with no plugin, registry key, or tool left behind.

```{note}
Uninstalling the `profile` extra removes the catalog, the content types, and the workflows.
It leaves every `Profile` object and its data exactly where it is.
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

A working install has all three of these:

-   the `identity` plugin in `acl_users`, active for extraction, authentication, and credentials reset
-   at least one provider in the control panel, with a title and a driver
-   a callback URL that matches what the provider has registered

If sign-in fails, read the audit log before you read the source.
The log records refusals as well as successes, and it tells an unknown identity apart from a denied group and a link collision.
See {doc}`read-the-audit-log`.

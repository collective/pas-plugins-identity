# Installation

## Requirements

Plone 6.2 and Python 3.12, 3.13 or 3.14.

## Install

```shell
pip install pas.plugins.identity
```

Then install the add-on in your site, through the add-ons control panel or by
applying the `pas.plugins.identity:default` GenericSetup profile.

For content-backed profiles and groups, install the extra and apply its
profile as well:

```shell
pip install "pas.plugins.identity[profile]"
```

```
pas.plugins.identity:profile
```

Every profile has a matching uninstall profile, and uninstalling is tested:
install, uninstall, and the site still works with no plugin, registry key or
tool left behind.

:::{note}
Uninstalling the `profile` extra removes the catalog, the content types and
the workflows. It leaves every `Profile` object and its data exactly where it
is. Uninstalling an add-on is a configuration change, not an instruction to
delete everyone's account data.
:::

## Configure a provider

Nothing happens until a provider is configured. Go to the
**Identity providers** control panel and add one; see {doc}`providers`.

You will also need to set the **login callback URL** — the frontend route
providers redirect back to, which must match the redirect URI registered with
every provider. It is a route in the Volto frontend, not a backend view, so it
cannot be derived from the portal URL.

## The frontend add-on

The Volto add-on ships from the same repository as
`@plone-collective/volto-identity` and provides `/login`, the callback route,
`/identities` for managing your own sign-in methods, and the providers control
panel.

## Verifying the install

A working install has:

- the `identity` plugin in `acl_users`, active for extraction, authentication
  and credentials reset;
- at least one provider in the control panel, with a title and a driver;
- a callback URL that matches what the provider has registered.

If sign-in fails, read the audit log before reading the source: it records
refusals as well as successes, and it distinguishes an unknown identity from a
denied group from a link collision. See {doc}`audit-log`.

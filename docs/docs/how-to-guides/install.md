---
myst:
  html_meta:
    "description": "Install the pas.plugins.identity backend in a Plone site and verify the result."
    "property=og:description": "Install the pas.plugins.identity backend in a Plone site and verify the result."
    "property=og:title": "How to install the backend"
---

(how-to-install)=

# How to install the backend

Install `pas.plugins.identity` in a Plone site and confirm it works.

This guide covers the backend only.
The frontend is a separate package and a separate guide: {doc}`install-the-frontend`.

```{note}
There are no GenericSetup upgrade steps in this release.
See {doc}`upgrade` before taking a new alpha, and {doc}`/reference/stability` for what that implies.
```

## Requirements

| | |
|---|---|
| Plone | 6.2 |
| Python | 3.12, 3.13, or 3.14 |
| Frontend | Volto, for sign-in. Classic UI is not supported yet—see {doc}`/reference/stability` |

## Install the backend

1. Add `pas.plugins.identity` to your backend's requirements.

   Two extras exist. Ask for the ones you want, comma-separated:

   | Extra | Adds | Needs |
   |---|---|---|
   | `server` | The authorization server layer, and a GenericSetup profile of its own. | step 4 below |
   | `sql` | An audit sink writing a row per event to a relational database. | `IDENTITY_AUDIT_DSN`, and `sql` named in `audit_sinks` |

   ```shell
   pip install "pas.plugins.identity[server]"
   ```

   Neither is needed for ordinary sign-in. See {doc}`/reference/audit-log` for
   the `sql` sink.

2. Restart the Plone instance.

   This is a ZCML change, so the site does not see the add-on until it restarts.

3. Install the add-on in your site.

   Either use the add-ons control panel, or apply the GenericSetup profile:

   ```text
   pas.plugins.identity:default
   ```

   That one profile installs everything: the control panel, both PAS plugins, the `UserProfile` and `UserGroup` content types with their workflows, and the catalog they are filed in.
   It also sets the registry records described in {doc}`/reference/user-content` and points them at this package's own types.

4. If you asked for the `server` extra, apply its profile too:

   ```text
   pas.plugins.identity.server:default
   ```

   The server layer is its own entry in the add-ons control panel, with its own install and uninstall button.
   The panel shows no version beside it, because the entry is named after a package rather than a distribution.

## Set the login callback URL

Nothing signs in until this matches what your providers have registered.

1. Open the **Identity providers** control panel.
2. Set **Callback URL** to the frontend route that providers redirect back to.

   The default is `/login-identity`, which is the route the Volto add-on registers.
   Most sites never change it.

The value is a path, and the full redirect URI you give a provider is your frontend's base URL plus that path:

```text
https://www.example.com/login-identity
```

It is a route in the Volto frontend rather than a backend view, so the package cannot derive it from the portal URL.
That is why it is a setting.

## Verify

A working install has all four of these:

- the `identity` plugin in `acl_users`, active for extraction, authentication, and credentials reset
- the `identity_profile` plugin beside it, at the top of `IPropertiesPlugin`
- at least one provider in the control panel, with a title and a driver
- a callback URL that matches what the provider has registered

## Uninstalling

Every profile has a matching uninstall profile, and uninstalling is tested: the test installs, uninstalls, and asserts that the site still works with no plugin, registry key, or tool left behind.

```{note}
Uninstalling removes the catalog, the content types, and the workflows.
It leaves every `UserProfile` object and its data exactly where it is.
Uninstalling an add-on is a configuration change, not an instruction to delete everyone's account data.
```

## Next steps

1. {doc}`install-the-frontend`—the Volto add-on, without which nobody can sign in.
2. {doc}`providers/index`—pick the provider you are adding and follow its recipe.
3. {doc}`troubleshoot`—if sign-in fails, start here rather than in the source.

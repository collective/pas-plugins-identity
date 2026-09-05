---
myst:
  html_meta:
    "description": "Add the volto-identity add-on to a Volto project so users can sign in."
    "property=og:description": "Add the volto-identity add-on to a Volto project so users can sign in."
    "property=og:title": "How to install the frontend"
---

(how-to-install-the-frontend)=

# How to install the frontend

Add `@plone-collective/volto-identity` to a Volto project.

Without it the backend is installed and nobody can sign in: every sign-in route this package uses is registered by the frontend add-on.

Do {doc}`install` first.

## Requirements

| | |
|---|---|
| Volto | developed against 19.3.0 |
| React | 18 |
| Also needs | `react-redux` 8, `react-router-dom` 5, `@plone/components` |

```{note}
The package is **not published to npm** yet, and there is no publish workflow.
Install it from the repository.
```

## Add the add-on

1. Add the package to your project's `package.json` dependencies, from the repository:

   ```json
   {
     "dependencies": {
       "@plone-collective/volto-identity": "github:collective/pas-plugins-identity#main&path:/frontend/packages/volto-identity"
     }
   }
   ```

   If your project vendors its add-ons with `mrs-developer` instead, add the repository there and point at `frontend/packages/volto-identity`.

2. Register it in `volto.config.js`:

   ```js
   const addons = ["@plone-collective/volto-identity"];
   const theme = "";

   module.exports = {
     addons,
     theme,
   };
   ```

3. Install and start:

   ```shell
   pnpm install
   pnpm start
   ```

## Verify

Open `/login` on the frontend.
The page lists the providers the backend has configured and enabled, and no others.

```{image} /_static/screens/login-page-options.png
:alt: A login page listing the configured providers, with a link to sign in with a password instead
```


If the page is Volto's own username-and-password form instead, the add-on is not registered—check `volto.config.js` and that `pnpm install` linked the package.

If the page loads but lists no providers, the backend has none enabled yet: see {doc}`providers/index`.

## Hide the Plone login form

The add-on hides Volto's built-in username-and-password form by default, so `/login` offers only the configured providers.

To show it as well—useful while migrating, when local accounts still need a way in—set the environment variable on the frontend process:

```shell
RAZZLE_IDENTITY_SHOW_PLONE_LOGIN=true
```

Two things to know about it:

- It is read at **run** time, not baked in at build time, so you can change it without rebuilding.
- `RAZZLE_` is the only prefix Volto carries through to the browser, which is why the name has it.

The equivalent setting, if you would rather set it in code, is `config.settings.identityShowPloneLogin`.

Volto's own login form stays reachable at `/fallback_login` whether or not you set this.

## What the add-on registers

Ten routes:

| Path | What it is |
|---|---|
| `/login` and `/**/login` | The provider list, replacing Volto's login |
| `/login-identity` | The callback providers redirect back to |
| `/first-login` | The gate a new account passes through once |
| `/fallback_login` | Volto's own login form, kept reachable |
| `/identities` | Manage your own sign-in methods |
| `/oauth-consent` | The consent screen, `server` layer |
| `/applications` | Applications using your data, `server` layer |
| `/controlpanel/identity-providers` | The provider control panel |
| `/controlpanel/identity-clients` | The client control panel, `server` layer |
| `/controlpanel/users/:userid/account` | One user's sign-in methods, for administrators |

It also registers views for the `UserProfile` and `UserGroup` content types, a `provider_icon` widget, reducers, and a menu entry.

The full surface is in {doc}`/reference/frontend`.

## Next steps

1. {doc}`providers/index`—add your first provider.
2. {doc}`/reference/frontend`—routes, environment variables, and what you can override.
3. {doc}`troubleshoot`—if `/login` does not show what you expect.

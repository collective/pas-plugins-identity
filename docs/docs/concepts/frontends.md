---
myst:
  html_meta:
    "description": "Why the pas.plugins.identity frontend is split into a shared core and one add-on per frontend, for Volto and Plone Aurora."
    "property=og:description": "Why the pas.plugins.identity frontend is split into a shared core and one add-on per frontend, for Volto and Plone Aurora."
    "property=og:title": "About the two frontends"
    "keywords": "Plone, pas.plugins.identity, Volto, Plone Aurora, identity-core, frontend"
---

(concepts-frontends)=

# About the two frontends

Plone has two React frontends: Volto, and its successor, Plone Aurora.
They run different versions of React, route differently, and translate with different libraries.
A site runs one of them.
The sign-in it offers is the same either way, because the package ships one add-on for each, built on a shared core.

`@plone-collective/identity-core`
:   What both frontends share: the REST payload types, a table of every REST path, the helpers that need no framework, the login components, and the card a provider's redirect lands on.

`@plone-collective/volto-identity`
:   The Volto add-on.
    Everything this package's frontend does: sign-in, the identities page, the profile, consent, and the control panels.

`@plone-collective/aurora-identity`
:   The Plone Aurora add-on.
    Sign-in: the login page, starting a sign-in with a provider, and finishing it.

<!-- frontend/packages/identity-core/src/index.ts, frontend/packages/aurora-identity/index.ts -->

```{mermaid}
:config: {"flowchart": {"htmlLabels": false}}
flowchart TB
  core["identity-core<br/>types, endpoints, helpers,<br/>login components"]
  volto["volto-identity<br/>React 18, Redux, react-intl"]
  aurora["aurora-identity<br/>React 19, React Router, i18next"]
  backend["pas.plugins.identity<br/>REST API"]
  volto --> core
  aurora --> core
  volto -->|"through Volto's API proxy"| backend
  aurora -->|"from Aurora's server"| backend
```

## What the core may not import

The core imports no frontend framework.
Not Volto, not Aurora, not Redux, not a router, and not an i18n library.
React, `react-aria-components` and `@plone/components` are allowed, because both frontends have them.
An ESLint rule rejects anything else.

<!-- frontend/.eslintrc.js, the override for packages/identity-core/** -->

A component still needs to translate a message, link to a page, and draw an icon, and each frontend does those differently.
So the core's components ask for them through `useIdentityUI()`, and each add-on wraps its pages in a provider that answers:

| Asked for | Volto's answer | Aurora's answer |
|---|---|---|
| Translating a message | `react-intl` | `i18next` |
| Linking within the site | Volto's router link | React Router's link |
| Icons | Volto's icons | Quanta's icons, from `@plone/icons` |
| The password-reset page | `/passwordreset` | `/reset-password` |

<!-- frontend/packages/identity-core/src/components/IdentityUI/IdentityUI.tsx, frontend/packages/volto-identity/src/components/IdentityUI/VoltoIdentityUI.tsx, frontend/packages/aurora-identity/components/IdentityUI/AuroraIdentityUI.tsx -->

Without a provider the components still render, in English, with plain links and plain icons.

## One set of translations

The core's messages are declared with `defineMessages`, and their translations live in the core's gettext catalogues.
Volto reads those catalogues as they are.
For Aurora, `pnpm i18n` in the harness writes them into the Aurora add-on's `locales/<lang>/common.json`, so a translation is made once and reaches both frontends.

<!-- frontend/packages/identity-core/locales/, frontend/packages/aurora-identity/scripts/i18n.mjs, frontend/packages/aurora-identity/lib/i18n.ts -->

## One look, two themes

The core's styles are plain CSS, since Aurora has no Sass compiler.
They read `--identity-*` custom properties, which the core defines with values that suit Volto.
The Aurora add-on redefines the ones a Quanta page shows the difference in: the accent, the state colours, the surfaces, and the width of a provider button.
A site restyles either frontend the same way, by redefining the properties.

<!-- frontend/packages/identity-core/src/styles.css, frontend/packages/aurora-identity/components/IdentityUI/AuroraIdentityUI.css -->

## Where Aurora's add-on calls the backend from

Volto's browser reaches the backend through Volto's API proxy, which rewrites every request into a virtual-host URL naming the site's public address.
Aurora's add-on calls the backend from Aurora's server, in the loaders and actions of its routes, so it builds that URL itself.
The backend builds the callback URL it gives a provider from that address, so the provider sends the visitor back to Aurora, not to the backend.

<!-- frontend/packages/aurora-identity/lib/backend.ts -->

Starting a sign-in sets the backend's flow cookie, and finishing it reads that cookie back.
The add-on passes it to the browser on the way out and back to the backend on the way in, and sends nothing else of the browser's.

The callback path is `/login-identity` in both frontends.
It is the redirect URI registered with every provider, so a site moving from Volto to Aurora keeps its provider registrations.

<!-- frontend/packages/aurora-identity/lib/paths.ts -->

## Why Aurora's login page is replaced

Aurora's own login page draws a password form and offers a slot inside it for other add-ons.
This package's ways in are forms of their own, and HTML does not allow a form inside a form.
Aurora's registry can add a route but not replace one, so the add-on keeps Aurora's `/login` route and changes the file it renders.
The page keeps Aurora's frame: the close link, the logo and hero slots, and the heading.
Inside it is the core's login form, the same one the Volto add-on shows.

<!-- frontend/packages/aurora-identity/lib/routes.ts, frontend/packages/aurora-identity/routes/login.tsx -->

If a later Aurora release moves its login page, the add-on leaves Aurora's page in place and warns while the site is built.

## Settings

Both add-ons have the same two login settings, with the same defaults.
Each reads them where its frontend reads settings at run time.

| Setting | Default | Volto | Aurora |
|---|---|---|---|
| Offer Plone's password form | Off | `RAZZLE_IDENTITY_SHOW_PLONE_LOGIN` | `IDENTITY_SHOW_PLONE_LOGIN` |
| Start a sole provider at once | On | `RAZZLE_IDENTITY_REDIRECT_TO_SOLE_PROVIDER` | `IDENTITY_REDIRECT_TO_SOLE_PROVIDER` |

<!-- frontend/packages/volto-identity/src/helpers/showPloneLogin.ts, frontend/packages/volto-identity/src/helpers/redirectToSoleProvider.ts, frontend/packages/aurora-identity/lib/settings.ts -->

The environment variable wins over `config.settings.identity` in both.
A login page visited with `?choose` shows the options, whatever the second setting says.

## What Aurora does not have yet

The Aurora add-on covers signing in.
The identities page, the profile, the consent screen and the control panels exist in the Volto add-on only.
Neither the Aurora add-on nor the core is published to npm yet.

## Related

- {doc}`mental-model`
- {doc}`layers`
- {doc}`../contributing`

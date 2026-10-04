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
    For a signed-in user, the sign-in methods page, `/identities`, and its entry among the header's tools, the email confirmation page, the profile gate, the applications page, and the consent screen of an authorization server.

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
| The reader's language, for dates and plural forms | `react-intl`'s locale | i18next's language |

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

## Where Aurora's other pages go

A page registered at the top of Aurora's route tree renders without the site's header, and so without the user's tools that lead to it and back.
The add-on's other pages are added under `@plone/publicui`'s layout instead, beside its search page.
They are signed-in pages: a visitor without a session is sent to `/login`.

<!-- frontend/packages/aurora-identity/lib/routes.ts, frontend/packages/aurora-identity/routes/identities.tsx -->

## The profile gate

While a signed-in user's profile is missing required fields, both add-ons hold them until it is complete, then send them on to where they were going.
They decide it the same way, with the core's helpers, and hold the user differently:

| | Volto | Aurora |
|---|---|---|
| Sent to | The profile's edit form | `/complete-profile`, which names the missing fields and links to the edit form |
| Told why | A toast, as it redirects | On that page |
| The profile asked for | As an expansion of the content request Volto makes anyway | With a request of its own, on every page a signed-in user opens |

Aurora shows no toast that every page carries, and its edit form belongs to `@plone/cmsui`, where the add-on cannot say anything, so the page is what explains the hold.
Its content request expands a fixed list an add-on cannot add to, so the profile costs one more request.

The gate runs on every page that has the site's header, from the header's tools.
A user who completes the profile through the edit form is let go on the profile's own page, which the form saves to.

<!-- frontend/packages/aurora-identity/lib/gate.ts, frontend/packages/aurora-identity/slots/ProfileGate.tsx, frontend/packages/aurora-identity/config/server.ts, frontend/packages/volto-identity/src/components/ProfileGate/ProfileGate.tsx -->

## The applications page

The applications a user has authorized are listed by `@oauth-grants`, which only the `[server]` layer publishes.
Both add-ons offer the page only where that endpoint answers, and neither can tell from anything else: the core may not depend on that layer.
Volto asks once per session.
Aurora asks from its server, and keeps the answer for five minutes per backend, since whether a site runs the authorization server does not change from one page to the next.
`IDENTITY_FEATURE_TTL`, in seconds, sets how long; the acceptance tests set it to 0.

<!-- frontend/packages/aurora-identity/lib/features.ts, frontend/packages/volto-identity/src/components/UserMenu/ApplicationsMenuItem.tsx -->

## In front of an authorization server

A site running the `[server]` layer is an OpenID Connect provider, and its endpoints, `@@oauth-authorize` and its siblings, are browser views on the backend rather than REST services.
In front of Volto, a reverse proxy sends them to the backend by a rule written for them: {doc}`federation`.
Aurora serves them itself, by passing each request on to the backend, for two reasons:

- **The issuer is the site's public address**, which is Aurora's, so a relying party asks Aurora for the discovery document, the keys, the tokens and the user's claims.
  Passing them on works without the proxy rule.
- **The authorization endpoint has to know who the browser is.**
  The backend recognises the user there by a bearer token, or by Volto's `auth_token` cookie.
  Aurora keeps its session in a cookie of its own, which the backend cannot read, so Aurora sends the session's token as a bearer token, on that endpoint only.

A signed-out visitor reaching the authorization endpoint is sent to Plone's login challenge, which Aurora answers with its own login page, keeping the authorization request to come back to.
The consent screen is `/oauth-consent`, in both add-ons: set `server_consent_url` to it, at the site's address.

<!-- frontend/packages/aurora-identity/lib/oauth.ts, frontend/packages/aurora-identity/routes/oauth-consent.tsx, frontend/packages/aurora-identity/routes/require-login.ts -->

Every request Aurora passes on also goes through Aurora's own request handling first, which fetches the site root's content for it.

## What Aurora does not have yet

The Aurora add-on covers everything a user meets: signing in, the sign-in methods page, the email confirmation page, the profile gate, the applications page and the consent screen.
The control panels exist in the Volto add-on only.
Neither has the first-login route: Volto offers it to sites that route to it, and nothing in either add-on does.
Neither the Aurora add-on nor the core is published to npm yet.

## Related

- {doc}`mental-model`
- {doc}`layers`
- {doc}`../contributing`

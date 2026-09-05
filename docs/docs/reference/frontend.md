---
myst:
  html_meta:
    "description": "The routes, settings, and components the volto-identity add-on registers."
    "property=og:description": "The routes, settings, and components the volto-identity add-on registers."
    "property=og:title": "Frontend"
---

(reference-frontend)=

# Frontend

Everything `@plone-collective/volto-identity` adds to a Volto project.

<!-- source: frontend/packages/volto-identity/src/config/ -->

## The package

| | |
|---|---|
| Name | `@plone-collective/volto-identity` |
| Version | `1.0.0-alpha.0` |
| Published to npm | **no** |
| Developed against Volto | 19.3.0 |
| Peer dependencies | React 18, `react-redux` ^8.1.2, `react-router-dom` ^5.2.0, `@plone/components` |

`peerDependencies` does not name `@plone/volto` itself. The version above is what
the monorepo builds against (`frontend/mrs.developer.json`).

Install from the repository—see {doc}`/how-to-guides/install-the-frontend`.

```{note}
Every component in this package has a story. **[Browse them in Storybook](https://collective.github.io/pas-plugins-identity/storybook/)**
to see a widget or a view rendered, with its props, without running a site.
Storybook is built from this repository and published beside these pages.
```

## Routes

<!-- source: frontend/packages/volto-identity/src/config/routes.ts -->

| Path | Constant | Component | Layer |
|---|---|---|---|
| `/login`, `/**/login` |—| `Login` | core |
| `/login-identity` | `CALLBACK_PATH` | `Callback` | core |
| `/first-login` | `FIRST_LOGIN_PATH` | `FirstLogin` | core |
| `/fallback_login` | `FALLBACK_LOGIN_PATH` | Volto's own `Login` | core |
| `/identities` | `IDENTITIES_PATH` | `Identities` | core |
| `/controlpanel/identity-providers` | `CONTROLPANEL_PATH` | `ProvidersControlPanel` | core |
| `/controlpanel/users/:userid/account` | `USER_ACCOUNT_PATH` | `UserAccount` | core |
| `/oauth-consent` | `CONSENT_PATH` | `Consent` | server |
| `/applications` | `APPLICATIONS_PATH` | `Applications` | server |
| `/controlpanel/identity-clients` | `CLIENTS_CONTROLPANEL_PATH` | `ClientsControlPanel` | server |

`/login-identity` matches the `callback_url` registry default, which is what
makes the callback work with no configuration. See {doc}`settings`.

`/fallback_login` keeps Volto's own username-and-password form reachable whether
or not it is shown on `/login`.

## Environment variables

| Variable | Default | Read at |
|---|---|---|
| `RAZZLE_IDENTITY_SHOW_PLONE_LOGIN` | off | **run** time |

Read through Volto's `runtimeConfig`, not baked in at build time, so it can be
changed without rebuilding. `RAZZLE_` is the only prefix Volto carries through to
the browser.

## Settings

| Key | Default | What it does |
|---|---|---|
| `config.settings.identityShowPloneLogin` | `false` | Show Volto's username-and-password form on `/login` as well as the providers. |

The environment variable above sets this at run time.

## Views

| Registration | Content type |
|---|---|
| `config.views.contentTypesViews` | `UserProfile` |
| `config.views.contentTypesViews` | `UserGroup` |

Each is a title and a body, because neither type has rich text.

## Widgets

| Name | Used for |
|---|---|
| `provider_icon` | The SVG icon field on the provider form. |

The backend decides which widget a field uses, through
`directives.widget(..., frontendOptions={"widget": ...})`, and Volto looks the
name up here. The frontend composes what it is served rather than describing it.

## Shadowed components

Three Volto components are shadowed, because Volto has no extension point for
what each needs.

<!-- source: frontend/packages/volto-identity/src/customizations/ -->

| Shadowed | Why |
|---|---|
| `manage/Toolbar/Toolbar.jsx` | to reach the personal tools panel |
| `manage/Toolbar/PersonalTools.tsx` | to add the sign-in methods entry |
| `manage/Controlpanels/Users/RenderUsers.tsx` | to link a user row to their account page |

A shadowed file here is a docstring and a re-export; the component itself lives
under `components/`. That keeps the shadow small enough to re-check against a new
Volto release.

## Other registrations

Reducers, a menu entry, and `appExtras`.

## Related

- [Storybook](https://collective.github.io/pas-plugins-identity/storybook/)—every component, rendered
- {doc}`endpoints`—the REST services these routes call
- {doc}`stability`—what may change between alpha releases
- {doc}`/how-to-guides/install-the-frontend`—installing it

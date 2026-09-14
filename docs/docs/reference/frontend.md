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
| Developed against Volto | 19.3.0 |
| Peer dependencies | React 18, `react-redux` ^8.1.2, `react-router-dom` ^5.2.0, `@plone/components` |

`peerDependencies` does not name `@plone/volto` itself. The Volto version above
is what the monorepo builds against (`frontend/mrs.developer.json`).

Installing it is {doc}`/how-to-guides/install-the-frontend`.

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
| `/confirm-email` | `CONFIRM_EMAIL_PATH` | `ConfirmEmail` | core |
| `/fallback_login` | `FALLBACK_LOGIN_PATH` | Volto's own `Login` | core |
| `/identities` | `IDENTITIES_PATH` | `Identities` | core |
| `/controlpanel/identity-providers` | `CONTROLPANEL_PATH` | `ProvidersControlPanel` | core |
| `/controlpanel/identity-providers/settings` | `PROVIDERS_SETTINGS_PATH` | `ProvidersControlPanel` | core |
| `/controlpanel/identity-providers/add` | `PROVIDER_ADD_PATH` | `ProvidersControlPanel` | core |
| `/controlpanel/identity-providers/:providerId/edit` | `PROVIDER_EDIT_PATH` | `ProvidersControlPanel` | core |
| `/controlpanel/users/:userid/account` | `USER_ACCOUNT_PATH` | `UserAccount` | core |
| `/oauth-consent` | `CONSENT_PATH` | `Consent` | server |
| `/applications` | `APPLICATIONS_PATH` | `Applications` | server |
| `/controlpanel/identity-clients` | `CLIENTS_CONTROLPANEL_PATH` | `ClientsControlPanel` | server |

`/login-identity` matches the `callback_url` registry default, which is what
makes the callback work with no configuration. See {doc}`settings`.

`/fallback_login` keeps Volto's own username-and-password form reachable whether
or not it is shown on `/login`.

`/confirm-email` is where `ProfileGate` and `/first-login` send a user whose
profile is waiting only on an address confirmation, rather than to the edit form.
A profile that is also missing fields goes to the edit form first. See
{doc}`profiles-and-groups`.

## Environment variables

<!-- source: frontend/packages/volto-identity/src/helpers/showPloneLogin.ts -->
<!-- source: frontend/packages/volto-identity/src/helpers/redirectToSoleProvider.ts -->

| Variable | Overrides | Default | Read at |
|---|---|---|---|
| `RAZZLE_IDENTITY_SHOW_PLONE_LOGIN` | `showPloneLogin` | off | **run** time |
| `RAZZLE_IDENTITY_REDIRECT_TO_SOLE_PROVIDER` | `redirectToSoleProvider` | on | **run** time |

Both are read through Volto's `runtimeConfig`, not baked in at build time, so
they can be changed without rebuilding. `RAZZLE_` is the only prefix Volto
carries through to the browser.

## Settings

<!-- source: frontend/packages/volto-identity/src/config/settings.ts -->
<!-- source: frontend/packages/volto-identity/src/types/settings.ts -->
<!-- source: frontend/packages/volto-identity/src/helpers/avatar.ts -->

Every setting the add-on reads is under `config.settings.identity`, typed as
`IdentitySettings`.

| Key | Default | What it does |
|---|---|---|
| `showPloneLogin` | `false` | Show Volto's username-and-password form on `/login` as well as the providers. |
| `redirectToSoleProvider` | `true` | Start the sign-in straight away when the only way in on `/login` is one provider. See {ref}`reference-frontend-sole-provider`. |
| `avatarColors` | the shipped palette of ten colours | The colours a user's initials are drawn on when they have no portrait. |

Each environment variable above overrides its setting at run time.

A user's colour is picked from their userid, modulo the number of colours, so
a palette of a different length moves most users to another colour. An empty
list means the shipped palette.

The shipped palette was chosen for contrast against the white initials. A
palette you configure is **not checked**, so its contrast is yours to verify.

The add-on sets these defaults under anything already there. Change them in
your project's own configuration, which runs after the add-on's:

```js
config.settings.identity = {
  ...config.settings.identity,
  avatarColors: ['#0b3d91', '#7a1f5c', '#1e5631'],
};
```

`showPloneLogin` was `config.settings.identityShowPloneLogin` up to `1.0.0a6`.
That key is no longer read.

(reference-frontend-sole-provider)=

## The sole-provider redirect

<!-- source: frontend/packages/volto-identity/src/components/Login/Login.tsx -->
<!-- source: frontend/packages/volto-identity/src/components/Login/LoginForm.tsx -->
<!-- source: frontend/packages/volto-identity/src/components/Callback/Callback.tsx -->

When the only way in on `/login` is one provider—no magic link and no password
form—the page starts that provider's sign-in without showing its button. It
shows the button instead in these cases:

| Case | What it prevents |
|---|---|
| `redirectToSoleProvider` is off | Nothing: the site chose the button |
| The visitor arrived already signed in | A provider with a session of its own signing them straight back in as the same account, and back to `/login` |
| The query string carries `choose`, as in `/login?choose=1` | Nothing: the visitor asked for the options |

A start that fails shows its error over the button rather than starting again.

`/login-identity` links to `/login?choose=1` when it reports a failure, so a
sign-in the provider refused does not go straight back to that provider.

## Expansion on content requests

The add-on adds one entry to `config.settings.apiExpanders`.

| Entry | What it does |
|---|---|
| `{ match: '', GET_CONTENT: ['my-profile'] }` | Asks for the caller's profile state with every content request, so the profile gate needs no request of its own. |

Registered for every path, and sent for anonymous visitors too—an entry cannot
be marked authenticated-only.
The backend answers an anonymous caller with no component at all.
See {doc}`endpoints`.

## Blocks

<!-- source: frontend/packages/volto-identity/src/config/blocks.ts -->
<!-- source: frontend/packages/volto-identity/src/components/Blocks/SignIn/schema.ts -->
<!-- source: frontend/packages/volto-identity/src/components/Welcome/Welcome.tsx -->
<!-- source: @plone/volto src/components/manage/BlockChooser/BlockChooser.jsx -->

| Block | `@type` | Page block chooser | Grid block chooser |
|---|---|---|---|
| Sign-in | `identitySignIn` | No, `restricted: true` | Yes |

A grid's block chooser offers the blocks named in the grid's `allowedBlocks`
and does not read `restricted`. The add-on adds the block to that list, and to
the grid's own `blocksConfig` when the grid has one. A project offers it on the
page as well by lifting the restriction in its own configuration:

```js
config.blocks.blocksConfig.identitySignIn.restricted = false;
```

To a visitor who is not signed in, the block shows the login card `/login`
shows: the same heading, description strip and sign-in options. It sets no
page title, and it never goes straight to a sole provider. After signing in,
the visitor comes back to the page the block is on.

To somebody signed in, it shows a welcome message and a summary. The sidebar
switches each line off:

| Field | Default | Shows |
|---|---|---|
| `greeting` | `Hello {fullname}!`, translated | The welcome message, as plain text. `{username}` is the name the user signs in with, `{fullname}` their full name. |
| `showProfile` | on | A link to the user's Profile, when they have one |
| `showEmail` | on | Their preferred address, and whether it is verified |
| `showProvider` | on | The provider of the newest successful `authenticated` audit event |
| `showLastLogin` | on | When the `authenticated` event before that one happened |
| `previewAnonymous` | off | While editing only: the sign-in options instead of the welcome |

The summary reads `@user-account` about the signed-in user, which they may read
about themselves. The audit log records `authenticated` for a sign-in through a
provider or a magic link, and not for a password sign-in. After a password
sign-in, `showProvider` and `showLastLogin` describe the sign-ins before it.

The block renders in the browser only. The server renders it empty, so a cached
page never carries somebody's welcome.

## Views

| Registration | Content type |
|---|---|
| `config.views.contentTypesViews` | `UserProfile` |
| `config.views.contentTypesViews` | `UserGroup` |

Each is a title and a body, because neither type has rich text.

## Widgets

<!-- source: frontend/packages/volto-identity/src/config/widgets.ts -->

| Name | Used for |
|---|---|
| `provider_icon` | The SVG icon field on the provider form. Shows the driver's default icon until one is uploaded. |
| `identity_string_list` | An ordered list of strings, edited as a table. A Profile's email addresses use it. The dialog renders the widget of the list's value type. |
| `identity_object_list` | An ordered list of objects an item schema describes, edited as a table. The `columns` prop picks the fields shown; without it every field is a column. |
| `social_media_object_list` | `identity_object_list`, showing a link's network and title. Replaces `@plonegovbr/volto-social-media`'s widget on `social_links` when this add-on is listed after that one. |

The backend decides which widget a field uses, through
`directives.widget(..., frontendOptions={"widget": ...})`, and Volto looks the
name up here. The frontend composes what it is served rather than describing it.
Asking for a list widget is {doc}`/how-to-guides/edit-a-list-as-a-table`.

### The list widgets

<!-- source: frontend/packages/volto-identity/src/components/Widgets/OrderedListTable/OrderedListTable.tsx -->
<!-- source: frontend/packages/volto-identity/src/components/Widgets/OrderedStringListWidget/OrderedStringListWidget.tsx -->
<!-- source: frontend/packages/volto-identity/src/components/Widgets/OrderedObjectListWidget/OrderedObjectListWidget.tsx -->
<!-- source: frontend/packages/volto-identity/src/helpers/orderedList.ts -->

| Action | What it does |
|---|---|
| Drag a row by its handle | Moves the entry. Handles appear once Volto's drag library has loaded |
| {guilabel}`Edit` | Opens the entry in a dialog built from the item schema |
| {guilabel}`Delete` | Asks, then removes the entry |
| The button beside the label | Opens an empty dialog, seeded with the item schema's defaults |

Every action changes the field's value only. Nothing is stored until the form is
saved.

| Prop | Widget | Set by | What it does |
|---|---|---|---|
| `items` | `identity_string_list` | `plone.restapi`, from the field's `value_type` | The one field in the dialog, and the column header |
| `uniqueItems` | `identity_string_list` | `plone.restapi`, `true` for a `Tuple`, a `Set`, and a `List` of `Choice` | Refuses an entry already on the list |
| `schemaName` | `identity_object_list` | `widgetProps` | Names a registered `schema` utility that builds the item schema. Wins over `schema` |
| `schema` | `identity_object_list` | A form schema built in the frontend | The item schema, or a function returning it. Ignored when it has no `fieldsets` |
| `columns` | `identity_object_list` | `widgetProps` | The item schema's fields shown as columns, in order. Every field when absent; `id` and `title` for `social_media_object_list` |
| `isDisabled` | Both | Volto's form | Removes the handles and disables every action |

| Widget | Value |
|---|---|
| `identity_string_list` | A list of strings, in order |
| `identity_object_list` | A list of objects, in order. Any change gives an `@id` to each entry without one, as Volto's `object_list` does |

A cell shows a choice by its label, a list as its entries joined by commas, and
an object—such as a link picked in the object browser—by its `title`, or its
`@id` without one.

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

## Slots

<!-- source: frontend/packages/volto-identity/src/components/Views/BelowTitleSlot.tsx -->

Three slots reach a profile page and a group page.

| Slot | Renders | Rendered by |
|---|---|---|
| `aboveContent` | Above the view | Volto's own `View` |
| `belowTitle` | Under the heading, above the description | `BelowTitleSlot` |
| `belowContent` | Below the view | Volto's own `View` |

The two outer slots come with registering a view in
`config.views.contentTypesViews`. `belowTitle` is rendered by each view itself.
Registering into any of them is {doc}`/how-to-guides/extend-a-profile-page`.

## Other registrations

Reducers, a menu entry, and `appExtras`.

## Related

- [Storybook](https://collective.github.io/pas-plugins-identity/storybook/)—every component, rendered
- {doc}`endpoints`—the REST services these routes call
- {doc}`stability`—what may change between alpha releases
- {doc}`/how-to-guides/install-the-frontend`—installing it
- {doc}`/how-to-guides/edit-a-list-as-a-table`—asking for a list widget from a field

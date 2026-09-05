<div align="center">

<h1 align="center">Multi-provider external authentication for Plone</h1>
<h2 align="center">@plone-collective/volto-identity</h2>

</div>

<div align="center">

[![Storybook](https://img.shields.io/badge/-Storybook-ff4785?logo=Storybook&logoColor=white&style=flat-square)](https://collective.github.io/pas-plugins-identity/storybook/)
[![Documentation](https://img.shields.io/badge/docs-collective.github.io-0083be)](https://collective.github.io/pas-plugins-identity/)
[![CI](https://github.com/collective/pas-plugins-identity/actions/workflows/main.yml/badge.svg)](https://github.com/collective/pas-plugins-identity/actions/workflows/main.yml)

[![GitHub contributors](https://img.shields.io/github/contributors/collective/pas-plugins-identity)](https://github.com/collective/pas-plugins-identity)
[![GitHub Repo stars](https://img.shields.io/github/stars/collective/pas-plugins-identity?style=social)](https://github.com/collective/pas-plugins-identity)

</div>

The frontend package for multi-provider external authentication in Plone: signing in through an external provider, managing the identities linked to your account, and the pages a user and a group are.
See also the backend package [pas.plugins.identity](https://github.com/collective/pas-plugins-identity/tree/main/backend), which this package requires.

## Features

Everything here renders from what the backend serves. The add-on describes no schema of its own: a provider form is generated from the driver's published schema, and this package supplies components where Volto has none.

- **Sign-in screen** — the login page offers every provider the backend says to show, in the order it gives, with the provider's own icon and colours. Plone's username and password form is offered alongside, or not, depending on `RAZZLE_IDENTITY_SHOW_PLONE_LOGIN`.
- **Callback route** — `/login-identity` completes the flow the provider redirects back into, and routes onward by what the backend answered rather than by guessing.
- **Sign-in methods page** — `/identities` lists the providers linked to your account, links another, and unlinks one. The addresses on your Profile are managed here too, and verifying one is what enables a magic link to it.
- **Authorized applications** — `/applications` is the other direction: the applications you signed in *to*, rather than the providers you signed in *with*. Only a site running the backend's `[server]` layer has any.
- **Consent screen** — `/oauth-consent`, for a site whose authorization server asks the frontend to render the question rather than its own standalone page.
- **First-login gate** — a just-signed-in user whose Profile is incomplete is routed to `/first-login` before anywhere else, so a site can require what the provider did not supply.
- **Profile and group views** — `UserProfile` and `UserGroup` are content, and without this they render through Volto's default view: a title over an empty body, because neither type has rich text. Registered by portal type, so a site filing users under its own type keeps its own view.
- **Two control panels** — identity providers and OAuth clients, each with the configlet icon and label the backend registers, so they sit in the control-panel listing looking like the panels beside them rather than like two things that failed to install.
- **User account review** — an administrator's view of one account: its linked identities, its addresses, and its audit trail in one place.
- **User menu and toolbar** — personal information, preferences, sign-in methods and applications reachable from where a user already looks for them.
- **A `provider_icon` widget** — the one widget this add-on registers, because it is the one Volto does not have. *Which* widget a field uses is the backend's decision, declared on the field itself; Volto looks the name up and finds this one.

### Configuration

| Environment variable | Default | Effect |
| --- | --- | --- |
| `RAZZLE_IDENTITY_SHOW_PLONE_LOGIN` | off | Whether Plone's own username and password form appears alongside the providers. |

`1`, `true`, `yes` and `on` switch it on; anything else switches it off, and an unset variable means the default.
The check is deliberately not `Boolean(value)`, which reads the string `"false"` as true and would leave the password form up for an operator who had just switched it off.

The form is **off** by default: a site installing this add-on has external providers, and offering a password form beside them invites people to make a second way into the same account.
A site that is itself an identity provider is the case that wants it on, and sets `config.settings.identityShowPloneLogin` in its own configuration. The environment variable still wins over that.

> [!NOTE]
> This variable is read at run time, not baked into the bundle. That is why the Login component reads it through `runtimeConfig` rather than writing `process.env.RAZZLE_IDENTITY_SHOW_PLONE_LOGIN` literally: webpack substitutes the literal form while `pnpm build` runs, which would make the answer a property of the image and force two images on two sites wanting two answers.

### Shadowed components

Three of Volto's own components are shadowed, in each case because Volto offers nothing to extend at that point.

| Shadowed | Why Volto could not be extended instead |
| --- | --- |
| `Toolbar` | `toolbar-personal` is a DOM id on a button, not a pluggable, so the icon it draws cannot be replaced from outside. That icon is the generic `user.svg`, which says somebody is signed in rather than who. |
| `PersonalTools` | The only pluggable is `toolbar-user-menu`, at the end of the menu *list*. The avatar block above it cannot be touched, and the entries themselves cannot be reordered or removed at all. |
| `Controlpanels/Users/RenderUsers` | The row's Edit action is built inline with no extension point, and led to the wrong form on the wrong store for every user whose fields live in a Profile, which is most of them. |

None of those files holds an implementation.
Each is a docstring saying why the path is shadowed, plus a one-line re-export of a component under `components/`, which is where the code, its tests and its stories live.
A shadowed path is a wiring decision, not somewhere to keep code nothing can import by name.

## Documentation

Full documentation is published at [collective.github.io/pas-plugins-identity](https://collective.github.io/pas-plugins-identity/), and its source lives in [`docs/`](https://github.com/collective/pas-plugins-identity/tree/main/docs) at the repository root.

The pages closest to this package are [Configure a provider](https://github.com/collective/pas-plugins-identity/blob/main/docs/docs/how-to-guides/configure-a-provider.md), [Review a user account](https://github.com/collective/pas-plugins-identity/blob/main/docs/docs/how-to-guides/review-a-user-account.md), and the [federation tutorial](https://github.com/collective/pas-plugins-identity/blob/main/docs/docs/tutorials/federation-demo.md), which walks two Plone sites into trusting each other.

Every component this add-on ships is in [Storybook](https://collective.github.io/pas-plugins-identity/storybook/), which is the fastest way to see one without a running Plone site.

## Installation

This add-on supports Volto 18 and above, and requires `pas.plugins.identity` installed on the Plone site.

Add `@plone-collective/volto-identity` to your `package.json`.

```json
"addons": [
    "@plone-collective/volto-identity"
],
"dependencies": {
    "@plone-collective/volto-identity": "*"
}
```

> [!IMPORTANT]
> Adding the package to `dependencies` without listing it under `addons` installs the code but never registers it, so nothing is rendered.

## Test installation

Visit http://localhost:3000/ in a browser, login, and check the awesome new features.


## Development

The development of this add-on is done in isolation using pnpm workspaces, the latest `mrs-developer`, and other Volto core improvements.
For these reasons, it only works with pnpm and Volto 18.


### Prerequisites ✅

-   An [operating system](https://6.docs.plone.org/install/create-project-cookieplone.html#prerequisites-for-installation) that runs all the requirements mentioned.
-   [nvm](https://6.docs.plone.org/install/create-project-cookieplone.html#nvm)
-   [Node.js and pnpm](https://6.docs.plone.org/install/create-project.html#node-js) 24
-   [Make](https://6.docs.plone.org/install/create-project-cookieplone.html#make)
-   [Git](https://6.docs.plone.org/install/create-project-cookieplone.html#git)
-   [Docker](https://docs.docker.com/get-started/get-docker/) (optional)

### Installation 🔧

1.  Clone this repository, then change your working directory.

    ```shell
    git clone git@github.com:collective/pas-plugins-identity.git
    cd pas-plugins-identity/frontend
    ```

2.  Install this code base.

    ```shell
    make install
    ```


### Make convenience commands

Run `make help` to list the available Make commands.


### Set up development environment

Install package requirements.

```shell
make install
```

### Start developing

Start the backend.

```shell
make backend-docker-start
```

In a separate terminal session, start the frontend.

```shell
make start
```

### Lint code

Run ESlint, Prettier, and Stylelint in analyze mode.

```shell
make lint
```

### Format code

Run ESlint, Prettier, and Stylelint in fix mode.

```shell
make format
```

### i18n

Extract the i18n messages to locales.

```shell
make i18n
```

### Unit tests

Run unit tests.

```shell
make test
```

### Storybook

Start Storybook on [port 6006](http://localhost:6006/).

```shell
make storybook-start
```

Build the static site, as CI does before publishing it:

```shell
make storybook-build
```

#### Writing a story

Every component this add-on ships has stories, and a `.stories.tsx` beside a component is as expected here as a `.test.tsx`.
Stories use Component Story Format 3, and payloads come from `src/stories/fixtures.tsx`, which holds provider lists, identities and audit entries shaped exactly like the backend serves them.
Reuse those rather than inventing a payload, so a story that renders is evidence the component handles the real contract.

Two decorators in `src/storybook/` cover what these components need from their surroundings.

- `withPage` supplies the router and store a page-level component reads.
- `withUserMenu` puts a component in the chrome it actually appears in, which is the only way to see a menu entry rendered where a user meets it.

### Run Cypress tests

Run each of these steps in separate terminal sessions.

In the first session, start the frontend in development mode.

```shell
make acceptance-frontend-dev-start
```

In the second session, start the backend acceptance server.

```shell
make acceptance-backend-start
```

In the third session, start the Cypress interactive test runner.

```shell
make acceptance-test
```

## License

The project is licensed under the MIT license.

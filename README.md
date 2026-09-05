<div align="center">

<h1 align="center">Multi-provider external authentication for Plone</h1>

</div>

<div align="center">

[![Built with Cookieplone](https://img.shields.io/badge/built%20with-Cookieplone-0083be.svg?logo=cookiecutter)](https://github.com/plone/cookieplone-templates/)
[![Documentation](https://img.shields.io/badge/docs-collective.github.io-0083be)](https://collective.github.io/pas-plugins-identity/)
[![Storybook](https://img.shields.io/badge/-Storybook-ff4785?logo=Storybook&logoColor=white&style=flat-square)](https://collective.github.io/pas-plugins-identity/storybook/)

[![GitHub contributors](https://img.shields.io/github/contributors/collective/pas-plugins-identity)](https://github.com/collective/pas-plugins-identity)
[![GitHub Repo stars](https://img.shields.io/github/stars/collective/pas-plugins-identity?style=social)](https://github.com/collective/pas-plugins-identity)

[![CI](https://github.com/collective/pas-plugins-identity/actions/workflows/main.yml/badge.svg)](https://github.com/collective/pas-plugins-identity/actions/workflows/main.yml)

</div>

Multi-provider external authentication for Plone, built on [authlib](https://authlib.org/).

One canonical Plone user id maps to many external identities — GitHub, Google, ORCID, a generic OIDC provider, an emailed magic link — for the same human, without running a separate identity broker.

📖 **[Read the documentation](https://collective.github.io/pas-plugins-identity/)**

## What it does 📋

- **Identity linking.** One account, many providers. The identity key is `(provider, subject)`, and an identity already linked to somebody is never silently re-attached: a collision is a hard error, not a merge.
- **Providers configured through the web.** A control panel with a form generated from each driver's published schema. Client secrets are write-only through every API surface, including GenericSetup export.
- **Magic-link sign-in.** Single-use signed tokens, at most fifteen minutes, rate limited per address *and* per IP, answering identically for known and unknown addresses.
- **An audit log.** Successes and refusals, per user or site-wide, bounded and purged on write. IP and user agent are off by default.
- **A documented event contract**, which is what the audit log, the profile machinery and your own integrations all consume. Nothing reaches into anything else.
- **Content-backed profiles and groups**, with user properties, enumeration and group membership served entirely from a dedicated catalog — no content object is woken to answer them, and the test suite asserts that rather than claiming it.
- **An authorization server, optionally.** The `[server]` extra makes the site an OAuth 2.1 and OpenID Connect provider in its own right, so one Plone site can be where the others sign in.
- **Core installs alone.** `uv add pas.plugins.identity` with no extras is a tested configuration, enforced in CI by an import-linter contract.

### Relationship to pas.plugins.oidc and pas.plugins.authomatic

[`pas.plugins.authomatic`](https://github.com/collective/pas.plugins.authomatic) is the long-standing multi-provider option, built on the `authomatic` library, which is no longer maintained upstream. This package is a candidate successor for those sites.

[`pas.plugins.oidc`](https://github.com/collective/pas.plugins.oidc) does one OIDC provider, and does it well. If that is what you need, it is the smaller and more mature dependency; there is no reason to move.

The difference is linking. Neither of the above maps several external identities onto one canonical Plone user id, and that mapping is what this package is arranged around. Migrations from both have shipped: they are dry-run by default, idempotent, and report what they would do before you let them do it. See [Migrating from `pas.plugins.authomatic`](docs/docs/how-to-guides/migrate-from-authomatic.md) and [Migrating from `pas.plugins.oidc`](docs/docs/how-to-guides/migrate-from-oidc.md) for what each can and cannot recover.

For how this compares with `Products.membrane` — a similar problem solved a different way — see [About users as content](docs/docs/concepts/users-as-content.md).

## Documentation 📚

Full documentation lives in [`docs/`](./docs) and is published at [collective.github.io/pas-plugins-identity](https://collective.github.io/pas-plugins-identity/).

- **Start here:** [Install](./docs/docs/how-to-guides/install.md), then [Configure a provider](./docs/docs/how-to-guides/configure-a-provider.md).
- **Tutorial:** [Two Plone sites, one login](./docs/docs/tutorials/federation-demo.md) — build a federation end to end.
- **How-to guides:** [write a driver](./docs/docs/how-to-guides/write-a-driver.md), [register an OAuth client](./docs/docs/how-to-guides/register-an-oauth-client.md), [read the audit log](./docs/docs/how-to-guides/read-the-audit-log.md), [export and import principals](./docs/docs/how-to-guides/export-and-import-principals.md).
- **Concepts:** [identities](./docs/docs/concepts/identities.md), [the two layers](./docs/docs/concepts/layers.md), [users as content](./docs/docs/concepts/users-as-content.md), [secrets](./docs/docs/concepts/secrets.md), [federation](./docs/docs/concepts/federation.md).
- **Reference:** [shipped drivers](./docs/docs/reference/shipped-drivers.md), [events](./docs/docs/reference/events.md), [claims](./docs/docs/reference/claims.md), [security guarantees](./docs/docs/reference/security-guarantees.md).

## Install in your project 🔧

Both packages are installed separately. The backend one is enough on its own; the frontend one requires it.

### Backend

Requires Plone 6.2 and Python 3.12 or later.

```shell
uv add pas.plugins.identity
```

For the authorization server as well:

```shell
uv add "pas.plugins.identity[server]"
```

Then install **pas.plugins.identity** from the add-ons control panel, and configure a provider in **Site Setup > Identity providers**.

### Frontend

Requires Volto 18 and above.

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

## Quick Start 🏁

### Prerequisites ✅

-   An [operating system](https://6.docs.plone.org/install/create-project-cookieplone.html#prerequisites-for-installation) that runs all the requirements mentioned.
-   [uv](https://6.docs.plone.org/install/create-project-cookieplone.html#uv)
-   [nvm](https://6.docs.plone.org/install/create-project-cookieplone.html#nvm)
-   [Node.js and pnpm](https://6.docs.plone.org/install/create-project.html#node-js) 24
-   [Make](https://6.docs.plone.org/install/create-project-cookieplone.html#make)
-   [Git](https://6.docs.plone.org/install/create-project-cookieplone.html#git)
-   [Docker](https://docs.docker.com/get-started/get-docker/) (optional)


### Installation 🔧

1.  Clone this repository, then change your working directory.

    ```shell
    git clone git@github.com:collective/pas-plugins-identity.git
    cd pas-plugins-identity
    ```

2.  Install this code base.

    ```shell
    make install
    ```


### Fire Up the Servers 🔥

1.  Create a new Plone site on your first run.

    ```shell
    make backend-create-site
    ```

2.  Start the backend at http://localhost:8080/.

    ```shell
    make backend-start
    ```

3.  In a new shell session, start the frontend at http://localhost:3000/.

    ```shell
    make frontend-start
    ```

Voila! Your Plone site should be live and kicking! 🎉

### Local Stack Deployment 📦

Deploy a local Docker Compose environment that includes the following.

- Docker images for Backend and Frontend 🖼️
- A stack with a Traefik router and a PostgreSQL database 🗃️
- Accessible at [http://pas-plugins-identity.localhost](http://pas-plugins-identity.localhost) 🌐

Run the following commands in a shell session.

```shell
make stack-create-site
make stack-start
```

And... you're all set! Your Plone site is up and running locally! 🚀

### The federation demo 🤝

A second stack runs two Plone sites and signs one into the other, which is the fastest way to see what this package is for.

```shell
make demo-stack-start
```

Read [the tutorial](./docs/docs/tutorials/federation-demo.md) for what to click once it is up.

## Project structure 🏗️

This monorepo consists of the following distinct sections:

- **backend**: The Plone add-on `pas.plugins.identity`, installed with uv, plus its test suite and the demo stack's own package.
- **frontend**: The Volto add-on `@plone-collective/volto-identity`, plus its Storybook stories.
- **docs**: The Sphinx and MyST documentation published at [collective.github.io/pas-plugins-identity](https://collective.github.io/pas-plugins-identity/).

### Why this structure? 🤔

- Both halves of the add-on live together, so a change to a REST API payload and the change to the component that reads it are one commit.
- GitHub Workflows are triggered per section, so a documentation change does not rebuild the frontend (refer to .github/workflows).
- The documentation is built from the same checkout as the code it describes, so a reference page and the source it documents cannot drift between repositories.

## Code quality assurance 🧐

To check your code against quality standards, run the following shell command.

```shell
make check
```

### Format the codebase

To format and rewrite the code base, ensuring it adheres to quality standards, run the following shell command.

```shell
make format
```

| Section | Tool | Description | Configuration |
| --- | --- | --- | --- |
| backend | Ruff | Python code formatting, imports sorting  | [`backend/pyproject.toml`](./backend/pyproject.toml) |
| backend | `zpretty` | XML and ZCML formatting  | -- |
| frontend | ESLint | Fixes most common frontend issues | [`frontend/.eslintrc.js`](./frontend/.eslintrc.js) |
| frontend | prettier | Format JS and Typescript code  | [`frontend/.prettierrc`](./frontend/.prettierrc) |
| frontend | Stylelint | Format Styles (css, less, sass)  | [`frontend/.stylelintrc`](./frontend/.stylelintrc) |

Formatters can also be run within the `backend` or `frontend` folders.

### Linting the codebase
or `lint`:

 ```shell
make lint
```

| Section | Tool | Description | Configuration |
| --- | --- | --- | --- |
| backend | Ruff | Checks code formatting, imports sorting  | [`backend/pyproject.toml`](./backend/pyproject.toml) |
| backend | Pyroma | Checks Python package metadata  | -- |
| backend | check-python-versions | Checks Python version information  | -- |
| backend | `zpretty` | Checks XML and ZCML formatting  | -- |
| frontend | ESLint | Checks JS / Typescript lint | [`frontend/.eslintrc.js`](./frontend/.eslintrc.js) |
| frontend | prettier | Check JS / Typescript formatting  | [`frontend/.prettierrc`](./frontend/.prettierrc) |
| frontend | Stylelint | Check Styles (css, less, sass) formatting  | [`frontend/.stylelintrc`](./frontend/.stylelintrc) |

Linters can be run individually within the `backend` or `frontend` folders.

The backend also enforces its own layering. `make check-imports`, from `backend/`, runs [import-linter](https://import-linter.readthedocs.io/) contracts asserting that core never imports the optional server layer, so the no-extras install stays a tested configuration rather than a claim.

## Internationalization 🌐

Generate translation files for Plone and Volto with ease:

```shell
make i18n
```

## Packages 📦

This repository holds two packages, released separately and each under its own license.

| Package | Location | Registry | License |
| ------- | -------- | -------- | ------- |
| `pas.plugins.identity` | [backend/](./backend/) | PyPI | GPL-2.0-only |
| `@plone-collective/volto-identity` | [frontend/](./frontend/) | npm | MIT |

The backend package is usable on its own: it needs no frontend to authenticate a user against an external provider, link an identity, or serve any of it over the REST API. The frontend package requires the backend, because everything it renders comes from what the backend serves.

## Credits and acknowledgements 🙏

Generated using [Cookieplone (2.0.0b3)](https://github.com/plone/cookieplone) and [cookieplone-templates (91c8455)](https://github.com/plone/cookieplone-templates/commit/91c845557fce11a401a959f763add9d1384b135f) on 2026-08-20 18:32:15.036687. A special thanks to all contributors and supporters!

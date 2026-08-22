# pas.plugins.identity 🚀

[![Built with Cookieplone](https://img.shields.io/badge/built%20with-Cookieplone-0083be.svg?logo=cookiecutter)](https://github.com/plone/cookieplone-templates/)
[![Black code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![CI](https://github.com/collective/pas-plugins-identity/actions/workflows/main.yml/badge.svg)](https://github.com/collective/pas-plugins-identity/actions/workflows/main.yml)

Multi-provider external authentication for Plone, built on [authlib](https://authlib.org/).

One canonical Plone user id maps to many external identities — GitHub, Google, ORCID, a generic OIDC provider, an emailed magic link — for the same human, without running a separate identity broker.

📖 **[Read the documentation](./docs/index.md)**

## Features

- **Identity linking.** One account, many providers. The identity key is `(provider, subject)`, and an identity already linked to somebody is never silently re-attached: a collision is a hard error, not a merge.
- **Providers configured through the web.** A control panel with a form generated from each driver's published schema. Client secrets are write-only through every API surface, including GenericSetup export.
- **Magic-link sign-in.** Single-use signed tokens, at most fifteen minutes, rate limited per address *and* per IP, answering identically for known and unknown addresses.
- **An audit log.** Successes and refusals, per user or site-wide, bounded and purged on write. IP and user agent are off by default.
- **A documented event contract**, which is what the audit log, the profile layer and your own integrations all consume. Nothing reaches into anything else.
- **Optional content-backed profiles and groups** (`[profile]`), with user properties, enumeration and group membership served entirely from a dedicated catalog — no content object is woken to answer them, and the test suite asserts that rather than claiming it.
- **Core installs alone.** `pip install pas.plugins.identity` with no extras is a tested configuration, enforced in CI by an import-linter contract.

## Relationship to pas.plugins.oidc and pas.plugins.authomatic

[`pas.plugins.authomatic`](https://github.com/collective/pas.plugins.authomatic) is the long-standing multi-provider option, built on the `authomatic` library, which is no longer maintained upstream. This package is a candidate successor for those sites.

[`pas.plugins.oidc`](https://github.com/collective/pas.plugins.oidc) does one OIDC provider, and does it well. If that is what you need, it is the smaller and more mature dependency; there is no reason to move.

The difference is linking. Neither of the above maps several external identities onto one canonical Plone user id, and that mapping is what this package is arranged around. Migrations from both have shipped: they are dry-run by default, idempotent, and report what they would do before you let them do it. See [Migrating from another package](docs/migration.md) for what each can and cannot recover.

## Why not Products.membrane / dexterity.membrane

`Products.membrane` solves a similar problem — users as content — and has been doing so far longer than this package has existed.

Its published compatibility matrix lists Plone 6.0 and 6.1, not 6.2. That is a fact about the current release rather than a judgement, and it may well change.

The other reason is narrower: serving user properties and enumeration without waking a content object is the property the `[profile]` layer exists to provide, so it has to be something this package can assert about its own code on every CI run. It does, with a test that counts ZODB object activations and requires zero.

Membrane does wake them, and it is worth being precise about where. Its `MembranePropertyManager.getPropertiesForUser` collects property providers through `findMembraneUserAspect`, which adapts `brain._unrestrictedGetObject()` — so answering a property lookup loads the content object, one per matching brain. The plugin inherits `OFS.Cache.Cacheable`, but that path never calls it, so there is no cache in front of the load. Its *user enumeration* is not affected: that goes through `findImplementations`, which stays on the brains.

This is architecture, not oversight. Membrane's property values live on the content object and are read through an adapter on it, so a brain genuinely cannot answer; the `[profile]` layer copies the values it serves into catalog metadata instead, which is what lets a brain answer and what the zero-wake test measures. The trade is real in both directions — metadata has to be kept honest, and this package ships a consistency check and a rebuild step precisely because of that.

Verified against `Products.membrane` 7.0.1.dev0 (`plugins/propertymanager.py`, `utils.py`) by reading the source, not by measurement — membrane is not a dependency here, and its compatibility matrix would make it awkward to install alongside. Membrane's *design* is nonetheless where this one comes from, and the resemblance is not accidental.


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

## Project structure 🏗️

This monorepo consists of the following distinct sections:

- **backend**: Houses the API and Plone installation, utilizing pip instead of buildout, and includes a policy package named pas.plugins.identity.
- **frontend**: Contains the React (Volto) package.
- **devops**: Encompasses Docker stack, Ansible playbooks, and cache settings.
- **docs**: Sphinx + MyST documentation, built in CI.

### Why this structure? 🤔

- All necessary codebases to run the site are contained within the repository (excluding existing add-ons for Plone and React).
- Specific GitHub Workflows are triggered based on changes in each codebase (refer to .github/workflows).
- Simplifies the creation of Docker images for each codebase.
- Demonstrates Plone installation/setup without buildout.

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
| frontend | ESLint | Fixes most common frontend issues | [`frontend/.eslintrc.js`](.frontend/.eslintrc.js) |
| frontend | prettier | Format JS and Typescript code  | [`frontend/.prettierrc`](.frontend/.prettierrc) |
| frontend | Stylelint | Format Styles (css, less, sass)  | [`frontend/.stylelintrc`](.frontend/.stylelintrc) |

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
| frontend | ESLint | Checks JS / Typescript lint | [`frontend/.eslintrc.js`](.frontend/.eslintrc.js) |
| frontend | prettier | Check JS / Typescript formatting  | [`frontend/.prettierrc`](.frontend/.prettierrc) |
| frontend | Stylelint | Check Styles (css, less, sass) formatting  | [`frontend/.stylelintrc`](.frontend/.stylelintrc) |

Linters can be run individually within the `backend` or `frontend` folders.

## Internationalization 🌐

Generate translation files for Plone and Volto with ease:

```shell
make i18n
```

## Credits and acknowledgements 🙏

Generated using [Cookieplone (2.0.0b3)](https://github.com/plone/cookieplone) and [cookieplone-templates (91c8455)](https://github.com/plone/cookieplone-templates/commit/91c845557fce11a401a959f763add9d1384b135f) on 2026-08-20 18:32:15.036687. A special thanks to all contributors and supporters!

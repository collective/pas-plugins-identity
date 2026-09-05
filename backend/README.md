<div align="center">

<h1 align="center">Multi-provider external authentication for Plone</h1>
<h2 align="center">pas.plugins.identity</h2>

</div>

<div align="center">

[![Documentation](https://img.shields.io/badge/docs-collective.github.io-0083be)](https://collective.github.io/pas-plugins-identity/)
[![CI](https://github.com/collective/pas-plugins-identity/actions/workflows/main.yml/badge.svg)](https://github.com/collective/pas-plugins-identity/actions/workflows/main.yml)

[![GitHub contributors](https://img.shields.io/github/contributors/collective/pas-plugins-identity)](https://github.com/collective/pas-plugins-identity)
[![GitHub Repo stars](https://img.shields.io/github/stars/collective/pas-plugins-identity?style=social)](https://github.com/collective/pas-plugins-identity)

</div>

The backend package for multi-provider external authentication in Plone, built on [authlib](https://authlib.org/).
See also the frontend package [@plone-collective/volto-identity](https://github.com/collective/pas-plugins-identity/tree/main/frontend).

One canonical Plone user id maps to many external identities — GitHub, Google, ORCID, a generic OIDC provider, an emailed magic link — for the same human, without running a separate identity broker.

## Features

- **Identity linking.** One account, many providers. The identity key is `(provider, subject)`, and an identity already linked to somebody is never silently re-attached: a collision is a hard error, not a merge.
- **Providers configured through the web.** A control panel with a form generated from each driver's published schema, so a driver describes its own settings and the frontend composes rather than describes them. Client secrets are write-only through every API surface, GenericSetup export included.
- **Five shipped drivers.** `github`, `google`, `oidc-generic`, `plone-identity` (another Plone site running this package's server layer), and `email` for magic-link sign-in. Writing another means subclassing `BaseDriver` and registering a utility.
- **Magic-link sign-in.** Single-use signed tokens, at most fifteen minutes, rate limited per address *and* per IP, answering identically for known and unknown addresses.
- **An audit log.** Successes and refusals, per user or site-wide, bounded and purged on write. IP address and user agent are off by default, and the sink is a utility a deployment can replace.
- **A documented event contract**, which is what the audit log, the profile machinery and your own integrations all consume. Nothing reaches into anything else.
- **Content-backed profiles and groups**, with user properties, enumeration and group membership served entirely from a dedicated catalog. No content object is woken to answer them, and the test suite asserts that rather than claiming it.
- **Federated group membership.** Each provider's grants are recorded separately, so signing in through one never revokes what another gave you, and local grants survive both.
- **Migrations from `pas.plugins.authomatic` and `pas.plugins.oidc`.** Dry-run by default, idempotent, and they report what they would do before you let them do it.
- **Core installs alone.** `uv add pas.plugins.identity` with no extras is a tested configuration, enforced in CI by an import-linter contract rather than by discipline.

### The two layers

The package ships as a core plus one optional extra, each switched on by its own GenericSetup profile.

| Profile | What it adds |
| --- | --- |
| `pas.plugins.identity:default` | Sign in with external providers, identity linking, the audit log, the control panel, and the content types users and groups are. |
| `pas.plugins.identity.server:default` | An OAuth 2.1 and OpenID Connect authorization server, so the site can *be* a provider for others. |

Core never imports from the server layer, and CI fails the build if it starts to.
Read [the layers page](https://github.com/collective/pas-plugins-identity/blob/main/docs/docs/concepts/layers.md) for why the boundary is more than tidiness.

### Not in scope

- **Being an identity broker.** Providers are configured on the site and mapped onto its own users; this package does not proxy one provider to another.
- **Merging two existing accounts.** A colliding identity is refused rather than reconciled, because a merge that guesses is worse than a refusal that explains.
- **Storing credentials in a Dexterity field.** Passwords stay in `source_users`, or in an annotation for a site that opts into `ICredentialStorage`. A field would be serialized, exported, indexed and versioned: four disclosure paths, each of which has to be remembered separately.
- **SAML.** Nothing here precludes a driver for it; none ships.

## Documentation

Full documentation is published at [collective.github.io/pas-plugins-identity](https://collective.github.io/pas-plugins-identity/), and its source lives in [`docs/`](https://github.com/collective/pas-plugins-identity/tree/main/docs) at the repository root.

The pages closest to this package:

- **Start here:** [Install](https://github.com/collective/pas-plugins-identity/blob/main/docs/docs/how-to-guides/install.md) and [Configure a provider](https://github.com/collective/pas-plugins-identity/blob/main/docs/docs/how-to-guides/configure-a-provider.md).
- **Concepts:** [identities](https://github.com/collective/pas-plugins-identity/blob/main/docs/docs/concepts/identities.md), [the two layers](https://github.com/collective/pas-plugins-identity/blob/main/docs/docs/concepts/layers.md), [users as content](https://github.com/collective/pas-plugins-identity/blob/main/docs/docs/concepts/users-as-content.md), [secrets](https://github.com/collective/pas-plugins-identity/blob/main/docs/docs/concepts/secrets.md).
- **Reference:** [shipped drivers](https://github.com/collective/pas-plugins-identity/blob/main/docs/docs/reference/shipped-drivers.md), [the event contract](https://github.com/collective/pas-plugins-identity/blob/main/docs/docs/reference/events.md), [the audit log](https://github.com/collective/pas-plugins-identity/blob/main/docs/docs/reference/audit-log.md), [security guarantees](https://github.com/collective/pas-plugins-identity/blob/main/docs/docs/reference/security-guarantees.md).
- **Writing a driver:** [Write a driver](https://github.com/collective/pas-plugins-identity/blob/main/docs/docs/how-to-guides/write-a-driver.md).

## Installation

Requires Plone 6.2 and Python 3.12 or later.

Install pas.plugins.identity with uv.

```shell
uv add pas.plugins.identity
```

For the authorization server as well:

```shell
uv add "pas.plugins.identity[server]"
```

Create the Plone site.

```shell
make create-site
```

Then install **pas.plugins.identity** from the add-ons control panel, and configure a provider in **Site Setup > Identity providers**.

## Contribute

- [Issue tracker](https://github.com/collective/pas-plugins-identity/issues)
- [Source code](https://github.com/collective/pas-plugins-identity/)

### Prerequisites ✅

-   An [operating system](https://6.docs.plone.org/install/create-project-cookieplone.html#prerequisites-for-installation) that runs all the requirements mentioned.
-   [uv](https://6.docs.plone.org/install/create-project-cookieplone.html#uv)
-   [Make](https://6.docs.plone.org/install/create-project-cookieplone.html#make)
-   [Git](https://6.docs.plone.org/install/create-project-cookieplone.html#git)
-   [Docker](https://docs.docker.com/get-started/get-docker/) (optional)

### Installation 🔧

1.  Clone this repository.

    ```shell
    git clone git@github.com:collective/pas-plugins-identity.git
    cd pas-plugins-identity/backend
    ```

2.  Install this code base.

    ```shell
    make install
    ```

### Tests

```shell
make test
```

Part of the suite drives a real OpenID Connect provider in a container and is marked `docker`.
To run everything else:

```shell
uv run pytest -m "not docker"
```

### Add features using `plonecli` or `bobtemplates.plone`

This package provides markers as strings (`<!-- extra stuff goes here -->`) that are compatible with [`plonecli`](https://github.com/plone/plonecli) and [`bobtemplates.plone`](https://github.com/plone/bobtemplates.plone).
These markers act as hooks to add all kinds of features through subtemplates, including behaviors, control panels, upgrade steps, or other subtemplates from `bobtemplates.plone`.
`plonecli` is a command line client for `bobtemplates.plone`, adding autocompletion and other features.

To add a feature as a subtemplate to your package, use the following command pattern.

```shell
make add <template_name>
```

For example, you can add a content type to your package with the following command.

```shell
make add content_type
```

You can add a behavior with the following command.

```shell
make add behavior
```

See also:

- The list of available subtemplates in the [`bobtemplates.plone` `README.md` file](https://github.com/plone/bobtemplates.plone/?tab=readme-ov-file#provided-subtemplates).
- The documentation of [Mockup and Patternslib](https://6.docs.plone.org/classic-ui/mockup.html) for how to build the UI toolkit for Classic UI.

## License

The project is licensed under GPLv2.

## Credits and acknowledgements 🙏

Generated using [Cookieplone (2.0.0b3)](https://github.com/plone/cookieplone) and [cookieplone-templates (91c8455)](https://github.com/plone/cookieplone-templates/commit/91c845557fce11a401a959f763add9d1384b135f) on 2026-08-20 18:32:15.036687. A special thanks to all contributors and supporters!

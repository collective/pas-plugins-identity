---
myst:
  html_meta:
    "description": "How to set up a development checkout of pas.plugins.identity, and what a change has to satisfy before it lands."
    "property=og:description": "How to set up a development checkout of pas.plugins.identity, and what a change has to satisfy before it lands."
    "property=og:title": "Contributing"
    "keywords": "Plone, pas.plugins.identity, contributing, development, tests"
---

(contributing)=

# Contributing

Everything in this page is run from a checkout. If you only want to *use* the
package, {doc}`how-to-guides/install` is the page you want instead.

If you are a coding agent, read
[`AGENTS.md`](https://github.com/collective/pas-plugins-identity/blob/main/AGENTS.md)
in the repository root. It covers the same ground more tersely, and adds the
traps that are only discoverable by hitting them.

## The repository holds both halves

<!-- source: README.md -->

| Directory | Holds |
|---|---|
| `backend/` | The Plone add-on `pas.plugins.identity`, its test suite, and the demo stack's own package. |
| `frontend/` | The Volto add-on `@plone-collective/volto-identity`, and its Storybook stories. |
| `docs/` | These pages, and the screenshot harness that illustrates them. |

They are one repository on purpose. A change to a REST API payload and the
change to the component that reads it are one commit, and a reference page
cannot drift from the source it documents because both are in the same
checkout.

The two packages are released separately, under different licences:
`pas.plugins.identity` is GPL-2.0-only on PyPI, `@plone-collective/volto-identity`
is MIT on npm.

## Set up a checkout

### What you need

- An operating system meeting [Plone's prerequisites](https://6.docs.plone.org/install/create-project-cookieplone.html#prerequisites-for-installation)
- [uv](https://6.docs.plone.org/install/create-project-cookieplone.html#uv)
- [nvm](https://6.docs.plone.org/install/create-project-cookieplone.html#nvm), and Node.js 24
- [Make](https://6.docs.plone.org/install/create-project-cookieplone.html#make)
- [Git](https://6.docs.plone.org/install/create-project-cookieplone.html#git)
- [Docker](https://docs.docker.com/get-started/get-docker/), for the stacks and for `pytest -m docker`

### Install

```shell
git clone git@github.com:collective/pas-plugins-identity.git
cd pas-plugins-identity
make install
```

That installs both halves. `make backend-install` and `make frontend-install`
do one each.

### Run it

```shell
make backend-create-site   # first run only
make backend-start         # http://localhost:8080/
```

Then, in a second shell:

```shell
make frontend-start        # http://localhost:3000/
```

To see the whole package working at once instead, run the two-site federation
in Docker: {doc}`tutorials/federation-demo`.

## What a change has to satisfy

Run these before opening a pull request. CI runs the same ones.

| Command | Checks |
|---|---|
| `make check` | `make format` then `make lint`, across both halves |
| `make test` | `make backend-test` and `make frontend-test` |
| `make check-imports`, from `backend/` | That core never imports the `[server]` layer |
| `make docs-build` | The documentation, with warnings as errors |
| `make -C docs vale` | Prose style. **Errors must be zero**; warnings are advisory |

### Formatting and linting

| Half | Tool | Does | Configured in |
|---|---|---|---|
| backend | Ruff | Formats Python, sorts imports | `backend/pyproject.toml` |
| backend | `zpretty` | Formats XML and ZCML | — |
| backend | Pyroma | Checks package metadata | — |
| backend | check-python-versions | Checks the declared Python versions | — |
| frontend | ESLint | Lints JavaScript and TypeScript | `frontend/.eslintrc.js` |
| frontend | prettier | Formats JavaScript and TypeScript | `frontend/.prettierrc` |
| frontend | Stylelint | Formats CSS, Less and Sass | `frontend/.stylelintrc` |

Each runs from `backend/` or `frontend/` on its own as well.

```{important}
Run `make format` **before** staging. A formatter that rewrites a file after
you have staged it leaves the staged and working copies disagreeing, and the
commit carries whichever half you were not looking at.
```

### The layer boundary is a contract

`make check-imports` runs [import-linter](https://import-linter.readthedocs.io/)
contracts asserting that core never imports the optional server layer. It is
not part of `make lint`, so run it yourself when you touch either layer.

A soft import counts: import-linter reads function bodies, so moving an import
inside a function does not get past it. That is deliberate—see
{doc}`concepts/layers`.

## Conventions

### Changelog

Every change carries a [towncrier](https://towncrier.readthedocs.io/) news
fragment. There are three scopes, and a change adds one to each it touches:

| Scope | Folder |
|---|---|
| Repository and documentation | `news/` |
| Backend | `backend/news/` |
| Frontend | `frontend/packages/volto-identity/news/` |

Name it `<issue>.<type>` when an issue exists, `+<slug>.<type>` when none does.
The types are `breaking`, `feature`, `bugfix`, `documentation`, `internal` and
`tests`. Write it in the past tense, for somebody reading the changelog rather
than the diff, and end with your GitHub handle.

### Tests

A bugfix carries a test that fails without it. Verify that by removing the fix
and watching the test go red—a regression test nobody has seen fail is a
regression test that may be asserting nothing.

The backend suite uses `pytest-plone`. Tests needing Docker are marked
`docker` and skipped without it.

### Documentation

`docs/STYLE.md` is the house style, and it is short. The parts that catch
people out:

- **The code is the source of truth.** Cite the file a fact came from in an
  HTML comment under the heading it supports.
- **No "should" language.** Either it does, or you have not run it—and then
  say that.
- Reference pages are tables. Rationale belongs in `concepts/`.
- Diagrams are Mermaid, never images. Screenshots are captured by the harness
  in `docs/screenshots/`, never by hand.
- Every page ends with **Related** or **Next steps**.

## Translations

```shell
make i18n
```

Generates the translation files for both halves.

## Reporting a security vulnerability

Not through the issue tracker. Follow
[SECURITY.md](https://github.com/collective/pas-plugins-identity/blob/main/SECURITY.md).

## Related

- {doc}`concepts/layers`—the boundary `make check-imports` enforces
- {doc}`reference/stability`—what may change before 1.0.0
- {doc}`how-to-guides/write-a-driver`—the most common thing to contribute
- {doc}`reference/driver-contract`—what a driver must implement

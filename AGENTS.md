# AGENTS.md

Instructions for coding agents working in this repository. Humans want
[`docs/docs/contributing.md`](docs/docs/contributing.md), which covers the same
ground in prose.

## What this repository is

A single repository holding both halves of one solution. They are released
separately, under different licences.

| Directory | Package | Released as |
|---|---|---|
| `backend/` | `pas.plugins.identity` | PyPI, GPL-2.0-only |
| `frontend/packages/identity-core/` | `@plone-collective/identity-core` | Not yet published; MIT |
| `frontend/packages/volto-identity/` | `@plone-collective/volto-identity` | npm, MIT |
| `frontend/packages/aurora-identity/` | `@plone-collective/aurora-identity` | Not yet published; MIT |
| `frontend/aurora/` | Development harness running Plone Aurora with the add-on | — |
| `docs/` | The published documentation and its screenshot harness | — |

They live together on purpose: a REST API payload and the component that reads
it change in one commit, and a reference page cannot drift from the source it
documents.

`identity-core` holds what the Volto add-on shares with the Aurora add-on
([#132](https://github.com/collective/pas-plugins-identity/issues/132)): the
REST payload types, the endpoint table, the framework-free helpers, the login
components and the callback card. An ESLint override in `frontend/.eslintrc.js` rejects any
import of Volto, Aurora, Redux, a router or an i18n library in it. React,
`react-aria-components` and `@plone/components` are allowed, because both
frontends have them. Code that needs anything else belongs in the add-on.

Core components get translations, links and icons from `useIdentityUI()`.
Each add-on provides them through an `IdentityUIProvider` -- `VoltoIdentityUI`
and `AuroraIdentityUI` -- wrapped around every container that renders one.
Core's styles are plain CSS: Aurora has no Sass compiler.

Core declares its messages with `defineMessages` imported from `#i18n`, never
by a relative path: the extractor recognises the call by that import name
(`identity-core/babel.config.js`). A message declared any other way is
silently left out of the catalogue. Core owns those translations; the Aurora
add-on's `locales/*/common.json` are generated from them by `pnpm i18n` in
`frontend/aurora`, and are never edited by hand.

### Two harnesses share `frontend/packages`

`frontend/` is the Volto harness and `frontend/aurora/` the Aurora one. Each is
its own pnpm workspace, with its own `mrs.developer` checkout in `core/`, its
own React (18 and 19) and its own pnpm (10 and 11). Both install
`identity-core`, so its `node_modules` points at whichever harness installed
last. Each harness corrects for that, and a change touching it has to keep
doing so:

- **Bundling:** `volto-identity/razzle.extend.js` aliases core's peer
  dependencies to Volto's copies, and `frontend/aurora/harness/vite.extend.js`
  deduplicates them in Aurora. Without them a page bundles two Reacts.
- **Typechecking:** each package's `typecheck` uses a `tsconfig.typecheck.json`
  that maps core's peers to that package's own copies and, in the add-ons,
  includes core's sources, so core is typechecked against both frontends'
  types. Those mappings never go in `tsconfig.json`: Volto turns every
  add-on's `tsconfig.json` `paths` into webpack aliases, and a path pointing
  at type declarations leaves webpack nothing to bundle.
- **Storybook:** its story globs stay inside `packages/*/src`. A wider glob
  follows `aurora-identity`'s `node_modules` into Aurora's own stories.
- **Catalogues:** a package used by both workspaces may use `catalog:` only for
  entries both catalogues define, and `workspace:*` only for packages both
  workspaces have.
- **React Aria:** both harnesses override `react-aria-components`,
  `react-aria`, `react-stately`, `@react-aria/utils`, `@react-spectrum/utils`
  and `@internationalized/date` to the ranges in
  `frontend/aurora/core/catalog.json`: `pnpm.overrides` in
  `frontend/package.json`, `overrides` in `frontend/aurora/pnpm-workspace.yaml`.
  Keep the two lists the same, and both lockfiles resolving the same versions,
  so core's components run on one React Aria in both frontends. They go once
  Volto's `@plone/components` and Aurora's agree by themselves.

The Aurora add-on renders Aurora's `/login` with its own page,
`aurora-identity/routes/login.tsx`. Aurora's registry cannot replace a route,
and the `loginActions` slot it offers sits inside its password `<Form>`, where
the add-on's forms cannot go. So `aurora-identity/index.ts` swaps the file
`@plone/cmsui` registered for `/login` (`lib/routes.ts`), and warns at build
time when that file is no longer there. Upgrading Aurora means checking that
`AURORA_LOGIN_FILE` still names it.

The Aurora version is pinned by `frontend/aurora/mrs.developer.json`. Aurora's
upgrade guides live in its checkout, at
`frontend/aurora/core/docs/upgrade-guide/`.

`frontend/core` and `frontend/aurora/core` are **not ours**. They are
`mrs.developer` checkouts of Volto and Aurora, excluded by their harness's
`.gitignore`. Never edit them, never cite them as this project's convention,
and ignore any `AGENTS.md` found inside them.

## Setup

```shell
make install                # both halves
make backend-create-site    # first run only
make backend-start          # http://localhost:8080/
make frontend-start         # http://localhost:3000/, second shell
make aurora-install         # optional: the Aurora harness
make aurora-start           # http://localhost:3000/, instead of Volto
```

`make backend-install` and `make frontend-install` do one half each. Python is
`>=3.12`; dependencies are managed with `uv` — never raw `pip`.

## Gates

Run these before proposing a commit. CI runs the same ones.

| Command | From | Checks |
|---|---|---|
| `make check` | root | `make format` then `make lint`, both halves |
| `make test` | root | `make backend-test` and `make frontend-test` |
| `make check-imports` | `backend/` | The core/server layer boundary |
| `make aurora-lint`, `make aurora-test`, `make aurora-build` | root | The Aurora add-on. Needs `make aurora-install`; CI runs them in `.github/workflows/aurora.yml` |
| `make acceptance-test` | `frontend/aurora` | A real sign-in through Dex, with Playwright. Needs the services its `acceptance-*` targets start; CI runs it too |
| `make docs-build` | root | Sphinx with `-W`, warnings as errors |
| `make vale` | `docs/` | Prose style. **Errors must be zero**; warnings are advisory |

Backend coverage has a floor: `fail_under = 97` in `backend/pyproject.toml`.
A change that adds uncovered lines fails the suite rather than warning.

`make backend-test` runs `pytest -m "not docker"`. Tests that drive real
containers are marked `docker` and run with `make -C backend test-docker`.

## Rules that are easy to get wrong

### Run `make format` before staging

The formatters rewrite files. Formatting after `git add` leaves the staged and
working copies disagreeing, and the commit carries whichever half you were not
looking at. This also defeats string-replacement edits written against a
remembered file shape — re-read a file after formatting it.

### The layer boundary is enforced, and soft imports count

`make check-imports` runs import-linter contracts asserting that core never
imports the optional `[server]` layer. import-linter reads function bodies, so
moving an import inside a function does not get past it. The rationale is in
`docs/docs/concepts/layers.md`.

It is **not** part of `make lint`. Run it yourself when you touch either layer.

It also builds its own clean virtualenv, because the migration test
dependencies ship a `pas/__init__.py` that stops `pas.plugins` being a PEP 420
namespace — see the comment at `backend/Makefile:218`.

### Ruff's config does not cover the whole repository

`backend/pyproject.toml` holds the ruff settings, including `force-single-line`
imports and the per-file ignores. It applies to `backend/` only. Invoking
`uvx ruff` from the root uses ruff's own defaults and will contradict the
repository — pass `--config backend/pyproject.toml`, or just use `make format`
and `make lint`.

### Every change carries a news fragment

There are five towncrier scopes. A change adds one fragment to each scope it
touches:

| Scope | Folder |
|---|---|
| Repository and documentation | `news/` |
| Backend | `backend/news/` |
| Frontend | `frontend/packages/volto-identity/news/` |
| Frontend core | `frontend/packages/identity-core/news/` |
| Aurora add-on | `frontend/packages/aurora-identity/news/` |

Name it `<issue>.<type>`, or `+<slug>.<type>` when no issue exists. Types:
`breaking`, `feature`, `bugfix`, `documentation`, `internal`, `tests`. Write in
the past tense for somebody reading the changelog rather than the diff, and end
with the author's GitHub handle.

### A bugfix carries a test that fails without it

Verify that by removing the fix and watching the test go red. A regression test
nobody has seen fail may be asserting nothing.

## Documentation

`docs/STYLE.md` is the house style, and it is short. The parts that catch
people out:

- **The code is the source of truth.** Cite the file a fact came from in an
  HTML comment under the heading it supports.
- No "should" language. Either it does, or you have not run it — and then say
  that.
- Reference pages are tables. Rationale belongs in `concepts/`.
- Diagrams are Mermaid, never images. Screenshots come from the harness in
  `docs/screenshots/`, never captured by hand.
- Every page ends with **Related** or **Next steps**.

Build with `make docs-build` from the root, or `make html` from `docs/`.
`make -C docs livehtml` serves a live-reloading build on port 8050.

Two Mermaid traps, both of which cost a debugging session:

- `sphinxcontrib-mermaid`'s `:config:` option takes **JSON**, and it claims a
  leading `---` block inside the code fence as that option. YAML front-matter
  in a mermaid block therefore crashes the build with a `JSONDecodeError`.
- Flowchart node labels default to an SVG `foreignObject`, which some browsers
  do not paint — the boxes render empty while edge labels still show. Use
  `:config: {"flowchart": {"htmlLabels": false}}` for native SVG text.

Screenshots need the demo stack running (`make demo-stack-start`) and are
captured with `make -C docs screenshots`. `make -C docs screenshots-coverage`
fails when a page references a screenshot nothing captures, or when an image is
referenced by nothing.

## Releasing

Both packages go out together, with `uvx repoplone release <segment>` from the
repository root. The procedure is in
[`docs/docs/contributing.md`](docs/docs/contributing.md#releasing).

**Do not run it.** A release publishes to PyPI and to npm under somebody's
credentials, tags the repository and opens a GitHub release — none of which can
be taken back, and the command asks for confirmation exactly once. Preparing a
release is fair game: fragments, metadata, the READMEs, a dry run. Cutting one
is a person's job.

## Security

Do not open an issue for a vulnerability. Follow [SECURITY.md](SECURITY.md).

Provider client secrets and signing keys never go into committed files —
not into `profiles/default/registry/`, not into fixtures, not into
documentation examples.

The one exception is `profiles/initial/registry/`. The `initial` profile is a
developer's quick start, and its GitHub and Google providers carry real client
secrets on purpose, so a fresh checkout can sign in without registering an
application first. Those applications accept only a `localhost` callback. Do
not flag them, move them into the environment, or copy them anywhere else, and
never add a secret for any other callback to that profile.

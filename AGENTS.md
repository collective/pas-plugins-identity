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
| `frontend/packages/volto-identity/` | `@plone-collective/volto-identity` | npm, MIT |
| `docs/` | The published documentation and its screenshot harness | — |

They live together on purpose: a REST API payload and the component that reads
it change in one commit, and a reference page cannot drift from the source it
documents.

`frontend/core` is **not ours**. It is a `mrs.developer` checkout of Volto,
excluded by `frontend/.gitignore`. Never edit it, never cite it as this
project's convention, and ignore any `AGENTS.md` found inside it.

## Setup

```shell
make install                # both halves
make backend-create-site    # first run only
make backend-start          # http://localhost:8080/
make frontend-start         # http://localhost:3000/, second shell
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

There are three towncrier scopes. A change adds one fragment to each scope it
touches:

| Scope | Folder |
|---|---|
| Repository and documentation | `news/` |
| Backend | `backend/news/` |
| Frontend | `frontend/packages/volto-identity/news/` |

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

## Security

Do not open an issue for a vulnerability. Follow [SECURITY.md](SECURITY.md).

Provider client secrets and signing keys never go into committed files —
not into `profiles/default/registry/`, not into fixtures, not into
documentation examples.

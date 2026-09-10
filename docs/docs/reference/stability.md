---
myst:
  html_meta:
    "description": "What is settled in pas.plugins.identity and what may still change before 1.0.0."
    "property=og:description": "What is settled in pas.plugins.identity and what may still change before 1.0.0."
    "property=og:title": "Stability"
---

(reference-stability)=

# Stability

What you can build against today, and what may change before 1.0.0.

## The two packages

| | |
|---|---|
| Backend | `pas.plugins.identity` |
| Frontend | `@plone-collective/volto-identity` |

They are versioned and released together. See {doc}`/how-to-guides/install` and {doc}`/how-to-guides/install-the-frontend`.

## What alpha means here

A change to a registry record, a content type or a plugin reaches an existing site when the profile is reapplied, and only then.
`pas.plugins.identity:default` is at version 1004 and declares an upgrade step for each thing a reapplied profile cannot carry: a persistent object written at install, and a value only a walk of the site can compute.
`pas.plugins.identity.server:default` is at 1000 and declares none.
{doc}`/how-to-guides/upgrade` lists what each step does.

Plan for that: treat an alpha site as one you can rebuild, and read {doc}`/how-to-guides/upgrade` before taking a new release.

## Settled

These are covered by tests that fail loudly if they change.

| Area | What holds | Enforced by |
|---|---|---|
| Layer boundaries | Core imports nothing from the `server` or `sql` layers, and nothing imports `api` | four import-linter contracts, run in CI |
| No-extras install | The package installs and imports with no extras | the `Backend: No-extras install imports` CI job |
| The Python import path | Names published by {doc}`python-api` are imported from `pas.plugins.identity.api` | a test for each group of calls, asserting the names it documents |
| Uninstall | Every profile has a matching uninstall profile that leaves nothing behind | uninstall tests per profile |
| Account data | Uninstalling removes types, catalog and workflows, and no `UserProfile` object | uninstall tests |
| Security properties | The list in {doc}`security-guarantees` | the test suite |
| Python and Plone | Plone 6.2 on Python 3.12, 3.13 and 3.14 | the CI matrix |

## Not settled

Expect these to change without a migration path before 1.0.0.

| Area | Why it may move |
|---|---|
| REST endpoint names and payloads | Named in {doc}`endpoints`; no deprecation cycle yet |
| Registry keys and defaults | Named in {doc}`settings`; a rename means a reinstall |
| The driver contract | {doc}`driver-contract` is the current shape; a third-party driver may need edits |
| The scope serializer contract | {doc}`/how-to-guides/serialize-a-claim` is the current shape; a downstream serializer may need edits |
| Frontend routes and component names | Named in {doc}`frontend`; shadowed components especially |
| The `[sql]` audit schema | One table today, and no migration tooling for it |
| Event interfaces | Named in {doc}`events` |
| Individual names in the Python API | The import path is settled; what is published at it may still gain and rename members before 1.0.0. {doc}`python-api` is the current surface |

## Classic UI

Sign-in requires the Volto frontend.
The add-on registers no Classic UI login view, viewlet or form, so a site without Volto has no way to start a sign-in.

Classic UI support is intended, and is not in this release.

One part already works without Volto: the authorization server's consent screen is a server-rendered page template, so a site running the `server` layer can be an identity provider for other applications regardless of which frontend it uses itself.

## Reporting

Report a security vulnerability privately, following [SECURITY.md](https://github.com/collective/pas-plugins-identity/blob/main/SECURITY.md).
Report anything else as a GitHub issue.

## Related

- {doc}`security-guarantees`—the properties the test suite enforces
- {doc}`/concepts/threat-model`—the reasoning behind them
- {doc}`/concepts/layers`—what each layer is for
- {doc}`/how-to-guides/upgrade`—taking a new release

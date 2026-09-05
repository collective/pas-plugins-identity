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

There are **no GenericSetup upgrade steps**.
Both installable profiles are at version 1000, and `upgrades/configure.zcml` declares nothing.
A change to a registry record or a content type between alpha releases reaches an existing site only if you reinstall the add-on.

Plan for that: treat an alpha site as one you can rebuild, and read {doc}`/how-to-guides/upgrade` before taking a new release.

## Settled

These are covered by tests that fail loudly if they change.

| Area | What holds | Enforced by |
|---|---|---|
| Layer boundaries | Core imports nothing from the `server` or `sql` layers | three import-linter contracts, run in CI |
| No-extras install | The package installs and imports with no extras | the `Backend: No-extras install imports` CI job |
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
| Frontend routes and component names | Named in {doc}`frontend`; shadowed components especially |
| The `[sql]` audit schema | One table today, and no migration tooling for it |
| Event interfaces | Named in {doc}`events` |

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

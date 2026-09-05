# Documentation rewrite — what changed

Working file, not published. Branch `docs-update`, 2026-09-05.

Companion files: `AUDIT.md` (the before-state and its 13 defects), `AUDIT-CODE.md`
(the source-of-truth extraction the rewrite was written from),
`TUTORIAL-RUN-LOG.md` (Gate 0.7, and five more defects found by running the
stack), `HUMAN-ACTIONS.md` (what is left for a person), `STYLE.md` (the house
rules the rewrite followed).

## Shape

Counts include each section's own `index.md`.

| | Before | After |
|---|---|---|
| Published pages | 33 | 57 |
| `reference/` | 10 | 18 |
| `how-to-guides/` | 11 | 25 (8 of them under `providers/`) |
| `concepts/` | 8 | 10 |
| `tutorials/` | 2 | 2 |
| Mermaid diagrams | 0 | 5 |
| Screenshots | 0 | 5, all captured by a committed harness |
| Content pages ending with Related or Next steps | 8 | **all 51** (the 6 index pages carry a `toctree` instead) |
| `sphinx-build -W` | clean | clean |
| `make vale` | 210 errors | 0 errors |

## New pages

### Reference

| Page | Why it did not exist |
|---|---|
| `reference/endpoints.md` | The landing page promised it. Every REST service, browser view and sub-path, with the permission each enforces. |
| `reference/settings.md` | Every registry record, with type and default, including the whole `IProfileSettings` group and `IServerSettings`, neither of which was documented anywhere. |
| `reference/provider-form.md` | The control panel form as the operator sees it, tab by tab, composed from three sources. |
| `reference/frontend.md` | The Volto add-on's routes, components and build-time variables. |
| `reference/permissions.md` | The six permissions and their site-wide floor. |
| `reference/install-profiles.md` | Every GenericSetup profile and the upgrade situation. |
| `reference/driver-contract.md` | What a driver must implement, extracted from the how-to that was carrying it. |
| `reference/stability.md` | Which contracts are contracts, at alpha. |

### How-to

`install-the-frontend.md`, `troubleshoot.md`, `upgrade.md`,
`link-accounts-by-email.md`, `map-provider-groups.md`,
`control-account-creation.md`, and a `providers/` set of seven recipes:
`another-plone-site`, `generic-oidc`, `magic-link`, `keycloak`, `github`,
`google`, `microsoft-entra`.

The four provider-side procedures nobody could verify against a live account
(`github`, `google`, `microsoft-entra`, and the console half of `generic-oidc`)
carry a warning saying so and point at the provider's own documentation. The
Plone half of every one is read from source and is accurate. `keycloak` was
verified against a live Keycloak 26 container; `another-plone-site` and
`magic-link` against the demo stack.

### Concepts

`mental-model.md` (three diagrams, and the map of which quadrant a reader needs)
and `threat-model.md`.

## Renames

| From | To | Why |
|---|---|---|
| `reference/profiles.md` | `reference/profiles-and-groups.md` | "Profiles" collided with GenericSetup profiles. Now pairs with `concepts/profiles-and-groups.md`. |
| *(new page)* `profiles-and-upgrades.md` | `reference/install-profiles.md` | Same collision, from the other side. |

## Defects fixed

All 13 from `AUDIT.md` and all 5 from `TUTORIAL-RUN-LOG.md`.

| # | Was | Now |
|---|---|---|
| D1 | Tutorial names "Alice"; the demo user is Dana | Dana throughout |
| D2 | Tutorial's layer table lists a `profile` layer that does not exist | core and `[server]` |
| D3 | Landing page promises endpoint and settings pages that did not exist | Both written |
| D4 | Frontend install was one sentence | `install-the-frontend.md` |
| D5 | Callback URL called mandatory, never shown | Shown with its value and its full redirect URI, in `install.md` |
| D6 | Classic UI support never stated | Stated on `stability.md` and the landing page |
| D7 | Alpha status visible only in the title bar | Stated on the landing page and in `stability.md` |
| D8 | `rebuild-catalog` had no how-to | Covered in `upgrade.md`, and listed in `install-profiles.md` |
| D9 | Glossary defined 15 terms nothing linked to; no `identity`, `group`, `user id` | Three entries added, and `{term}` used—on `concepts/mental-model.md` only, so far. See `HUMAN-ACTIONS.md`. |
| D10 | 25 of 33 pages ended nowhere | Every page ends with Related or Next steps |
| D11 | ORCID advertised as a shipped provider | Removed from both READMEs; the five real drivers are tabulated |
| D12 | "one optional extra" | Two: `server` and `sql`, both documented in `install.md` |
| D13 | `pip install pas.plugins.identity` | The git install, with a note that it is not on PyPI |
| D14 | Tutorial's magic-link section could not be performed | Rewritten around enabling the provider in the control panel first, which also teaches `enabled` versus `show_in_login` |
| D15 | An unexplained `VOLTO_VERSION` warning twice per command | Stated as harmless |
| D16 | Tutorial layer table wrong (same as D2) | Fixed |
| D17 | Magic-link prose described the old mail arrangement | Describes what the demo package now does |
| D18 | Group-crossing section named the wrong group three times | `content-site-editors`, which is the mapped one |

## Factual corrections found while writing

Each of these was in the docs, or would have been, and was caught by reading the
source rather than by review.

| Claim | Reality |
|---|---|
| `google` has a configurable group claim | Its settings schema is `IOAuth2Settings`. **No Groups tab exists.** Same for `github` and `email`. |
| `email` providers have trust and account switches | `IEmailSettings` extends `IDriverSettings` only. No `create_user`, so an `email` provider always creates accounts. |
| Provider form tabs inferred from backend fieldsets | The real form composes Identity + Style from `IProviderRecords`, the driver's fieldsets prefixed `settings-`, and a frontend-composed Mapping tab. |
| `server_issuer` undocumented | It is in `IServerSettings`, a schema no page had introspected. |
| The whole `IProfileSettings` group undocumented | Twelve records, including the container layout and the profile gate. |
| Endpoint table listed bare paths | Nine of them take sub-paths (`@identity-keys/rotate`, `@identity-clients/<id>/rotate-secret`, `@identities/<provider>/<subject>`, …); a bare POST is a 400. |
| Keycloak recipe written from documentation | Verified live: `email_verified` is a real boolean by default, `groups` is **absent** until a Group Membership mapper exists, and `realm_access` is not in the `id_token` at all. |
| Profile omits `server_clients` to avoid overwriting a live registry | The actual reason is that an empty `<value>` imports as `None` while omitting the key takes the schema default. |

## Content moved

Rationale removed from reference pages, per the Diátaxis split:

| From | To |
|---|---|
| `reference/claims.md` — the two unregistered claims, and `groups` riding on a display scope | `concepts/federation.md` |
| `reference/profiles.md` — the address-list history, and why `Owner` is stated per state | `concepts/profiles-and-groups.md` |
| `reference/shipped-drivers.md` — back-channel logout | `reference/endpoints.md`, where the other endpoints are |
| `how-to-guides/write-a-driver.md` — the interface itself | `reference/driver-contract.md` |

## Tooling added

| Path | Does |
|---|---|
| `docs/screenshots/` | Playwright + pytest harness. `discovery.py` finds every screenshot a page references; `test_coverage.py` fails when one has no script. |
| `docs/scripts/generate_placeholders.py` | Writes a marked placeholder PNG for any referenced-but-uncaptured screenshot, so the build never breaks on a missing image. |
| `docs/Makefile` targets | `screenshots-install`, `screenshots-coverage`, `screenshots-placeholders`, `screenshots` |
| `docs/STYLE.md` | The house rules, written from what the rewrite actually did |
| `.vale.ini` `TokenIgnores` | Skips MyST anchor targets, which are markup rather than prose |

Three harness bugs were found and fixed while capturing: a token written to
`localStorage` when Volto reads a cookie (three captures were silently
photographing anonymous pages), a click that hit a table cell instead of a button
(two captures were byte-identical and the test passed), and a capture that did
not match the prose around it.

One requested screenshot, `login-page-one-provider`, is impossible: the relying
party's login page auto-redirects, exactly as the tutorial says. The reference,
the script and the placeholder were all removed rather than faked.

# AUDIT

Working file, not published. Measured on 2026-09-05 with
`scratchpad/page_audit.py`, against `docs/docs/` on branch `docs-update`.

33 pages, **26,142 words**.

## Gate 0.1 and 0.2 results

| Check | Result |
|---|---|
| `sphinx-build -b html -W --keep-going` | **passes, zero warnings** |
| `make linkcheck` | see §5 |

The build being clean at `-W` is worth recording: the defects in this
documentation are editorial and structural, not broken markup.

## The table

`rat%` is the share of sentences containing one of *because, rather than, is
not, are not, and that is, instead of, the reason* — the constructions two
reviewers independently identified as the package's tic. `doc` is outbound
`{doc}` cross-references.

| Page | Quadrant | Words | Numbered steps | rat% | `{doc}` out |
|---|---|---|---|---|---|
| `index.md` | root | 335 | 0 | 10 | 6 |
| `glossary.md` | root | 33 | 0 | 0 | 0 |
| `tutorials/index.md` | tutorials | 74 | 0 | 0 | 0 |
| `tutorials/federation-demo.md` | tutorials | 958 | 0 | 8 | 1 |
| `how-to-guides/index.md` | how-to | 101 | 0 | 0 | 1 |
| `how-to-guides/install.md` | how-to | 484 | **0** | 10 | 3 |
| `how-to-guides/configure-a-provider.md` | how-to | **1648** | 3 | 12 | 5 |
| `how-to-guides/read-the-audit-log.md` | how-to | 408 | **0** | 11 | 2 |
| `how-to-guides/review-a-user-account.md` | how-to | 491 | 3 | 9 | 5 |
| `how-to-guides/enable-back-channel-logout.md` | how-to | 383 | 3 | 8 | 2 |
| `how-to-guides/export-and-import-principals.md` | how-to | 567 | **0** | 20 | 3 |
| `how-to-guides/register-an-oauth-client.md` | how-to | 648 | **0** | 8 | 4 |
| `how-to-guides/migrate-from-authomatic.md` | how-to | 373 | **0** | **25** | 3 |
| `how-to-guides/migrate-from-oidc.md` | how-to | 385 | **0** | 13 | 2 |
| `how-to-guides/write-a-driver.md` | how-to | 1040 | **0** | 17 | 2 |
| `reference/index.md` | reference | 64 | 0 | 0 | 1 |
| `reference/profiles.md` | reference | **2882** | 0 | 19 | 4 |
| `reference/principal-documents.md` | reference | 1669 | 3 | **24** | 3 |
| `reference/security-guarantees.md` | reference | 1351 | 0 | 16 | 7 |
| `reference/claims.md` | reference | 1085 | 0 | 15 | 4 |
| `reference/user-content.md` | reference | 1068 | 0 | 14 | 5 |
| `reference/shipped-drivers.md` | reference | 887 | 0 | 18 | 4 |
| `reference/audit-log.md` | reference | 645 | 0 | 9 | 2 |
| `reference/events.md` | reference | 583 | 0 | 7 | 4 |
| `reference/migration-reports.md` | reference | 340 | 0 | 12 | 2 |
| `concepts/index.md` | concepts | 91 | 0 | 0 | 0 |
| `concepts/profiles-and-groups.md` | concepts | 1598 | 0 | 19 | 4 |
| `concepts/users-as-content.md` | concepts | 1554 | 0 | **22** | 5 |
| `concepts/email-verification.md` | concepts | 1246 | 0 | 17 | 4 |
| `concepts/federation.md` | concepts | 1202 | 0 | 19 | 4 |
| `concepts/layers.md` | concepts | 791 | 0 | 15 | 3 |
| `concepts/identities.md` | concepts | 665 | 0 | 15 | 3 |
| `concepts/secrets.md` | concepts | 493 | 0 | 15 | 2 |

## What the numbers say

**1. Ten how-to guides, and seven of them contain not one numbered step.**
`install.md`, `read-the-audit-log.md`, `export-and-import-principals.md`,
`register-an-oauth-client.md`, `migrate-from-authomatic.md`,
`migrate-from-oidc.md` and `write-a-driver.md` have zero. The three that do have
three each. This is the plan's central claim, measured: the how-to quadrant is
prose, not procedure.

**2. Rationale density is uniform across quadrants.** Concepts average 17%,
how-to 13%, reference 15%. A reader cannot tell which quadrant they are in from
the writing. The extremes are in the wrong places: `migrate-from-authomatic.md`
is the *most* rationale-dense page in the whole set at 25%, and it is a how-to.

**3. Reference is where the words are.** `reference/profiles.md` alone is 2,882
words — 11% of the documentation, and the single largest page. Reference pages
total 10,574 words against how-to's 6,128.

**4. `{term}` is used zero times, on every page.** The glossary exists and
nothing links into it. Combined with the empty inbound counts, the glossary is
unreachable except by navigation.

**5. Pages do cross-link.** Between 1 and 7 `{doc}` references each, except
`concepts/index.md`, `tutorials/index.md` and `glossary.md`, which have none.
The reviews' "reader does not know what to do next" is therefore **not** an
absence of links — it is that the ending is unstructured on most pages.
**8 of 33** end with a "Next steps" or "Related" section
(`configure-a-provider`, `register-an-oauth-client`, `review-a-user-account`,
and five of the seven concept pages). The other 25 stop when the prose stops.
Every quadrant is affected; reference has none at all.

**6. The glossary is good, and unreachable.** ~600 words defining 15 terms of
this package's own — audit log, claim, client, driver, external identity,
issuer, magic link, nested group, preferred address, Profile, provider, relying
party, subject, verified address, userid — alongside the four the cookiecutter
shipped. Nothing links into any of them, per finding 4. The problem is reach,
not content.

Gaps worth filling while linking them up: no entry for **identity** on its own
(only *external identity*), none for **group** (only *nested group*), and
**userid** is spelled as one word while the prose says "user id".

## Unsearchable headings

The plan's table, confirmed present, plus what the scan found beyond it.

| Page | Current | Proposed |
|---|---|---|
| `configure-a-provider.md` | Give it a look | Style the login button |
| `configure-a-provider.md` | Decide whether it works, and whether it is advertised | Enable a provider and show it on the login page |
| `configure-a-provider.md` | Change a secret, or keep it | Replace or keep the client secret |
| `configure-a-provider.md` | Decide whether the provider's email verification counts | Trust a provider's email verification |
| `configure-a-provider.md` | Decide whether the provider may create accounts | Allow or block account creation |
| `configure-a-provider.md` | Keep the provider, decide the groups yourself | Disable provider-managed group membership |
| `concepts/identities.md` | The user id is opaque, and that is not an accident | Why the user id is a random UUID |
| `concepts/identities.md` | A collision is an error, not a merge | Why linking collisions raise instead of merging |
| `concepts/identities.md` | Unlinking your last way in is refused | Why the last sign-in method cannot be unlinked |

Further renames are decided per page during Phase 2 and Phase 3 and recorded in
`CHANGES-DOCS.md`.

## Confirmed defects

| # | Defect | Evidence |
|---|---|---|
| D1 | `federation-demo.md:62` says "Alice exists only on `id.localhost`"; the demo user is Dana | `backend/demo/src/identitydemo/settings.py:111` `DEMO_USER_ID = "dana"` |
| D2 | Tutorial's layer table lists `core`, `profile`, `server`; there is no `profile` layer | `AUDIT-CODE.md` §8 |
| D3 | Landing page and `reference/index.md` promise "endpoints, settings"; neither page exists | `docs/docs/reference/` listing |
| D4 | Frontend install is one sentence; no steps, version, or add-on registration | `how-to-guides/install.md` |
| D5 | Callback URL described as mandatory, never shown as a value | `configure-a-provider.md` |
| D6 | Classic UI support never stated | absent |
| D7 | Alpha status visible only in the title bar | `index.md` |
| D8 | `rebuild-catalog` profile has no how-to | `AUDIT-CODE.md` §7 |
| D9 | Glossary defines 15 package terms and nothing links to any of them; missing entries for *identity*, *group* | `glossary.md`; `{term}` count of 0 |
| D10 | 25 of 33 pages end without a "Next steps" or "Related" section; no reference page has one | §5 above |
| D11 | Landing page and `README.md` advertise **ORCID** as a provider; no ORCID driver exists | `AUDIT-CODE.md` §3 — the five drivers are `email`, `github`, `google`, `oidc-generic`, `plone-identity` |
| D12 | Landing page says "a core and one optional extra"; there are two (`server`, `sql`) | `backend/pyproject.toml` |
| D13 | `install.md` says `pip install pas.plugins.identity`; the package is not on PyPI | npm/PyPI both 404, `AUDIT-CODE.md` §13 |

## Method note

**The word counts in the table above understate every page.** The measuring
script stripped everything between ``` fences, which in MyST removes admonitions,
`{glossary}` blocks and `{mermaid}` diagrams along with the code samples it meant
to drop. The effect is small for most pages (under 90 words) and total for
`glossary.md`, which is one directive from top to bottom: it measured 33 words
and contains about 600.

Re-measured keeping directive content, the pages listed under finding 6 gain
between 45 and 120 words each. The table is left as measured, with this note,
because the ranking it drives is unaffected — but no number in it should be
quoted as a page's length.

The first run of `page_audit.py` counted markdown `](...)` links and reported
zero cross-references on every page. That was the script's fault, not the
documentation's: cross-references here are MyST `{doc}` roles. The finding was
re-measured before being written down. The same caution applies to the `rat%`
column, which is a keyword count and not a judgement — it locates candidates for
the Phase 6 pass, and does not by itself condemn a sentence.

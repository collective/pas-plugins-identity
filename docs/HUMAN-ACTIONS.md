# What is left for a person

Working file, not published. Branch `docs-update`, 2026-09-05.

Everything here is something I could not verify, could not decide, or should not
decide. Nothing on this list blocks the branch; all of it is worth a look before
1.0.

## Must be checked by a human before release

### 1. Four provider recipes were never walked through

`how-to-guides/providers/github.md`, `google.md`, `microsoft-entra.md`, and the
provider-console half of `generic-oidc.md` describe consoles I have no account
for. Each carries a warning saying so.

The **Plone** half of each is read from source and is accurate. What needs a
person is the provider-side procedure: menu names, where the redirect URI field
lives, what the secret screen looks like now.

`keycloak.md` was verified against a live Keycloak 26 container.
`another-plone-site.md` and `magic-link.md` were verified against the demo stack.

**Suggested:** run one of the four end to end, and either confirm the steps or
correct them. Then drop that page's warning. Leave the warning on the ones still
unwalked — it is more useful than a confident guess.

### 2. The authomatic extraction script is documented and untested

`reference/principal-documents.md` ships a complete extraction script under
"Writing the extraction". It cannot run in this repository, because it needs a
site with `pas.plugins.authomatic` installed.

Two of its details were found by running it against a real authomatic store —
`setSite(site)` and reading `_identities` rather than `propertysheet` — so the
script is not theoretical. But it is not covered by CI and will rot.

**Suggested:** either accept that and note the date it was last run, or add a
test fixture that stands in for an authomatic plugin.

### 3. Screenshots are five, and could be more

`make -C docs screenshots-coverage` passes: every screenshot a page references
has a script that captures it. It does **not** assert that pages which *should*
have a screenshot do.

Candidates a person might want: the audit log panel, the identities page as an
administrator sees it, the consent screen, the sign-in methods page.

Adding one is a `Shot` in `docs/screenshots/`, a `{image}` in the page, and
`make -C docs screenshots`.

## Decisions I did not make

### 4. The two overlapping concept pages

`concepts/profiles-and-groups.md` and `concepts/users-as-content.md` both carry
a "Membership lives on the member" section and both carry a "Why not
`Products.membrane`" section. The content differs in emphasis, not in substance.

I left both, because merging them is a judgment about which reader each page is
for, and I would be guessing.

**Suggested:** decide whether `users-as-content` is the mechanism page and
`profiles-and-groups` is the policy page, then let each own one copy.

### 5. Vale warnings and suggestions

`make vale` is clean of **errors**. It still reports 128 warnings and about 1,190
suggestions, almost all of them `Microsoft.Passive`, `Microsoft.Contractions`
and `Microsoft.SentenceLength`.

Acting on the contractions ones would change the register of the whole
documentation. That is a house-voice decision, not a lint fix.

**Suggested:** either turn those three rules off in `.vale.ini` so the signal is
honest, or leave them and accept that the counts stay high.

### 6. Alpha wording

`reference/stability.md` states which contracts are contracts. The wording of
what "alpha" commits you to is yours, not mine — particularly the line about the
event contract requiring a changelog note after 1.0.

## Known-imperfect, deliberately

### 7. Word counts in `AUDIT.md` understate every page

The measuring script stripped MyST directive content along with code fences. The
table carries a Method note saying so. It was left as measured because the
ranking it drives is unaffected, but no number in it should be quoted.

### 8. `login-page-one-provider` does not exist and cannot

The relying party's login page auto-redirects when there is exactly one
provider — which is the point the tutorial is making. The reference, the capture
script and the placeholder were removed rather than faked.

## Housekeeping before merging

- [ ] The demo stack may still be running. `docker compose -f docker-compose.demo.yml down --volumes`.
- [ ] `docs/AUDIT.md`, `docs/AUDIT-CODE.md`, `docs/TUTORIAL-RUN-LOG.md`, `docs/CHANGES-DOCS.md` and this file are working documents. Decide whether they belong in the repository or only in the PR description.
- [ ] `docs/STYLE.md` is meant to stay.
- [ ] A news fragment for the docs work.

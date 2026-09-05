# Tutorial run log — plan item 0.7

Working file, not published. `tutorials/federation-demo.md` run against a real
stack on 2026-09-05, from a torn-down state (`down --volumes`), on branch
`docs-update`.

Stack: `make demo-stack-start`, which built both images from scratch. All six
services reached healthy: `db`, `traefik`, `idp-backend`, `idp-frontend`,
`rp-backend`, `rp-frontend`.

## Steps that ran exactly as written

| Step | Check | Result |
|---|---|---|
| Start the stack | `make demo-stack-start` | both sites listening |
| Open the relying party | `GET http://plone.localhost` | 200 |
| Open the provider | `GET http://id.localhost` | 200 |
| "offers exactly one way in" | `@login-providers` on `plone.localhost` | exactly one: `demo-idp`, driver `plone-identity` |
| Sign in as `dana` | `POST @login` with `dana` / `dana-demo-password` | token issued |
| Fetch the contract | `curl .../.well-known/openid-configuration \| jq` | issuer, `authorization_endpoint`, `token_endpoint`, `jwks_uri` all present and pointing at `id.localhost` |

The discovery step is worth calling out: the tutorial promises the reader will
read four specific fields out of that document, and all four are there with the
values the surrounding prose describes.

## Defects found by running it

### D14 — the magic-link section cannot be performed

The tutorial says:

> Go back to the provider at <http://id.localhost/login> and choose the
> magic-link option.

There is no magic-link option on that page.

`@login-providers` on `id.localhost` returns **only** GitHub. The demo's `email`
provider is configured with `show_in_login = False`
(`profiles/idp/registry/pas.plugins.identity.xml`), `@login-providers` filters on
that flag, and `LoginForm.tsx:126` decides whether to render `MagicLinkForm` by
looking for an `email` driver **in that list**. Enabled, and not offered.

**The demo is right and the tutorial is stale.** `show_in_login = False` is
Érico's own change, commit `dbb4956` of 2026-09-04, made deliberately so the
stack demonstrates the difference between `enabled` and `show_in_login`. The
tutorial predates it.

The endpoint itself works: `POST @magic-link` with `dana@id.localhost` answers
`{"sent": true}` and the link appears in `make demo-stack-logs`. So the feature
is fine and only the instruction is wrong.

Fix in Phase 5: rewrite the section to demonstrate what the demo now
demonstrates — a provider that is usable and not advertised — and request the
link over the API, which is both honest and the only way to see it in this
stack.

### D18 — the group-crossing section names the wrong group, three times

The longest section of the tutorial, "See a group cross", is wrong about which
group does the crossing. Read live from the running relying party:

```text
provider: demo-idp | driver: plone-identity
  groupmap: {'content-site-editors': 'Reviewers'}
```

Dana is in **both** `site-editors` and `content-site-editors`
(`setuphandlers/idpcontent/content/6b157a7d.../data.json`, `group_ids`). Only
`content-site-editors` is mapped.

Three sentences are therefore false:

| Tutorial says | Actually |
|---|---|
| "configured with one row, `site-editors` to `Reviewers`" | the row is `content-site-editors` to `Reviewers` |
| "also has `foundation-members` and `content-site-editors`, and neither of them appears here" | `content-site-editors` is precisely the one that appears |
| "remove Dana from `site-editors` … She is no longer in `Reviewers`" | removing that group changes nothing; the reader concludes the feature is broken |

The third is the damaging one: a reader who follows it exactly performs a
revocation that correctly does nothing, and the tutorial tells them to expect a
change. The feature works; the instruction points at the wrong group.

Fix in Phase 5 against the live values, not against the profile XML — and the
profile is the better source than the prose either way.

### D15 — `make demo-stack-start` prints a warning twice

```text
level=warning msg="The \"VOLTO_VERSION\" variable is not set. Defaulting to a blank string."
```

Printed twice on every compose command. The tutorial says "The first run builds
images and takes a few minutes. When it finishes, both sites are listening", and
shows no output, so a reader meets an unexplained warning at step one. Either set
a default in the compose file or say in the tutorial that it is harmless.

### D16 — the tutorial's own layer table is wrong

`| http://id.localhost | The identity provider | core, profile, and server |`

There is no `profile` layer. See `AUDIT-CODE.md` §8. This is plan defect D2,
confirmed against the running stack rather than only against the source.

### D17 — the magic-link prose describes the old mail arrangement

> `Products.PrintingMailHost` is switched on instead

It is no longer switched on by an environment variable in the compose file; the
demo package loads it on startup (commit `8c5e1c9`). The sentence is close enough
to true to mislead rather than to fail, which is the kind that survives longest.

## Steps not verified in this pass

These need a browser, and are deferred to the Playwright harness (see
`HUMAN-ACTIONS.md`, and the screenshot decision):

- the consent screen appearing, being approved, and not appearing the second time
- `/identities` listing the federated identity
- the group crossing from `site-editors` to `Reviewers`, and being revoked
- `/controlpanel/identity-clients` and `/applications`
- withdrawing consent and seeing the screen return

Nothing in the API-level checks contradicts any of them. They are marked not
verified rather than assumed, and the harness that captures screenshots will
drive exactly this sequence, which is why building it verifies the tutorial as a
side effect.

## Gate 0 status

| Gate 0 requirement | Status |
|---|---|
| `AUDIT.md` exists | yes |
| `AUDIT-CODE.md` exists | yes |
| Tutorial run log exists | this file |
| Every `[H]` converted to `[V]` or `[V: false]` | yes — `AUDIT-CODE.md` §13 |
| Docs build passes with `-W` | yes, zero warnings |
| `linkcheck` | clean, empty report |

Gate 0 passes.

One plan item was **retired as stale** rather than fixed: item 1.2 describes a
broken anchor `#configure-provider-verification` in `configure-a-provider.md`.
The label is defined at line 106 of that file and referenced with `{ref}` at line
209; it resolves. The only other in-page anchor in the documentation,
`user-content.md:66`, points at a heading in its own file at line 115 and also
resolves. There is no anchor defect to fix.

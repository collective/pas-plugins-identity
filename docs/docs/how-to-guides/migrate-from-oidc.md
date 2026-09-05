---
myst:
  html_meta:
    "description": "Move a site from pas.plugins.oidc to pas.plugins.identity, and understand when the migration refuses."
    "property=og:description": "Move a site from pas.plugins.oidc to pas.plugins.identity, and understand when the migration refuses."
    "property=og:title": "How to migrate from pas.plugins.oidc"
---

(how-to-migrate-from-the-legacy-plugin)=

# How to migrate from `pas.plugins.oidc`

Move a site from `pas.plugins.oidc` to this package—and find out whether your
site can move at all.

This migration is harder than the authomatic one, and it may refuse.

`pas.plugins.oidc` stores no identity mapping. It derives a user id from a
configurable claim, creates a `source_users` account with that id, and keeps
nothing else. So the migration has to reconstruct a join that was never written
down.

```{important}
This is a hard cutover. Running the old plugin and this one side by side is not
supported and not tested.
```

## Steps

1. **Check `user_property_as_userid` on the old plugin.** This decides whether
   you can migrate at all.

   | Value | Outcome |
   |---|---|
   | `sub`, the default | The Plone user id **is** the subject, so the join reconstructs exactly. Continue. |
   | anything else, usually `email` | The `sub` was never written down and cannot be recovered. **The migration refuses.** |

   A site in the second row should stay on `pas.plugins.oidc` for now. The
   migration refuses rather than producing a plausible-looking wrong join.

2. **Back up the database.**

3. **Decide which accounts are yours.** Nothing marks an account as
   OIDC-created, so the migration cannot tell one from an account an
   administrator typed in. It will not guess.

   If the site used OIDC exclusively, take every `source_users` account:

   ```python
   from pas.plugins.identity.migration import oidc

   report = oidc.migrate()
   ```

   If the site has a mix, name the user ids instead:

   ```python
   report = oidc.migrate(userids=["sub-alice", "sub-bob"])
   ```

   ```{warning}
   The default claims **every** `source_users` account as an OIDC identity. On a
   mixed site that is wrong, and it is wrong in a way that is easy to miss.

   The dry-run report lists exactly which user ids would be claimed. That is how
   you find out before it matters.
   ```

4. **Read the dry run.** `migrate()` writes nothing unless you tell it to.

   ```python
   print(report.as_dict())
   ```

   Check `refused` first: when it is true, nothing was done and nothing will be
   until you deal with the reason in `refusals`. Then read `identities` and
   confirm every user id listed is one you meant to claim.

   Every field a report carries is in {doc}`/reference/migration-reports`.

5. **Run the migration.**

   ```python
   report = oidc.migrate(dry_run=False)
   ```

   Or, for a mixed site:

   ```python
   report = oidc.migrate(userids=["sub-alice", "sub-bob"], dry_run=False)
   ```

   It is idempotent. Running it twice does nothing the second time.

6. **Update the redirect URI at the provider** to the callback URL you set during
   {doc}`install`, by default `https://www.example.com/login-identity`.

7. **Remove the old plugin.**

## Verify

1. Sign in with the provider.
2. Confirm you land on the account you had before, not a new one.
3. Check the audit log for an `authenticated` entry.

If a sign-in fails, read the audit log first—see {doc}`read-the-audit-log` and
{doc}`troubleshoot`.

## What comes across

Provider configuration translates cleanly, because it all lives on the plugin:
issuer, client id, client secret, scope, and title.

## Next steps

- {doc}`/reference/migration-reports`—every field and refusal
- {doc}`export-and-import-principals`—the alternative when the old site is elsewhere
- {doc}`troubleshoot`—if somebody lands on a new account

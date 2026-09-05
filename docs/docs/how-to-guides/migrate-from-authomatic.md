---
myst:
  html_meta:
    "description": "Move a site from pas.plugins.authomatic to pas.plugins.identity, keeping every user id."
    "property=og:description": "Move a site from pas.plugins.authomatic to pas.plugins.identity, keeping every user id."
    "property=og:title": "How to migrate from pas.plugins.authomatic"
---

(how-to-migrate-from-authomatic)=

# How to migrate from `pas.plugins.authomatic`

Move a site from `pas.plugins.authomatic` to this package, keeping every user id.

`pas.plugins.authomatic` already stores exactly the mapping this package stores:
`(provider, subject)` to userid. The migration reads that mapping rather than
reconstructing it, which makes this the straightforward migration of the two.

```{important}
This is a hard cutover. Running the old plugin and this one side by side is not
supported and not tested. Two plugins both claiming to authenticate the same
people is how one person ends up with two accounts.
```

Both plugins must be installed in the same instance. If the old site is somewhere
this instance cannot reach, use {doc}`export-and-import-principals` instead.

## Steps

1. **Back up the database.** This rewrites the site's principals.

2. **Run the dry run.** `migrate()` writes nothing unless you tell it to.

   ```python
   from pas.plugins.identity.migration import authomatic

   report = authomatic.migrate()
   print(report.as_dict())
   ```

3. **Read the report.** Check `refused` first: when it is true, nothing was done
   and nothing will be until you deal with the reason in `refusals`.

   Every field a report carries is in {doc}`/reference/migration-reports`.

4. **Run the migration.**

   ```python
   report = authomatic.migrate(dry_run=False)
   ```

   It is idempotent. Running it twice does nothing the second time.

5. **Update the redirect URI at every provider.**

   authomatic's callback was `<portal_url>/authomatic-handler/<provider>`. This
   package uses a frontend route instead—the callback URL you set during
   {doc}`install`, by default:

   ```text
   https://www.example.com/login-identity
   ```

6. **Remove the old plugin**, so nothing else claims to authenticate the same
   people.

## Verify

1. Sign in with each configured provider.
2. Confirm you land on the account you had before, not a new one.
3. Check the audit log has an `authenticated` entry, not `identity-linked`
   followed by a new account.

If a sign-in fails, read the audit log first—see {doc}`read-the-audit-log` and
{doc}`troubleshoot`.

## What comes across, and what does not

| Carried over | Left behind |
|---|---|
| User ids, verbatim | Property maps |
| Provider credentials | Class references |
| The `(provider, subject)` mapping | authomatic's own scope vocabulary |
| | Passwords |

**User ids come across verbatim**, so every local role, sharing setting, and
piece of content ownership keeps pointing at the right person. That holds
whichever of authomatic's four user-id factories the site used, because they all
produce opaque strings that are already stored.

**Provider credentials are carried over**, because without them nothing can sign
in.

**The rest of authomatic's per-provider configuration is deliberately left
behind.** Translating it silently would produce a provider that looks configured
and behaves differently.

**Passwords are not carried over.** authomatic gives each user a random secret and
uses it as a password, so it is not something a person knows or could type.

## Why the old callback URL is not served

Serving `<portal_url>/authomatic-handler/<provider>` as well was considered and
rejected. It would mean a second permanent entry point into the sign-in flow,
with its own open-redirect and session-binding surface, to save a one-time
configuration change.

## Next steps

- {doc}`/reference/migration-reports`—every field and refusal
- {doc}`configure-a-provider`—checking the migrated providers
- {doc}`troubleshoot`—if somebody lands on a new account

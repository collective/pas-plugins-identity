---
myst:
  html_meta:
    "description": "Move a site from pas.plugins.authomatic to pas.plugins.identity, keeping every user id."
    "property=og:description": "Move a site from pas.plugins.authomatic to pas.plugins.identity, keeping every user id."
    "property=og:title": "How to migrate from pas.plugins.authomatic"
---

(how-to-migrate-from-authomatic)=

# How to migrate from `pas.plugins.authomatic`

This guide shows you how to move a site from `pas.plugins.authomatic` to this package.

`pas.plugins.authomatic` already stores exactly the mapping this package stores, which is `(provider, subject)` to userid.
The migration reads that mapping rather than reconstructing it, so this is the straightforward migration of the two.

```{important}
This is a hard cutover.
Running the old plugin and this one side by side is not supported and not tested.
Two plugins both claiming to authenticate the same people is how one person ends up with two accounts.
```

## Run the dry run

`migrate()` writes nothing unless you tell it to.

```python
from pas.plugins.identity.migration import authomatic

report = authomatic.migrate()
print(report.as_dict())
```

Read the report before you go further.
Check `refused` first: when it is true, nothing was done and nothing will be until you deal with the reason in `refusals`.

For every field a report carries, see {doc}`/reference/migration-reports`.

## Run the migration

```python
report = authomatic.migrate(dry_run=False)
```

The migration is idempotent.
Running it twice does nothing the second time.

## Know what comes across

User ids come across verbatim, so every local role, sharing setting, and piece of content ownership keeps pointing at the right person.
That holds whichever of authomatic's four user-id factories the site used, because they all produce opaque strings that are already stored.

Provider credentials are carried over, because without them nothing can sign in.

The rest of authomatic's per-provider configuration is deliberately left behind: property maps, class references, and its own scope vocabulary.
Translating that silently would produce a provider that looks configured and behaves differently.

Passwords are not carried over.
authomatic gives each user a random secret and uses it as a password, so it is not something a person knows or could type.

## Update the redirect URI at each provider

authomatic's callback was `<portal_url>/authomatic-handler/<provider>`.
This package uses a frontend route instead.

Update the registered redirect URI at every provider to the callback URL you set during {doc}`install`.

Serving the old URL as well was considered and rejected.
It would mean a second permanent entry point into the sign-in flow, with its own open-redirect and session-binding surface, to save a one-time configuration change.

## Verify

Sign in with each configured provider and confirm you land on the account you had before.
If a sign-in fails, read the audit log.
See {doc}`read-the-audit-log`.

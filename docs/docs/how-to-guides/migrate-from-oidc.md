---
myst:
  html_meta:
    "description": "Move a site from pas.plugins.oidc to pas.plugins.identity, and understand when the migration refuses."
    "property=og:description": "Move a site from pas.plugins.oidc to pas.plugins.identity, and understand when the migration refuses."
    "property=og:title": "How to migrate from pas.plugins.oidc"
---

(how-to-migrate-from-the-legacy-plugin)=

# How to migrate from `pas.plugins.oidc`

This guide shows you how to move a site from `pas.plugins.oidc` to this package, and how to tell whether your site can move at all.

This migration is harder than the authomatic one, and it may refuse.

`pas.plugins.oidc` stores no identity mapping.
It derives a user id from a configurable claim, creates a `source_users` account with that id, and keeps nothing else.
So the migration has to reconstruct a join that was never written down.

```{important}
This is a hard cutover.
Running the old plugin and this one side by side is not supported and not tested.
```

## Check `user_property_as_userid` first

Look at the `user_property_as_userid` setting on the old plugin.

If it is the default `sub`, the Plone user id is the subject, so the join reconstructs exactly and you can continue.

If the site changed it, most likely to `email`, the `sub` was never written down anywhere and cannot be recovered.
The migration refuses rather than producing a plausible-looking wrong join.
Those sites should stay on `pas.plugins.oidc` for now.

## Decide which accounts are yours

Nothing marks an account as OIDC-created, so the migration cannot tell one from an account an administrator typed in.
It will not guess, so you have to choose.

If the site used OIDC exclusively, take every `source_users` account:

```python
from pas.plugins.identity.migration import oidc

report = oidc.migrate()
```

If the site has a mix of OIDC and locally created accounts, name the user ids instead:

```python
report = oidc.migrate(userids=["sub-alice", "sub-bob"])
```

```{warning}
The default claims every `source_users` account as an OIDC identity.
On a mixed site that is wrong.
The dry-run report lists exactly which user ids would be claimed, and it is how you find out before it matters.
```

## Read the dry run

`migrate()` writes nothing unless you tell it to.

```python
print(report.as_dict())
```

Check `refused` first.
When it is true, nothing was done and nothing will be until you deal with the reason in `refusals`.
Then read `identities` and confirm that every user id listed is one you meant to claim.

For every field a report carries, see {doc}`/reference/migration-reports`.

## Run the migration

```python
report = oidc.migrate(dry_run=False)
```

Or, for a mixed site:

```python
report = oidc.migrate(userids=["sub-alice", "sub-bob"], dry_run=False)
```

The migration is idempotent.
Running it twice does nothing the second time.

## Know what comes across

Provider configuration translates cleanly, because it all lives on the plugin: issuer, client id, client secret, scope, and title.

## Verify

Sign in with the provider and confirm you land on the account you had before.
If a sign-in fails, read the audit log.
See {doc}`read-the-audit-log`.

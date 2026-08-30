---
myst:
  html_meta:
    "description": "Every field a migration report carries, and what each one means."
    "property=og:description": "Every field a migration report carries, and what each one means."
    "property=og:title": "Migration reports"
---

(reference-migration-reports)=

# Migration reports

Both migrations return a report object.
`report.as_dict()` renders it:

```python
{
    "dry_run": True,
    "refused": False,
    "refusals": [],
    "identities": [["github", "12345", "some-userid"]],
    "providers": ["github"],
    "users": ["some-userid"],
    "skipped": [],
    "counts": {"identities": 1, "providers": 1, "users": 1, "skipped": 0},
}
```

## Fields

`dry_run`
:   Whether the run wrote anything.
    `True` means it did not.

`refused`
:   Whether the migration refused to proceed.
    Check this first.
    When it is `True`, nothing was done and nothing will be until you deal with the reason in `refusals`.

`refusals`
:   Why the migration refused.
    Empty when `refused` is `False`.

`identities`
:   Each identity the migration would claim or did claim, as `[provider, subject, userid]`.

`providers`
:   The provider ids the migration would create or did create.

`users`
:   The people the migration produced.
    On a live run, the migrated userids that have a Profile afterwards; on a dry run, those that would gain one.
    A migrated person is a user, not only a row in the identity store: they are in `@users`, they can be put in a group and granted a role, and none of that waits for their first sign-in.

`skipped`
:   What the migration passed over, and why.

`counts`
:   The lengths of `identities`, `providers`, `users`, and `skipped`.

## Guarantees

Both migrations write through the plugin rather than into the identity store, so the event that mints a Profile is fired for every identity they claim.
Until 2026-08-30 they wrote to the store directly, and a migrated person existed as an identity and as nobody at all: absent from `@users`, unable to be granted a role or added to a group, and invisible altogether once the old plugin was removed.
They appeared at their first login, and not before.

Both migrations are dry-run by default.
You must pass `dry_run=False` to change anything.

Both are idempotent.
Running one twice does nothing the second time.

Both are loud about what they cannot do.
A migration that silently produces a wrong identity join is worse than one that refuses, because the wrong join surfaces months later as somebody signing in to somebody else's account.

```{important}
Both migrations are hard cutovers.
Running the old plugin and this one side by side is not supported and not tested.
```

## The migrations

-   {doc}`/how-to-guides/migrate-from-authomatic`
-   {doc}`/how-to-guides/migrate-from-oidc`

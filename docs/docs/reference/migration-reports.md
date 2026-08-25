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
    "skipped": [],
    "counts": {"identities": 1, "providers": 1, "skipped": 0},
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

`skipped`
:   What the migration passed over, and why.

`counts`
:   The lengths of `identities`, `providers`, and `skipped`.

## Guarantees

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

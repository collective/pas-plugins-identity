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

<!-- source: backend/src/pas/plugins/identity/migration/ -->

| Field | Type | Meaning |
|---|---|---|
| `dry_run` | `bool` | Whether the run wrote anything. `True` means it did not. |
| `refused` | `bool` | **Check this first.** `True` means nothing was done and nothing will be until you deal with `refusals`. |
| `refusals` | `list` | Why the migration refused. Empty when `refused` is `False`. |
| `identities` | `list` | Each identity claimed, or that would be claimed, as `[provider, subject, userid]`. |
| `providers` | `list` | The provider ids created, or that would be created. |
| `users` | `list` | The migrated userids that have a profile afterwards; on a dry run, those that would gain one. |
| `skipped` | `list` | What the migration passed over, and why. |
| `counts` | `dict` | The lengths of `identities`, `providers`, `users` and `skipped`. |

## Guarantees

| Guarantee | What it means |
|---|---|
| They produce **people**, not only identities | They write through the plugin rather than into the identity store, so the event that mints a profile fires for every identity they claim. A migrated person is in `@users`, can be granted a role and added to a group, and none of it waits for their first sign-in. |
| Dry run by default | You must pass `dry_run=False` to change anything. |
| Idempotent | Running one twice does nothing the second time. |
| Loud about what they cannot do | A migration that silently produces a wrong identity join surfaces months later as somebody signing in to somebody else's account. |

```{important}
Both migrations are hard cutovers. Running the old plugin and this one side by
side is not supported and not tested.
```

## Related

- {doc}`/how-to-guides/migrate-from-authomatic`
- {doc}`/how-to-guides/migrate-from-oidc`
- {doc}`principal-documents`—the file format one of them consumes
- {doc}`profiles-and-groups`—what a migrated person ends up as

# Migrating from another package

Two migrations, one from `pas.plugins.authomatic` and one from
`pas.plugins.oidc`. Both are **hard cutovers**: running the old plugin and this
one side by side is not supported and not tested. Two plugins both claiming to
authenticate the same people is how one human ends up with two accounts.

Both are also:

**Dry-run by default.** `migrate()` reports what it would do and writes
nothing. You have to pass `dry_run=False` to change anything. Read the report
first — for the OIDC migration especially, it is the only thing that will tell
you it is about to claim an account it should not.

**Idempotent.** Running twice does nothing the second time.

**Loud about what they cannot do.** A migration that silently produces a wrong
identity join is worse than one that refuses, because the wrong join surfaces
months later as somebody logging into somebody else's account.

## From `pas.plugins.authomatic`

The straightforward one. authomatic already stores exactly the mapping this
package stores — `(provider, subject) -> userid` — so the migration reads it
rather than reconstructing it.

```python
from pas.plugins.identity.migration import authomatic

report = authomatic.migrate()          # dry run
print(report.as_dict())

report = authomatic.migrate(dry_run=False)
```

User ids come across **verbatim**, so every local role, sharing setting and
piece of content ownership keeps pointing at the right person. That holds
whichever of authomatic's four user-id factories the site used: they all
produce opaque strings that are already stored.

Provider credentials are carried over, because without them nothing can log
in. The rest of authomatic's per-provider configuration — property maps, class
references, its own scope vocabulary — is deliberately left behind. Translating
it silently would produce a provider that looks configured and behaves
differently.

Passwords are not carried over. authomatic gives each user a random secret and
uses it as a password; it is not something a human knows or could type.

### After the migration

Update the redirect URI at each provider. authomatic's callback was
`<portal_url>/authomatic-handler/<provider>`; this package uses a frontend
route. Serving the old URL as well was considered and rejected — it would mean
a second permanent entry point into the login flow, with its own open-redirect
and session-binding surface, to save a one-time configuration change.

## From `pas.plugins.oidc`

Harder, and it may refuse.

`pas.plugins.oidc` stores **no identity mapping at all**. It derives a user id
from a configurable claim, creates a `source_users` account with that id, and
keeps nothing else.

### It refuses a non-default `user_property_as_userid`

When the setting is its default `sub`, the Plone user id *is* the subject, so
the join reconstructs exactly.

When a site changed it — to `email`, most likely — the `sub` was never written
down anywhere and cannot be recovered. The migration refuses rather than
producing a plausible-looking wrong join. Those sites should stay on
`pas.plugins.oidc` for now.

### It cannot tell which accounts are yours

Nothing marks an account as OIDC-created, so the migration cannot distinguish
one from an account an administrator typed in. It will not guess:

```python
from pas.plugins.identity.migration import oidc

# Every source_users account. Right for a site that used OIDC exclusively.
report = oidc.migrate()

# Or name them, for a mixed site.
report = oidc.migrate(userids=["sub-alice", "sub-bob"])
```

:::{warning}
The default claims **every** `source_users` account as an OIDC identity. On a
site with a mix of OIDC and locally created accounts that is wrong, and the
dry-run report — which lists exactly which user ids would be claimed — is how
you find out before it matters.
:::

Provider configuration translates cleanly, since it is all on the plugin:
issuer, client id, client secret, scope and title.

## Reading a report

```python
report.as_dict()
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

`refused` is the field to check first. When it is true, nothing was done and
nothing will be until the reason in `refusals` is dealt with.

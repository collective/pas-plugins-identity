---
myst:
  html_meta:
    "description": "Export a site's users, groups and identities as JSON, and import them into another site."
    "property=og:description": "Export a site's users, groups and identities as JSON, and import them into another site."
    "property=og:title": "How to export and import principals"
    "keywords": "Plone, pas.plugins.identity, export, import, backup, migration"
---

(how-to-export-and-import-principals)=

# How to export and import principals

Move a site's users, groups and identity join between sites as a single JSON
file.

Use it to take a copy of your accounts that outlives the instance, to seed a new
site from an old one, or to import a `pas.plugins.authomatic` site that is not in
this instance and cannot be.

If both plugins are installed in the same instance and the site is staying where
it is, use {doc}`migrate-from-authomatic` instead.

## Export a site

1. Run the exporter:

   ```shell
   identity-exporter etc/zope.conf plone var/principals.json
   ```

   The arguments are a `zope.conf`, the site id or path, and the file to
   write—the same shape `plone-exporter` uses.

2. Read what it reports:

   ```console
    Wrote /srv/plone/var/principals.json
    - 1284 users
    - 17 groups
    - 1509 identities
   ```

An export writes nothing to the site, so it is safe to run against production.

```{note}
Identity records belonging to a userid with no Profile are not exported, and are
named in the log. Deleting a user leaves its identities behind on purpose; see
{doc}`/reference/user-content`.
```

## Import into another site

1. **Dry run first.**

   ```shell
   identity-importer etc/zope.conf plone var/principals.json --dry-run
   ```

   A dry run writes nothing at all. It does not write and then roll back, so
   nothing can be left half applied.

2. **Read what it reports.**

   ```console
    Reading /srv/plone/var/principals.json into the Plone site at /plone
    - dry run -- nothing was written
    - 1284 users
    - 17 groups
    - 1509 identities
    - skipped: identity github:1234567: already linked to alice, not to bob
   ```

   Anything under `skipped` is a record that will not land. A `refused:` line
   means **nothing** will land, and names the reason.

3. **Import.**

   ```shell
   identity-importer etc/zope.conf plone var/principals.json
   ```

   The import commits once, at the end, after the whole document has been
   applied, so a failure part way through leaves the site as it was. It exits
   non-zero when it refuses, so a shell script can act on that.

Running the same document twice writes the same site: an existing user is
updated rather than duplicated, and an identity already pointing at the right
userid is left alone.

## Import from `pas.plugins.authomatic`

1. Produce the dump on the old site. The format and a working extraction are in
   {ref}`reference-authomatic-dumps`.

2. **Configure the providers in the target site first**, under the same names.
   See the warning below.

3. Dry run, then import:

   ```shell
   identity-importer etc/zope.conf plone var/authomatic.json --from-authomatic --dry-run
   identity-importer etc/zope.conf plone var/authomatic.json --from-authomatic
   ```

```{important}
**Name the provider exactly as `pas.plugins.authomatic` named it.**

Its provider *name*—the key in that package's `json_config`—is the left half
of every identity key in the dump, and this package's provider *id* is what a
login presents as the right one. They have to be the same string: a dump whose
identities say `"provider": "google"` needs a provider whose id is `google`, not
`google-workspace` and not `Google`.

The importer checks this and refuses before writing anything, naming what is
missing and what is configured—including when the difference is only one of
case.

Without the check the mistake is invisible: the import reports success, and then
every migrated person signs in and is handed a brand-new account beside the one
waiting for them, while the migrated Profile keeps their name and their groups
and belongs to nobody who can sign in.
```

### Import before configuring the providers

```shell
identity-importer etc/zope.conf plone var/authomatic.json --from-authomatic --allow-unknown-providers
```

The identities are written either way, so the join starts working the moment a
provider is configured under the right name. The flag only turns off the check
that the name is one this site knows.

### Arrive with verified addresses

If the people in the dump should arrive with verified addresses, and this site
does not otherwise trust that provider at a login, ask for it per run:

```shell
identity-importer etc/zope.conf plone var/authomatic.json --from-authomatic --trust-verified-emails
```

```{warning}
Do not switch `trust_email_verification` on to get the same effect and switch it
off afterwards. That changes the site's policy for every login in the meantime,
and nothing tells you if the last step is forgotten.
```

A site that *does* trust the provider at a login needs no flag; the claim is
honoured through the ordinary path.

Provider configuration is not carried in either format, and the client secret is
deliberately not something a document can hold.

## Do it from a script instead

The commands are a thin wrapper over two functions that take and return plain
data. Script a site that does not fit the general case, rather than arguing with
it on a command line:

```python
from pas.plugins.identity.exportimport import export_site, import_site
import json

document = export_site()

# Bring across only the people who have signed in this year.
document["users"] = [
    user for user in document["users"]
    if any(i["last_login"] and i["last_login"] > "2026-01-01" for i in user["identities"])
]

result = import_site(document, dry_run=True)
print(json.dumps(result.as_dict(), indent=2))
```

`export_site()` returns the document as a `dict`, and `import_site()` returns a
result carrying `users`, `groups`, `identities`, `skipped` and `refusals`.

```{important}
Both functions act on the site that is currently active, and the import needs
`Manager`. Running them from a script means setting up a site and a security
context yourself, which is what the console commands do for you.
```

## Verify

1. The importer's summary counts match the exporter's.
2. `skipped` is empty, or every entry in it is one you expected.
3. A migrated person signs in and lands on their existing account.

## Next steps

- {doc}`/reference/principal-documents`—the document format and every refusal
- {doc}`migrate-from-authomatic`—the in-place alternative
- {doc}`troubleshoot`—if a migrated person gets a second account

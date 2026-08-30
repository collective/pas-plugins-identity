Added `pas.plugins.identity.exportimport`: a site's users, groups and identity join as a single JSON file, and the same file back into a site.

`pas.plugins.identity.migration` moves a site in place, with both plugins installed in one instance. It cannot help when the old site is a database you were handed, when the new site is somewhere else, or when what you want is a copy of your accounts that outlives the instance. This is for those.

Two console scripts, taking the same `zope.conf` and site arguments as `plone-exporter` and `plone-importer`:

```shell
identity-exporter etc/zope.conf plone var/principals.json
identity-importer etc/zope.conf plone var/principals.json --dry-run
identity-importer etc/zope.conf plone var/authomatic.json --from-authomatic
```

Both are a thin wrapper over `export_site()` and `import_site()`, which take and return plain data, so anything the commands do can be scripted.

Migrating from `pas.plugins.authomatic` offline is the ordinary import: a dump extracted from the old site is converted into a document and read by the same importer, so there is one importer to get right rather than two. The dump format and a working extraction are documented; the script is not shipped, because it has to run where that package is installed.

The userid travels verbatim in every direction. Every local role, ownership and sharing entry in a site is written against it, so an import that minted new ids would produce a site full of content belonging to nobody, silently.

No passwords, no client secrets and no audit entries are in the format at all, in either direction — a document is a file that gets copied around, and the one thing it must never be is a way in. A refusal stops the whole run and writes nothing; a single bad record is skipped and reported, so one identity already linked to somebody else does not stop the other nine hundred. A dry run never attempts the write. @ericof

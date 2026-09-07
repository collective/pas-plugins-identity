---
myst:
  html_meta:
    "description": "Add an index or a metadata column to the dedicated user catalog with GenericSetup."
    "property=og:description": "Add an index or a metadata column to the dedicated user catalog with GenericSetup."
    "property=og:title": "Add an index to the user catalog"
    "keywords": "Plone, pas.plugins.identity, catalog, index, metadata, GenericSetup"
---

(howto-add-a-catalog-index)=

# Add an index to the user catalog

<!-- source: backend/src/pas/plugins/identity/profiles/default/identity-catalog.xml -->
<!-- source: backend/src/pas/plugins/identity/setuphandlers/catalogxml.py -->
<!-- source: backend/src/pas/plugins/identity/core/indexers/__init__.py -->

The user catalog is declared in `profiles/default/identity-catalog.xml` and
applied by the `identity-catalog` GenericSetup step. Adding an index is an edit
to that file.

## Why you would

A **metadata column** is what the PAS property sheet and enumeration read.
Both are served from brains alone, so a field with no column cannot be answered
without waking the Profile object—which is what a property sheet must never do.

An **index** is what lets a query match on the field. Add one when something
looks a principal up by it, rather than reading it off a principal it already
has.

A field a site added through its own behavior gets neither by default.

## Add it

1. Add the entry to `identity-catalog.xml`:

   ```xml
   <index name="nickname" meta_type="FieldIndex">
     <indexed_attr value="nickname"/>
   </index>

   <column value="nickname"/>
   ```

2. If the value is not a plain attribute read—folded, narrowed, or derived—add
   an indexer beside the two in `core/indexers/__init__.py` and register it:

   ```python
   @indexer(IUserProfile)
   def nickname_index(obj: UserProfile) -> str:
       return (obj.nickname or "").casefold()
   ```

   ```xml
   <adapter factory=".nickname_index" name="nickname" />
   ```

   `login` is the worked example: it is case-folded at index time, so every
   caller case-folds at query time too.

3. If it is a **column**, add it to `PROFILE_METADATA` or `GROUP_METADATA` in
   `core/catalog.py`. One schema serves both types, so a column that means
   nothing on the other one is blank there, and those two tuples are what tell
   the consistency check to expect the blank rather than report it as drift.

4. Apply the profile, then rebuild:

   ```shell
   # in the add-ons control panel, or from a script
   portal_setup.runImportStepFromProfile(
       "pas.plugins.identity:default", "identity-catalog"
   )
   ```

```{important}
**Applying the profile does not populate the index.**

The step creates the index empty, and `addColumn` fills existing records with a
default rather than with the value. Every brain reads as blank for the new field
until something reindexes—and a query against an empty index answers "nothing
matched" rather than failing, so the mistake is silent.

Apply `pas.plugins.identity:rebuild-catalog` afterwards. See
{doc}`/how-to-guides/upgrade`.
```

## Remove one

```xml
<index name="nickname" meta_type="FieldIndex" remove="True"/>
<column value="nickname" remove="True"/>
```

Removing an index that is not there is not an error, so a profile carrying this
stays re-runnable.

## Why the file is not called `catalog.xml`

GenericSetup's own `catalog` step resolves its target with
`queryUtility(ICatalogTool)`, which answers `portal_catalog` and nothing else.
It has no notion of a second catalog.

A `catalog.xml` in this package's profile is therefore **not ignored**. It is
read by that step and applied to the site catalog, adding this package's indexes
to `portal_catalog`, silently. The separate filename is what keeps the two
apart, and `IdentityCatalogXMLAdapter` exists to change it—everything else about
reading a `ZCatalog` from XML is inherited from GenericSetup.

## Related

- {doc}`/reference/user-content`—what the catalog holds today
- {doc}`/reference/install-profiles`—the profiles and steps this package ships
- {doc}`upgrade`—when a release changes what the catalog stores

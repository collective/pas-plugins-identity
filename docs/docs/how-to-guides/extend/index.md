---
myst:
  html_meta:
    "description": "Extend pas.plugins.identity from another package: drivers, profile enrichers, claims, catalog indexes, and profile pages."
    "property=og:description": "Extend pas.plugins.identity from another package: drivers, profile enrichers, claims, catalog indexes, and profile pages."
    "property=og:title": "Extend the package"
---

# Extend the package

Add to this package from one of your own, without changing it.

| Guide | Adds |
|---|---|
| {doc}`write-a-driver` | Support for a provider no shipped driver covers |
| {doc}`write-a-profile-enricher` | Profile fields filled from a provider's claims |
| {doc}`serialize-a-claim` | A claim, or a scope, that the server layer releases |
| {doc}`add-a-catalog-index` | An index or a metadata column to the user catalog |
| {doc}`extend-a-profile-page` | Your own component, in a slot on a profile or group page |
| {doc}`edit-a-list-as-a-table` | A table editor, in Volto, for a list field |

## Related

- {doc}`/reference/python-api`—the public Python API
- {doc}`/reference/driver-contract`—what a driver must do
- {doc}`/reference/stability`—what a release may change under you

```{toctree}
:maxdepth: 1
:hidden: true

write-a-driver
write-a-profile-enricher
serialize-a-claim
add-a-catalog-index
extend-a-profile-page
edit-a-list-as-a-table
```

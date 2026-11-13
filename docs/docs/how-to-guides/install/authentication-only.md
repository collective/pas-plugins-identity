---
myst:
  html_meta:
    "description": "Install pas.plugins.identity for sign-in alone, keeping users in Plone's own user folder instead of as content."
    "property=og:description": "Install pas.plugins.identity for sign-in alone, keeping users in Plone's own user folder instead of as content."
    "property=og:title": "Install sign-in without users as content"
---

(how-to-install-authentication-only)=

# Install sign-in without users as content

Install external sign-in on a site that keeps its users in Plone's own user folder, without the `UserProfile` and `UserGroup` content types.

Most sites want the whole add-on, which is what {doc}`backend` installs.
Follow this guide only when the site has a reason to keep its users out of the content tree.

## What the site gets

<!-- source: backend/src/pas/plugins/identity/profiles/core/ -->
<!-- source: backend/src/pas/plugins/identity/core/pas/plugin.py -->

| | With `core` alone |
|---|---|
| Sign-in with external providers, linking, the audit log | Yes |
| The **Identity providers** control panel | Yes, without the Profile settings |
| Where a federated user's account is written | `source_users`, with a random password nobody knows |
| Where the provider's claims are written | The member's properties, through the provider's property map, only into empty properties. A number is written as text; a list, an object or a boolean is not written, and a value a property refuses is logged and skipped |
| Which address becomes the user's `email` | The first one the provider offers |
| Where provider group memberships are written | `source_groups` |
| The {guilabel}`Profile` entry in the user menu | Volto's own personal information form |
| `UserProfile` and `UserGroup` content, and their pages | No |
| The required-information gate and the address confirmation at first sign-in | No |
| `@group-members`, and exporting or importing principals | No |

## Install it

Follow steps 1, 2, 4 and 5 of {doc}`backend` as written.
In step 3, name the `core` profile instead of `default`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<metadata>
  <version>1000</version>
  <dependencies>
    <dependency>profile-pas.plugins.identity:core</dependency>
  </dependencies>
</metadata>
```

`core` is hidden from the add-ons control panel, so `metadata.xml` is where a site asks for it.

```{important}
The add-ons control panel reports `pas.plugins.identity` as not installed on such a site, because it only checks the `default` profile.
Its {guilabel}`Install` button installs `default`, which adds the content types.
Do not press it unless the site is meant to keep its users as content.
```

## Verify

- `acl_users` holds the `identity` plugin, and no `identity_profile` plugin.
- `portal_types` has no `UserProfile` type.
- After a first sign-in with a provider, the new user appears in {menuselection}`Site Setup --> Users`, and their account is in `source_users`.

## Next steps

1. {doc}`/how-to-guides/install/frontend`—the Volto add-on, without which nobody can sign in.
2. {doc}`/how-to-guides/providers/index`—pick the provider you are adding and follow its recipe.
3. {doc}`/reference/install-profiles`—what each profile installs.

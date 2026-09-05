---
myst:
  html_meta:
    "description": "Every field on the provider form, by tab, and which drivers show it."
    "property=og:description": "Every field on the provider form, by tab, and which drivers show it."
    "property=og:title": "The provider form"
---

(reference-provider-form)=

# The provider form

Every field the **Identity providers** control panel shows when you add or edit a
provider, arranged as the form arranges it.

The form is generated from the driver's published schema, so a site that installs
a third-party driver gets that driver's form with no frontend change. Which tabs
appear depends on which driver you picked.

<!-- source: backend/src/pas/plugins/identity/core/drivers/settings.py -->

## Which tabs each driver shows

The form is composed from three sources, which is why the tab list is longer than
the driver's own fieldsets:

1. the fields **every** provider has, from `IProviderRecords`—the first tab,
   titled **Identity**, plus **Style**;
2. the **driver's** own fieldsets, the first titled **Settings** and the rest
   keeping their own names;
3. a **Mapping** tab composed in the frontend, holding the property map and the
   group map.

<!-- source: frontend/packages/volto-identity/src/helpers/providerSchema.ts -->

| Driver | Tabs |
|---|---|
| `email` | Identity, Style, Settings, Mapping |
| `github` | Identity, Style, Settings, Accounts, Mapping |
| `google` | Identity, Style, Settings, Accounts, Mapping |
| `oidc-generic` | Identity, Style, Settings, Accounts, Groups, Profile, Mapping |
| `plone-identity` | Identity, Style, Settings, Accounts, Groups, Profile, Mapping |

A driver that declares no fieldsets gets a single **Settings** tab, which is what
`email` gets and what a third-party driver that never declares one gets.

Driver tab ids are namespaced under `settings-`, because the backend serves a
`default` fieldset on both halves of this form and two tabs with one id renders
only one of them.

```{image} /_static/screens/provider-form-tabs.png
:alt: A provider's edit form, showing the Identity, Style, Settings, Accounts and Mapping tabs
```

## Identity tab

Shown for every driver. The first thing asked, and when adding a provider it also
carries the driver and the provider id.

| Field | Registry key | Type | Default |
|---|---|---|---|
| Title | `title` | `TextLine` | `''` |
| Enabled | `enabled` | `Bool` | `True` |
| Show on the login screen | `show_in_login` | `Bool` | `True` |
| Order | `order` | `Int` | `0` |

`order` is stored rather than derived: records live in a BTree and read back
alphabetically, and this is the order the login buttons appear in.

## Style tab

| Field | Registry key | Type | Default |
|---|---|---|---|
| Icon | `icon` | `Bytes` | `None` |
| Background colour | `background_color` | `TextLine` | `''` |
| Foreground colour | `foreground_color` | `TextLine` | `''` |

None of it changes what the provider does. The icon is sanitized on save—see
{doc}`/concepts/threat-model`.

## Mapping tab

| Field | Registry key | Type | Default |
|---|---|---|---|
| Property map | `propertymap` | `Dict` | `{}` |
| Group map | `groupmap` | `Dict` | `{}` |

Composed in the frontend rather than served as a fieldset. The group map appears
only for a driver that has a group claim.

## Settings tab

The fieldset a driver does not name. How to reach the provider.

| Field | Registry key | Type | Drivers |
|---|---|---|---|
| Client ID | `config.client_id` | `TextLine`, required | all but `email` |
| Client secret | `config.client_secret` | `Password`, required | all but `email` |
| Scope | `config.scope` | `Tuple` | all but `email` |
| Issuer | `config.issuer` | `TextLine`, required | `oidc-generic`, `plone-identity` |
| Token lifetime | `config.token_ttl` | `Int`, default `900` | `email` |
| Rate limit per hour | `config.rate_limit_per_hour` | `Int`, default `5` | `email` |

Leave **Scope** empty to use the driver's own default. `github` has no
**Issuer**, because it is not an OpenID Connect provider.

## Accounts tab

Who the provider's answer makes the person standing here.

| Field | Registry key | Type | Default |
|---|---|---|---|
| User id source | `config.userid_source` | `Choice` | `uuid` |
| Let this provider create accounts | `config.create_user` | `Bool` | on |
| Attach to an existing account with the same verified email | `config.auto_link_by_email` | `Bool` | off |
| This provider's email verification counts | `config.trust_email_verification` | `Bool` | off, except `github` and `google` |
| This provider sends verification flags as text | `config.accept_string_booleans` | `Bool` | off |

Shown for every driver except `email`.

See {doc}`/how-to-guides/link-accounts-by-email` and
{doc}`/how-to-guides/control-account-creation`.

## Groups tab

| Field | Registry key | Type | Default |
|---|---|---|---|
| Groups arrive in the claim | `config.group_claim` | `TextLine` | `groups` for OIDC drivers, empty otherwise |
| Only these groups may sign in | `config.allowed_groups` | `Tuple` | empty |
| Let this provider set group membership | `config.sync_groups` | `Bool` | on |

Shown only for `oidc-generic` and `plone-identity`, the two drivers whose
settings schema is `IOIDCSettings`. `github`, `google` and `email` carry no
groups this package can read, so none of them gets this tab.

See {doc}`/how-to-guides/map-provider-groups`.

## Profile tab

| Field | Registry key | Type | Default |
|---|---|---|---|
| Fetch the picture over HTTP | `config.picture_over_http` | `Bool` | off |

One field, and it still gets a tab rather than trailing after group settings it
has nothing to do with.

## Actions

**Test connection**
: Fetches the provider's discovery document, or validates the static
  configuration for drivers that have no discovery, and reports what it found. It
  clears the discovery cache first. It does not sign anybody in, so it says
  nothing about the client secret, the redirect URI, or the trust switches.

**Delete**
: Removes the provider's configuration. It does **not** delete the identities
  linked through it—those are account data.

## The client secret is write-only

The control panel serializes a stored secret as a mask, never as its value.

- To keep the stored secret, save the form with the mask unchanged.
- To replace it, type the new one over the mask.

```{warning}
Do not clear the field to keep the existing secret. Blanking it sends an empty
string, which is a different instruction, and it destroys the stored secret.
```

## Related

- {doc}`settings`—the same fields as registry records
- {doc}`shipped-drivers`—each driver's defaults
- {doc}`/how-to-guides/configure-a-provider`—the procedure

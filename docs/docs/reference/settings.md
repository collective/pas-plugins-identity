---
myst:
  html_meta:
    "description": "Every registry record pas.plugins.identity reads, with type and default."
    "property=og:description": "Every registry record pas.plugins.identity reads, with type and default."
    "property=og:title": "Settings"
---

(reference-settings)=

# Settings

Every registry record the package reads.

All keys are under the `pas.plugins.identity.` prefix. Configuration lives in the
registry, one record per setting, so a GenericSetup export describes a site field
by field and one setting can be changed without rewriting the rest.

## Site-wide

<!-- source: backend/src/pas/plugins/identity/core/controlpanel/interfaces.py -->

Set by the `pas.plugins.identity:default` profile. Edited in the
**Identity providers** control panel.

| Key | Type | Default | What it does |
|---|---|---|---|
| `callback_url` | `TextLine` | `/login-identity` | The frontend route providers redirect back to. Matches the route the Volto add-on registers. |
| `user_content_type` | `TextLine` | `''` | Content type used for user profiles. |
| `user_container_path` | `TextLine` | `''` | Where profiles are filed. |
| `group_content_type` | `TextLine` | `''` | Content type used for groups. |
| `group_container_path` | `TextLine` | `''` | Where groups are filed. |
| `sync_portraits` | `Bool` | `False` | Fetch a portrait from the provider at sign-in. |
| `portrait_timeout` | `Int` | `5` | Seconds to wait for one. |
| `portrait_max_bytes` | `Int` | `2097152` | Refuse a portrait larger than this. |
| `discovery_timeout` | `Int` | `10` | Seconds to wait for a discovery document. |
| `audit_max_entries` | `Int` | `500` | Entries the built-in log keeps. |
| `audit_max_days` | `Int` | `180` | Days the built-in log keeps. |
| `audit_record_pii` | `Bool` | `False` | Record personally identifying detail in audit entries. |
| `audit_sinks` | `Tuple` | `('plugin',)` | Which audit sinks to write to, in order. See {doc}`audit-log`. |

The four content-type and container records are empty by default and filled in by
the install profile, which points them at this package's own types. See
{doc}`user-content`.

`user_container_path` and `group_container_path` are derived from the container
records in the next section and kept in step with them. Set the container
records; do not set these two by hand.

## Profiles and groups

<!-- source: backend/src/pas/plugins/identity/core/controlpanel/interfaces.py, IProfileSettings -->

Where principals are filed, which of their workflow states count, and what a
profile must carry before its owner is let past the gate.

### Where principals are filed

| Key | Type | Default | What it does |
|---|---|---|---|
| `profile_container_parent` | `TextLine` | `''` | Path of the folder the profile container lives in, relative to the site root. Empty means the site root. |
| `profile_container_id` | `TextLine` | `identity-profiles` | Id of the folder holding user profiles. |
| `profile_container_title` | `TextLine` | `Identity Profiles` | Title used when this package creates the folder. Changing it later does not rename an existing one. |
| `profile_container_type` | `TextLine` | `Folder` | Portal type used when this package creates the folder. |
| `group_container_parent` | `TextLine` | `''` | Same, for groups. Read only when `group_container_id` is set. |
| `group_container_id` | `TextLine` | `''` | Id of the folder holding groups. **Empty means groups are filed with the profiles.** |
| `group_container_title` | `TextLine` | `Groups` | Title used when this package creates the group folder. |
| `group_container_type` | `TextLine` | `Folder` | Portal type used when this package creates the group folder. |

The group records default to the profile container's, so a site that files
principals together sets none of them.

### Which states count

| Key | Type | Default | What it does |
|---|---|---|---|
| `profile_enumeration_states` | `Tuple` | `('incomplete', 'complete')` | Profile workflow states visible to user enumeration and to the properties plugin. |
| `group_enumeration_states` | `Tuple` | `('active',)` | Group workflow states visible to group enumeration and granting membership. |

### The profile gate

| Key | Type | Default | What it does |
|---|---|---|---|
| `enforce_required_profile_fields` | `Bool` | `True` | Redirect a user to their own edit form while their profile is incomplete. |
| `required_profile_fields` | `Tuple` | `()` | Fields a profile must carry to count as complete. Empty means the fields the type itself marks required. |
| `gate_exempt_paths` | `Tuple` | `()` | Extra view names the gate never redirects, matched on the last path segment. |

See {doc}`profiles-and-groups` for what each state means and which routes are
exempt already.

## Server layer

<!-- source: backend/src/pas/plugins/identity/server/interfaces.py, IServerSettings -->

Present only where `pas.plugins.identity.server:default` has been applied.

| Key | Type | Default | What it does |
|---|---|---|---|
| `server_issuer` | `TextLine` | `''` | The URL identifying this authorization server. **Never derived from the portal URL.** |
| `server_consent_url` | `TextLine` | `''` | Where the browser is sent to approve a request. |
| `server_access_token_ttl` | `Int` | `900` | Access token lifetime, in seconds. |
| `server_refresh_token_ttl` | `Int` | `1209600` | Refresh token lifetime, in seconds—14 days. |
| `server_clients` | `Text` | `''` | The client registry. Managed through `@identity-clients`, not by hand. |
| `server_signing_keys` | `Text` | `''` | The signing key ring. Managed through `@identity-keys`, not by hand. |

Only the two lifetimes are written by the install profile. `server_clients` and
`server_issuer` are deliberately left out, because an empty `<value>` imports as
`None` while omitting the key takes the empty string the schema field declares.
A site with no clients and no issuer is the correct initial state: the server
signs nothing until it is told what it is called.

Set `server_issuer` yourself. See {doc}`/concepts/federation` for why it is
configured rather than derived.

The two defaults are chosen, not arbitrary:

- **900 seconds** for an access token. There is no denylist, so this doubles as
  the worst case between revoking a client and the last token minted for it
  expiring.
- **14 days** for a refresh token. They rotate on every use, so this is how long
  a client may stay away before a person has to sign in again—long enough that
  a daily integration never sees a login page, short enough that an abandoned one
  stops working inside a sprint.

## Per provider

Pattern:

```text
pas.plugins.identity.providers.<provider_id>.<field>
```

`<field>` is a field of that provider's driver settings schema. Which fields
exist, and what type each one is, comes from the driver at runtime.

Provider records belong to no interface—each carries its own field type. That
is why a GenericSetup profile writing them needs a `field` element per record
unless it names an interface that declares them.

### Fields every provider has

<!-- source: backend/src/pas/plugins/identity/core/controlpanel/interfaces.py, IProviderRecords -->

| Key | Type | Default | What it does |
|---|---|---|---|
| `driver` | `TextLine` | `''` | Which driver this provider uses. |
| `title` | `TextLine` | `''` | What the login button says. |
| `enabled` | `Bool` | `True` | Whether the provider works at all. |
| `show_in_login` | `Bool` | `True` | Whether the login page offers a button for it. |
| `icon` | `Bytes` | `None` | An SVG document, sanitized on save. |
| `background_color` | `TextLine` | `''` | Button background, such as `#24292f`. |
| `foreground_color` | `TextLine` | `''` | Button text colour. |
| `order` | `Int` | `0` | Position among the buttons. |
| `propertymap` | `Dict` | `{}` | Claim path → Plone property. |
| `groupmap` | `Dict` | `{}` | Provider group name → local group id. |

Both default to `True`, so a provider added through the API without saying
otherwise is enabled and shown.

`enabled` and `show_in_login` are different questions. An enabled provider that
is not shown still signs people in and is still linkable from a user's own
sign-in methods page; it has no button.

### Fields from the driver

Under `pas.plugins.identity.providers.<id>.config.<field>`.

#### Every OAuth2 driver—`IOAuth2Settings`

<!-- source: backend/src/pas/plugins/identity/core/drivers/settings.py -->

| Field | Type | Required | Default | Tab |
|---|---|---|---|---|
| `client_id` | `TextLine` | yes |—| Settings |
| `client_secret` | `Password` | yes |—| Settings |
| `scope` | `Tuple` | no | `()` | Settings |
| `userid_source` | `Choice` | no | `'uuid'` | Accounts |
| `create_user` | `Bool` | no | `True` | Accounts |
| `auto_link_by_email` | `Bool` | no | `False` | Accounts |
| `trust_email_verification` | `Bool` | no | `False` | Accounts |
| `accept_string_booleans` | `Bool` | no | `False` | Accounts |

An empty `scope` means the driver's own default is used. See
{doc}`shipped-drivers`.

#### OpenID Connect drivers add—`IOIDCSettings`

| Field | Type | Required | Default | Tab |
|---|---|---|---|---|
| `issuer` | `TextLine` | yes |—| Settings |
| `group_claim` | `TextLine` | no | `''` | Groups |
| `allowed_groups` | `Tuple` | no | `()` | Groups |
| `sync_groups` | `Bool` | no | `True` | Groups |
| `picture_over_http` | `Bool` | no | `False` | Profile |

Applies to `oidc-generic` and `plone-identity`.

#### The magic-link driver—`IEmailSettings`

| Field | Type | Required | Default | Tab |
|---|---|---|---|---|
| `token_ttl` | `Int` | no | `900` | Settings |
| `rate_limit_per_hour` | `Int` | no | `5` | Settings |

`token_ttl` is a ceiling below 15 minutes, not above it: a larger value does not
extend the token's life past 15 minutes.

#### GitHub—`IGitHubSettings`

Inherits `IOAuth2Settings` and adds no fields. There is no `issuer`: GitHub is
not an OpenID Connect provider and the endpoints are built into the driver.

## Secrets are not exported

A GenericSetup export omits client secrets, so an export of your provider
configuration is not enough to rebuild a working site. Secrets travel separately.

See {doc}`/concepts/secrets`.

## Related

- {doc}`provider-form`—the same fields, arranged as the control panel shows them
- {doc}`shipped-drivers`—each driver's defaults
- {doc}`install-profiles`—which profile writes what
- {doc}`/how-to-guides/configure-a-provider`—setting them

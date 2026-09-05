# AUDIT-CODE

Working file, not published. Everything here was read from the source tree on
2026-09-05, at commit `811e213` plus the `docs-update` branch. It is the source
of truth for Phase 3 reference tables. Nothing in it came from existing prose.

Regenerate the introspected parts with the scripts named beside each table.

---

## 1. REST API services

All registered through `plone.restapi`. Source: `**/services/**/configure.zcml`.

**Every service is registered with `permission="zope2.View"`.** Authorization is
performed inside the service class, not by the ZCML registration. This is a fact
worth stating in `reference/endpoints.md`: reading the ZCML alone understates
what a caller needs.

### Core layer

<!-- source: backend/src/pas/plugins/identity/core/services/*/configure.zcml -->

| Method | Name | Factory |
|---|---|---|
| GET | `@my-profile` | `myprofile.MyProfileGet` |
| GET | `@types` | `types.ProfileTypesGet` |
| PATCH | `@users` | `users.ProfileUsersPatch` |
| GET | `@portrait` | `users.ProfilePortraitGet` |
| POST | `@magic-link` | `magiclink.post.MagicLinkSend` |
| POST | `@magic-link-confirm` | `magiclink.confirm.MagicLinkConfirm` |
| GET | `@group-members` | `groups.get.GroupMembersGet` |
| GET | `@identity-drivers` | `providers.drivers.DriversGet` |
| GET | `@identity-providers` | `providers.get.ProvidersGet` |
| POST | `@identity-providers` | `providers.post.ProvidersPost` |
| PATCH | `@identity-providers` | `providers.patch.ProvidersPatch` |
| DELETE | `@identity-providers` | `providers.delete.ProvidersDelete` |
| GET | `@user-account` | `useraccount.get.UserAccountGet` |
| GET | `@identities` | `identities.get.IdentitiesGet` |
| POST | `@identities` | `identities.post.IdentitiesPost` |
| DELETE | `@identities` | `identities.delete.IdentitiesDelete` |
| GET | `@login-providers` | `login.get.LoginProviders` (also an expander) |
| POST | `@identity-callback` | `callback.post.IdentityCallback` |
| GET | `@audit-log` | `auditlog.get.AuditLogGet` |

`@login-providers` is registered **both** as a service and as a `plone.restapi`
expander (`login.expander.LoginProviders`), so it appears inline on responses
that ask for it as well as at its own path.

### Server layer

Only present when the `server` profile has been applied — these are bound to
`IIdentityServerLayer`.

<!-- source: backend/src/pas/plugins/identity/server/services/configure.zcml -->

| Method | Name | Factory |
|---|---|---|
| GET | `@identity-clients` | `clients.get.ClientsGet` |
| POST | `@identity-clients` | `clients.post.ClientsPost` |
| PATCH | `@identity-clients` | `clients.patch.ClientsPatch` |
| DELETE | `@identity-clients` | `clients.delete.ClientsDelete` |
| GET | `@identity-keys` | `keys.KeysGet` |
| POST | `@identity-keys` | `keys.KeysPost` |
| GET | `@oauth-consent` | `consent.get.ConsentGet` |
| GET | `@oauth-grants` | `grants.get.GrantsGet` |
| DELETE | `@oauth-grants` | `grants.delete.GrantsDelete` |

## 2. Browser views

<!-- source: backend/src/pas/plugins/identity/{core,server}/browser/configure.zcml -->

| Path | Class | Layer | ZCML permission |
|---|---|---|---|
| `@@identity-controlpanel` | `core.controlpanel.view.IdentitySettingsControlPanel` | core | (control panel) |
| `@@backchannel-logout` | `core.browser.logout.BackChannelLogoutView` | core | see source |
| `@@oauth-authorize` | `server.browser.authorize.AuthorizeView` | `IIdentityServerLayer` | `zope2.Public` |
| `@@oauth-token` | `server.browser.token.TokenView` | `IIdentityServerLayer` | `zope2.Public` |
| `/.well-known/<document>` | `server.browser.discovery.WellKnownView` | `IIdentityServerLayer` | see source |
| `@@oauth-jwks` | `server.browser.discovery.JWKSView` | `IIdentityServerLayer` | see source |
| `@@oauth-userinfo` | `server.browser.userinfo.UserInfoView` | `IIdentityServerLayer` | see source |

`.well-known` is registered as a **view name** with a traversal stub, because the
path segment contains a dot. The document name is traversed into it, so the
published path is `/.well-known/openid-configuration`
(`server/browser/discovery.py`, `WELL_KNOWN` / `DISCOVERY_DOCUMENT`). A bare
`/.well-known/` is refused.

**The only page template in the whole add-on** is
`server/browser/templates/consent.pt`. See §8.

## 3. Drivers

Introspected, so inherited attributes are resolved.
<!-- regenerate: scratchpad/introspect_drivers.py -->
<!-- source: backend/src/pas/plugins/identity/core/drivers/*.py -->

| `driver_id` | `title` | `settings_schema` | `default_scope` | `subject_keys` | `default_group_claim` | trusts email verification |
|---|---|---|---|---|---|---|
| `email` | Email | `IEmailSettings` | `()` | `('email',)` | — | no |
| `github` | GitHub | `IGitHubSettings` | `('read:user', 'user:email')` | `('id', 'node_id')` | — | **yes** |
| `google` | Google | `IOAuth2Settings` | `('openid', 'email', 'profile')` | `('sub',)` | — | **yes** |
| `oidc-generic` | OpenID Connect | `IOIDCSettings` | `('openid', 'email', 'profile')` | `('sub',)` | `groups` | no |
| `plone-identity` | Plone site | `IPloneIdentitySettings` | `('openid', 'email', 'profile', 'address')` | `('sub',)` | `groups` | no |

Property maps (`default_propertymap`, claim → Plone property):

| driver | map |
|---|---|
| `email` | `email → email` |
| `github` | `email → email`, `fullname → fullname` |
| `google` | `email → email`, `fullname → fullname` |
| `oidc-generic` | `email → email`, `fullname → fullname` |
| `plone-identity` | `email → email`, `fullname → fullname`, `website → home_page`, `description → description`, `address.formatted → location`, `picture_url → portrait` |

`default_groupmap` is `{}` for every shipped driver.

Base class defaults (`core/drivers/base.py`): `settings_schema = IOAuth2Settings`,
`default_scope = ()`, `subject_keys = ('sub',)`, `default_group_claim = ''`,
`default_trust_email_verification = False`.

## 4. Settings schemas

Introspected. `required` and `default` are the field's own, not the registry's.
<!-- regenerate: scratchpad/introspect_settings.py and scratchpad/fieldsets.py -->
<!-- source: backend/src/pas/plugins/identity/core/drivers/settings.py -->

### `IOAuth2Settings` — the base every OAuth2 driver inherits

| Field | Type | Required | Default | Fieldset |
|---|---|---|---|---|
| `client_id` | TextLine | yes | — | Settings |
| `client_secret` | Password | yes | — | Settings |
| `scope` | Tuple | no | `()` | Settings |
| `userid_source` | Choice | no | `'uuid'` | Accounts |
| `create_user` | Bool | no | `True` | Accounts |
| `auto_link_by_email` | Bool | no | `False` | Accounts |
| `trust_email_verification` | Bool | no | `False` | Accounts |
| `accept_string_booleans` | Bool | no | `False` | Accounts |

### `IOIDCSettings` — adds

| Field | Type | Required | Default | Fieldset |
|---|---|---|---|---|
| `issuer` | TextLine | yes | — | Settings |
| `group_claim` | TextLine | no | `''` | Groups |
| `allowed_groups` | Tuple | no | `()` | Groups |
| `sync_groups` | Bool | no | `True` | Groups |
| `picture_over_http` | Bool | no | `False` | Profile |

### `IGitHubSettings`

Inherits `IOAuth2Settings` and adds no fields. Two tabs: Settings, Accounts.

### `IPloneIdentitySettings`

Inherits `IOIDCSettings` and adds no fields. Four tabs.

### `IEmailSettings` — the magic-link driver

| Field | Type | Required | Default | Fieldset |
|---|---|---|---|---|
| `token_ttl` | Int | no | `900` | Settings |
| `rate_limit_per_hour` | Int | no | `5` | Settings |

Declares no fieldsets, so the form shows one tab.

### Fieldsets per driver

Resolved through `plone.supermodel.utils.mergedTaggedValueList`, which is what
the form and `plone.restapi` use. `queryTaggedValue` alone does **not** merge
across base interfaces and gives a wrong answer.

| driver | tabs |
|---|---|
| `email` | Settings |
| `github` | Settings, Accounts |
| `google` | Settings, Accounts |
| `oidc-generic` | Settings, Accounts, Groups, Profile |
| `plone-identity` | Settings, Accounts, Groups, Profile |

## 5. Registry records

### Site-wide: `IIdentitySettings`

<!-- source: backend/src/pas/plugins/identity/core/controlpanel/interfaces.py -->

Key prefix `pas.plugins.identity.`.

| Key | Type | Default |
|---|---|---|
| `callback_url` | TextLine | `/login-identity` |
| `user_content_type` | TextLine | `''` |
| `user_container_path` | TextLine | `''` |
| `group_content_type` | TextLine | `''` |
| `group_container_path` | TextLine | `''` |
| `sync_portraits` | Bool | `False` |
| `portrait_timeout` | Int | `5` |
| `portrait_max_bytes` | Int | `2097152` |
| `discovery_timeout` | Int | `10` |
| `audit_max_entries` | Int | `500` |
| `audit_max_days` | Int | `180` |
| `audit_record_pii` | Bool | `False` |
| `audit_sinks` | Tuple | `('plugin',)` |

`callback_url` defaults to `/login-identity`, which is exactly the frontend's
`CALLBACK_PATH` (§6). That correspondence is what makes the default work
out of the box, and it belongs in `reference/settings.md`.

### Per provider

Pattern: `pas.plugins.identity.providers.<provider_id>.<field>`, where `<field>`
is a field of that driver's `settings_schema` (§4). Provider records belong to no
interface — each carries its own field type. This is why the demo profile's
registry XML uses `<records prefix="...">` **with** an `interface` attribute
where one applies, and why `tests/demo/test_registry_profile.py` exists.

## 6. Frontend

<!-- source: frontend/packages/volto-identity/src/config/routes.ts -->

Package `@plone-collective/volto-identity`, version `1.0.0-alpha.0`.
**Not published to npm** (registry answers 404 as of 2026-09-05) and there is no
publish workflow in `.github/workflows/`. Install is from the repository.

Developed against Volto **19.3.0** (`frontend/mrs.developer.json`, tag `19.3.0`).
`peerDependencies` names React 18, `react-redux` ^8.1.2, `react-router-dom`
^5.2.0 and `@plone/components`; it does **not** name `@plone/volto`.

### Routes registered

| Constant | Path | Component |
|---|---|---|
| `CALLBACK_PATH` | `/login-identity` | `Callback` |
| `FIRST_LOGIN_PATH` | `/first-login` | `FirstLogin` |
| `FALLBACK_LOGIN_PATH` | `/fallback_login` | Volto's own `Login` |
| — | `/login` and `/**/login` | `Login` (this add-on's) |
| `IDENTITIES_PATH` | `/identities` | `Identities` |
| `CONSENT_PATH` | `/oauth-consent` | `Consent` |
| `APPLICATIONS_PATH` | `/applications` | `Applications` |
| `USER_ACCOUNT_PATH` | `/controlpanel/users/:userid/account` | `UserAccount` |
| `CONTROLPANEL_PATH` | `/controlpanel/identity-providers` | `ProvidersControlPanel` |
| `CLIENTS_CONTROLPANEL_PATH` | `/controlpanel/identity-clients` | `ClientsControlPanel` |

Ten routes, two of them control panels.

### Environment variables

| Variable | Default | Read where |
|---|---|---|
| `RAZZLE_IDENTITY_SHOW_PLONE_LOGIN` | off | `helpers/showPloneLogin.ts` |

`config.settings.identityShowPloneLogin` defaults to `false`
(`config/settings.ts`). The variable is read at **run** time via Volto's
`runtimeConfig`, not baked at build time; `RAZZLE_` is the only prefix Volto
carries through.

### Other registrations

- Views: `contentTypesViews` for the Profile and Group content types.
- Widgets: `provider_icon`.
- Reducers, menu entries, `appExtras`.

## 7. GenericSetup profiles

<!-- source: backend/src/pas/plugins/identity/profiles.zcml, server/profiles.zcml -->

| Profile id | Title | Version |
|---|---|---|
| `pas.plugins.identity:default` | Install | 1000 |
| `pas.plugins.identity:rebuild-catalog` | Rebuild the user catalog | — |
| `pas.plugins.identity:uninstall` | Uninstall | — |
| `pas.plugins.identity.server:default` | Authorization server | 1000 |
| `pas.plugins.identity.server:uninstall` | Uninstall the authorization server | — |

**There are no upgrade steps.** `upgrades/configure.zcml` contains only a
commented-out example. Both installable profiles are at version 1000. Any
`how-to-guides/upgrade.md` therefore documents reinstall and profile-application
procedures, not `portal_setup` upgrade steps — writing otherwise would be fiction.

`rebuild-catalog` is the "consistency check and rebuild step" the concept pages
refer to. It has a profile and **no how-to guide**. This is a real documentation
gap, not a hypothesis.

## 8. Layer terminology (resolves plan item 0.6)

The canonical set, from code:

**Distribution extras** (`backend/pyproject.toml`): `server`, `sql`, `test`.
There is **no `content` extra** and **no `profile` extra**.

**Python subpackages**: `core`, `server`, `sql`, plus support packages
(`exportimport`, `migration`, `upgrades`, `setuphandlers`, `profiles`,
`locales`).

**Layers a site installs**: two — **core** and **server**. Each has a
GenericSetup profile. `sql` has **no profile**: it is an optional extra that
registers an extra audit sink when SQLAlchemy is importable
(`configure.zcml`, `zcml:condition="installed sqlalchemy"`).

**Browser layers**: one, `IIdentityServerLayer`, declared in
`server/interfaces.py`. The core layer declares none.

So: the landing page's "two layers" is correct. The tutorial's table listing
`core`, `profile`, `server` is **wrong** — `profile` is the name of the user
*content type*, not a layer. Fix under plan item 1.3.

## 9. Classic UI (resolves plan item 1.5)

Findings:

- The add-on registers **no** Classic UI login view, viewlet or form.
- Its only page template is `server/browser/templates/consent.pt`, the OAuth
  consent screen. It is server-rendered and does not need Volto.
- `core/subscribers/gate.py` exempts the paths `login_form`, `logged_out`,
  `require_login` and `@@require_login` from the profile gate. That is an
  exemption, not an integration.
- Sign-in is entirely Volto routes (§6).

Érico's decision: document that Volto works today and that Classic UI support is
intended to come later.

## 10. Audit log

<!-- source: backend/src/pas/plugins/identity/core/audit/__init__.py -->

Event names, which are what `troubleshoot.md` entries must key on:

`authenticated`, `identity-linked`, `identity-unlinked`, `email-verified`,
`claims-refreshed`, `flow-refused`, `payload-rejected`, `link-refused`,
`link-collision`, `magic-link-sent`, `magic-link-confirmed`,
`magic-link-refused`, `signin-refused`.

Sentinel: `UNATTRIBUTED = "\x00unattributed"`. Constant `AUTHENTICATED` doubles
as the scope name `authenticated`.

Sinks are named utilities: `plugin` (bounded ZODB log, readable), `log`
(write-only, logger `pas.plugins.identity.audit`), `sql` (readable, `[sql]`
extra). Registry record `pas.plugins.identity.audit_sinks` lists which are used,
in order.

## 11. Events

<!-- source: backend/src/pas/plugins/identity/core/events/__init__.py -->

| Interface | Base |
|---|---|
| `IIdentityEvent` | `Interface` |
| `IExternalIdentityAuthenticated` | `IIdentityEvent` |
| `IIdentityLinked` | `IIdentityEvent` |
| `IIdentityUnlinked` | `IIdentityEvent` |
| `IEmailVerified` | `IIdentityEvent` |
| `ISessionsRevoked` | `IIdentityEvent` |
| `IUserClaimsRefreshed` | `IIdentityEvent` |

Attributes to be read per interface when `reference/events.md` is audited.

## 12. Permissions

<!-- source: backend/src/pas/plugins/identity/permissions.zcml -->

| Permission id | Title |
|---|---|
| `pas.plugins.identity.userprofile.add` | Add User Profile |
| `pas.plugins.identity.usergroup.add` | Add User Group |
| `pas.plugins.identity.content.edit` | Edit Profile |
| `pas.plugins.identity.content.editgroups` | Edit Profile Group Membership |
| `pas.plugins.identity.content.view` | View Profile |
| `pas.plugins.identity.content.viewpii` | View Personal Identifiable Information |

Default roles to be read from `profiles/default/rolemap.xml` when
`reference/permissions.md` is written.

## 13. Resolved `[H]` items from the plan's §0

| Item | Verdict |
|---|---|
| Docs compare against `Products.membrane` | `[V: true]` — `concepts/users-as-content.md`, `concepts/profiles-and-groups.md`, and `README.md` |
| Docs cite `OFS.Cache.Cacheable` | `[V: true]` — `concepts/users-as-content.md:151`, `concepts/profiles-and-groups.md:154` |
| CI test asserting zero ZODB wake-ups | `[V: true]` — `backend/tests/core/test_zero_wake.py` |
| A "Quick Start" page exists | `[V: it is `README.md` §"Quick Start 🏁", not a docs page]` — as the plan anticipated |
| Undocumented consistency check / rebuild step | `[V: true]` — the `rebuild-catalog` profile, §7 |
| `sphinxcontrib-mermaid` available | `[V: already a dependency]` — `docs/pyproject.toml` dev group, enabled in `conf.py`, `mermaid_version = "11.2.0"`. Plan item H4 needs no decision. |
| Packages published | `[V: false]` — npm and PyPI both 404 on 2026-09-05, no publish workflow |

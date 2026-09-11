---
myst:
  html_meta:
    "description": "Every REST endpoint and browser view pas.plugins.identity publishes."
    "property=og:description": "Every REST endpoint and browser view pas.plugins.identity publishes."
    "property=og:title": "Endpoints"
---

(reference-endpoints)=

# Endpoints

Every endpoint the package publishes, by layer.

```{important}
**Every authenticated REST service is registered with `zope2.View`, and
authorization happens inside the service class.** Reading the registration
alone understates what a caller needs. The "Requires" column below is what the
code actually enforces. The anonymous services are registered `zope.Public`
instead: `zope2.View` is inherited from the site root, so a site that takes
`View` away from `Anonymous` would refuse them.
```

<!-- source: backend/src/pas/plugins/identity/core/services/**/configure.zcml -->

## Core layer

Present in every installation.

| Method | Path | Requires | Purpose |
|---|---|---|---|
| GET | `@login-providers` | anonymous | Providers to offer on the login page. Enabled **and** shown only. Also available as a `plone.restapi` expander. |
| POST | `@identity-callback` | anonymous | The provider redirects here; completes a sign-in. |
| POST | `@magic-link` | anonymous | Send a single-use sign-in link. Answers identically whether or not the address is known. |
| POST | `@magic-link-confirm` | anonymous | Redeem a link. Burns the token. |
| GET | `@my-profile` | authenticated | The caller's own profile. Also available as a `plone.restapi` expander, on any content. |
| GET | `@identities` | authenticated | The caller's own sign-in methods. |
| POST | `@identities` | authenticated | Link a new sign-in method. |
| DELETE | `@identities/<provider>/<subject>` | authenticated | Unlink one. Refused for the last remaining method. |
| GET | `@types` | authenticated | The profile content types. |
| PATCH | `@users` | see source | Update profile fields. |
| GET | `@portrait/<userid>` | anonymous | A user's picture: the Profile's when it has one, the member portrait otherwise. The `[server]` layer publishes this URL as the OIDC `picture` claim. |
| GET | `@group-members/<group id>` | `Manage users`, or membership of the group | Members of a group. |
| GET | `@user-account/<userid>` | `Manage users` | One user's sign-in methods, for administrators. |
| GET | `@identity-drivers` | `Manage portal` | Drivers available to configure. |
| GET | `@identity-providers` | `Manage portal` | Configured providers, or one with `/<id>`. Secrets are masked. A bare `GET` also carries the form schema, and `can_export`: whether the caller may take an export. |
| POST | `@identity-providers` | `Manage portal` | Add a provider. |
| POST | `@identity-providers/<id>/test-connection` | `Manage portal` | Fetch the provider's discovery document, cache cleared first, and report what came back. |
| GET | `@identity-providers/<id>/export` | `pas.plugins.identity: Export Identity Providers` | One provider as a registry fragment a profile can ship. **Carries the client secret in the clear.** |
| GET | `@identity-providers/@export` | `pas.plugins.identity: Export Identity Providers` | Every provider as one registry document, in their order. **Carries every client secret in the clear.** |
| PATCH | `@identity-providers` | `Manage portal` | Reorder every provider, with `{"order": [<id>, …]}` naming each configured provider exactly once. The login page offers its buttons in this order. |
| PATCH | `@identity-providers/<id>` | `Manage portal` | Change one. |
| DELETE | `@identity-providers/<id>` | `Manage portal` | Remove one. Linked identities are kept. |
| GET | `@audit-log` | `Manage portal` | Authentication events. |

`@group-members` is the one with a compound rule: `Manage users`, **or**
membership of the group being asked about.

### Three answers worth knowing

| Endpoint | Answers |
|---|---|
| `@my-profile` | Where the caller's `UserProfile` is, what workflow state it is in, and the addresses it carries. Each `emails` entry has `verified` and `preferred`, the second marking the one `email` resolves to—so a page can show it without repeating the rule that picks it. The frontend uses this to send a new user to their profile once and never ask again. |
| `@group-members` | The people in one group, named rather than only listed as userids, plus the nesting around it and a search within it. `@groups/<id>` already carries member userids through PlonePAS; what it cannot do is name each person or search inside the group. |
| `@user-account` | Which providers a person has configured—named, dated, and flagged when the provider has since been disabled or removed—and when they last authenticated. One user at a time: the audit log is bounded per user, so folding this into the `@users` listing would read one bounded log per row. |

`@user-account` allows a caller asking about themselves without `Manage users`.

### `my-profile` as a component

<!-- The component is
     backend/src/pas/plugins/identity/core/services/myprofile/expander.py. -->

The profile gate asks its question on every navigation, and a navigation to a
content route is already a request.
`my-profile` is registered as an expandable component so the answer rides along
with the page, and `volto-identity` adds it to Volto's `apiExpanders`.

| Fact | Value |
|---|---|
| Registered on | Any content, not the site root alone |
| `@id` | The **site's** `@my-profile`, whatever page carries the component—the endpoint is registered for the site root and resolves nowhere else |
| Expanded | The same body the endpoint returns |
| Anonymous | The component is absent entirely, not an `@id` |

The anonymous rule is the one that differs from every other component here,
which publish a URL when unexpanded.
Volto's `apiExpanders` has no way to mark an entry authenticated-only, so
`?expand=my-profile` arrives on anonymous content requests as well; answering
with nothing keeps a public site's payload exactly as it was.


### A membership row

<!-- source: backend/src/pas/plugins/identity/core/serializers/groupmember.py -->

Each entry in the `items` of `@group-members`:

| Key | What it holds |
|---|---|
| `@id` | The person's `UserProfile`. |
| `id` | Their userid. |
| `fullname` | The full name, falling back to the login and then the userid, so a row is never blank. |
| `login` | The login name. |
| `profile_url` | The same URL as `@id`. Kept for clients written against the earlier `@id`, which pointed at the listing's own URL with the userid appended and answered `400`. |
| `through` | The groups this person is directly in, so a page listing an outer group can say where each of them came from. |

No address. A membership listing is personal data about other people, and it is
not a directory of contact details.

Every value is a catalog metadata column. That is what lets a group of a
thousand people be one query rather than a thousand object loads, so a
deployment adding a field to a row adds a metadata column to
`identity-catalog.xml` first, then subclasses `GroupMemberSerializer`, calls up
to it, and registers the subclass for its own browser layer. See
{doc}`/concepts/profiles-and-groups` for why the adapter is on the site rather
than on the brain.

## Server layer

Published only where the `pas.plugins.identity.server:default` profile has been
applied. These are bound to `IIdentityServerLayer`, so a site without that
profile does not publish them at all.

<!-- source: backend/src/pas/plugins/identity/server/services/configure.zcml -->

| Method | Path | Requires | Purpose |
|---|---|---|---|
| GET | `@identity-clients` | `Manage portal` | Registered OAuth clients, or one with `/<id>`. |
| POST | `@identity-clients` | `Manage portal` | Register one. **The secret is in this response and nowhere else.** |
| POST | `@identity-clients/<id>/rotate-secret` | `Manage portal` | Mint a fresh secret. Same warning applies. |
| PATCH | `@identity-clients/<id>` | `Manage portal` | Change title, redirect URIs, grants, scope, service user, and enabled. `client_id` and `auth_method` are not editable, and an unknown field is refused rather than ignored. |
| DELETE | `@identity-clients/<id>` | `Manage portal` | Remove one. |
| GET | `@identity-keys` | `Manage portal` | Describe the signing ring. |
| POST | `@identity-keys/rotate` | `Manage portal` | Rotate the signing key. Older keys stay in the ring so tokens already issued keep verifying. |
| GET | `@oauth-consent` | authenticated | What a client is asking for, for the consent screen. |
| GET | `@oauth-grants` | authenticated | Applications the caller has granted access to. |
| DELETE | `@oauth-grants/<client id>` | authenticated | Withdraw one. |

## Browser views

<!-- source: backend/src/pas/plugins/identity/{core,server}/browser/configure.zcml -->

| Path | Layer | Purpose |
|---|---|---|
| `@@identity-controlpanel` | core | The control panel view. |
| `@@backchannel-logout` | core | Receives a logout token from a provider. See {doc}`/how-to-guides/enable-back-channel-logout`. |
| `@@oauth-authorize` | server | The authorization endpoint. Public: the browser reaching it may be anonymous, and the view refuses an unauthenticated end user itself with the error code the specification names. |
| `@@oauth-token` | server | The token endpoint. Public: the caller is a server holding client credentials, authenticated inside against the client registry. |
| `@@oauth-jwks` | server | The signing keys, as JWKS. |
| `@@oauth-userinfo` | server | The userinfo endpoint. |
| `/.well-known/openid-configuration` | server | The discovery document. |

(reference-backchannel-logout)=

### Back-channel logout

```text
POST @@backchannel-logout
```

One endpoint serves every configured provider. The logout token names its issuer,
and that is how the package chooses the provider, and therefore the key to verify
the signature with.

The endpoint follows OpenID Connect Back-Channel Logout 1.0. A token must satisfy
**all** of the following:

| Check | Refused when |
|---|---|
| Signature | Not valid against the issuer's published key. |
| Issuer and audience | Either does not match. |
| `iat` | Outside the acceptable window. |
| `jti` | Already acted on. A repeat is a replay. |
| Event | No back-channel logout event declared. |
| Subject | Neither a `sub` nor a `sid` present. |
| `nonce` | **Present.** A nonce means somebody is passing an `id_token` off as a logout instruction. |

```{note}
Only `sub`-based logout is supported. This package does not track provider
session identifiers, so a token carrying only a `sid` is refused.
```

A logout for an identity this site has never seen answers `200`, not an error.
There is nothing to end, and answering differently would tell an unauthenticated
caller which of a provider's subjects have accounts here.

To enable it, see {doc}`/how-to-guides/enable-back-channel-logout`.

### Why `.well-known` is registered oddly

The path segment contains a dot, which a Zope view name cannot carry through
traversal in the usual way. So `.well-known` is registered as the **view**, and
the document name is traversed into it. A bare `/.well-known/` is refused.

The published path is what a client expects:

```text
https://id.example.com/.well-known/openid-configuration
```

## The consent screen is the only page template

`server/browser/templates/consent.pt` is the only page template in the package.
It is server-rendered, so a site running the `server` layer can be an identity
provider regardless of which frontend it runs itself.

Everything else a person sees is in the Volto add-on—see {doc}`frontend`.

## Related

- {doc}`frontend`—the routes that call these
- {doc}`settings`—the registry records that configure them
- {doc}`permissions`—the permissions named above
- {doc}`claims`—what the server layer releases

---
myst:
  html_meta:
    "description": "The public Python API of pas.plugins.identity: one import path for the interfaces, events, content classes and functions a downstream package needs."
    "property=og:description": "The public Python API of pas.plugins.identity: one import path for the interfaces, events, content classes and functions a downstream package needs."
    "property=og:title": "Python API"
    "keywords": "Plone, pas.plugins.identity, Python API, facade, IProfileEnricher, UserProfile"
---

(reference-python-api)=

# Python API

Everything this package offers Python code, at one import path.

```python
from pas.plugins.identity import api

api.IProfileEnricher            # register against
api.IdentityLinked              # subscribe to
api.UserProfile                 # type hint, adapt
api.profile.get_current()       # do
```

Write against `pas.plugins.identity.api`.
The module a name happens to live in under `core` or `server` is where it is implemented, not where it is published, and it moves without notice.

```{note}
`from pas.plugins.identity import api` shadows `from plone import api`.
A module that wants both aliases one:

    from pas.plugins.identity import api as identity_api
```

## Conventions

These hold across every name below, so that one worked example teaches the rest.

<!-- Source: backend/src/pas/plugins/identity/api/__init__.py -->

| | |
|---|---|
| Arguments | A userid where the question is about a *person*; the object where it is about a *Profile* |
| Returns | A lookup answers `None`. An operation that cannot proceed raises |
| Names | Verb first, no redundant noun: `api.profile.get`, never `api.get_profile` |
| Current user | Never implicit. `profile.get` takes its argument, `profile.get_current` takes none |

The last one is the one to read twice.
`api.profile.get(userid)` has no default, and that is deliberate: a default falling back to the current user would make `None` mean two things at once—"I did not say whose" and "the lookup missed"—and only the caller knows which.
A caller passing a userid read from catalog metadata that turned out to be missing would be handed *their own* Profile, and every check downstream would pass.

## Vocabulary

What a policy package registers against.
These are the same objects the layer defines, not copies, so an adapter registered through the façade is registered for what the package actually fires.

<!-- Source: backend/src/pas/plugins/identity/api/__init__.py -->

| Kind | Names |
|---|---|
| Content classes | `UserProfile`, `UserGroup` |
| Content interfaces | `IUserContent`, `IUserProfile`, `IUserGroup`, `IGroupContent` |
| Extension points | `IProfileEnricher`, `IDriver`, `IAuditSink`, `IAuditSource`, `IIdentityStore` |
| Catalog | `IIdentityProfileCatalog` |
| Event classes | `ExternalIdentityAuthenticated`, `IdentityLinked`, `IdentityUnlinked`, `EmailVerified`, `SessionsRevoked`, `UserClaimsRefreshed` |
| Event interfaces | `IIdentityEvent`, `IExternalIdentityAuthenticated`, `IIdentityLinked`, `IIdentityUnlinked`, `IEmailVerified`, `ISessionsRevoked`, `IUserClaimsRefreshed` |
| Driver authoring | `BaseDriver`, `IDriverSettings`, `IOAuth2Settings`, `IOIDCSettings`, `IGitHubSettings`, `IEmailSettings`, `IPloneIdentitySettings`, `USERID_SOURCES` |
| Records and types | `IdentityRecord`, `Claims`, `ProviderEmail`, `JSONDict` |
| Exceptions | `IdentityCollision`, `ClaimsError`, `ProviderUnusable` |
| Constants | `PROFILE`, `GROUP`, `MAPPABLE_FIELDS` |

Subscribe to an **event interface**, not to an event class—that is what a
ZCML `<subscriber>` registration and `@adapter` both take.
The classes are here for the code that constructs or type-hints one.

## `api.profile`

<!-- Source: backend/src/pas/plugins/identity/api/profile.py -->

| Call | Answers |
|---|---|
| `get(userid)` | The Profile, or `None` |
| `get_current()` | The current user's Profile, or `None`—including for an anonymous caller |
| `get_or_create(userid, login)` | The Profile, minting one if this is a first sign-in; `None` on a site that does not keep users as content |

A Profile wakes when you fetch it, so these are for paths that are going to read a field or write one.
A check that only needs one value should go through the catalog.

### Questions the Profile answers itself

There is no `api.profile.email(userid)` and no `api.profile.url(userid)`, on purpose.
A question about one Profile that the Profile can answer is a property on it:

```python
profile = api.profile.get(userid)

profile.email             # the address that stands for this person
profile.verified_emails   # the ones this site has proved
profile.absolute_url()    # where it lives
```

## `api.portrait`

Keyed by userid rather than by Profile, because a user with no Profile can still have a member portrait—so `profile.has_picture()` could not express an answer of `True`.

<!-- Source: backend/src/pas/plugins/identity/api/portrait.py -->

| Call | Answers |
|---|---|
| `has_picture(userid)` | Whether a picture exists in *either* store |
| `get_url(userid)` | The URL of the Profile's picture, or `None` |
| `store(userid, data, url="")` | Nothing. Stores image bytes the caller already holds, where a login would put them |
| `sync_portrait(userid, url, allow_http=False)` | Whether a picture was stored. Fetches the URL with a login's checks first |

The first two are not the same question: `has_picture` also looks in `portal_memberdata`.

The two writes are for two kinds of caller.
`store` is for one that downloaded its pictures beforehand, such as an import that caches them on disk.
It puts the picture on the Profile, unless the user has no Profile or chose a picture of their own there; then it goes to `portal_memberdata`.
Passing `url` lets the Profile remember where the picture came from, so a later login can replace it.

`sync_portrait` is for a caller that holds only a URL.
It fetches nothing unless the site-wide portrait switch is on, refuses plain HTTP unless `allow_http` is set, and applies the site's timeout and size limit.

`sync_portrait` is the one exception to the rule that an operation which cannot proceed raises.
It answers `False` instead, because it is the same call a login makes, and a login must not fail over an avatar.
A batch import learns *why* a picture was refused only from the log.

## `api.provider`

<!-- Source: backend/src/pas/plugins/identity/api/provider.py -->

| Call | Answers |
|---|---|
| `get(provider_id)` | One configured provider, or `None` |
| `get_all()` | Every configured provider, enabled or not, in the order the sign-in page offers them |
| `plugin()` | This package's PAS plugin, or `None` when the add-on is not installed here |

Read-only.
Registering or editing a provider goes through the control panel or a GenericSetup profile, so that every route in is held to the same validation.

## `api.claims`

Only on a site running the authorization server.
Importing `api.claims` is safe anywhere; calling into it needs `pas.plugins.identity[server]` installed and its profile applied.

<!-- Source: backend/src/pas/plugins/identity/api/claims.py -->

| Call | Answers |
|---|---|
| `get(userid, scope="")` | The claims this server releases, with `sub` set |
| `get_scopes()` | Every scope the server will release claims for |
| `get_released(scope)` | The claim names one scope releases, with no user in hand |
| `declared_scopes()` | The scopes the registered serializers declare |
| `declared_claims()` | The claims those serializers declare |

`declared_scopes()` is a subset of `get_scopes()`: `openid` is supported and declares no claims of its own.

For writing a serializer of your own, the same group carries what you subclass and register against:

| Name | Is |
|---|---|
| `ScopeSerializer` | The base class a new scope subclasses |
| `IScopeSerializer` | The interface a scope serializer is registered under |
| `ProfileScope`, `EmailScope`, `AddressScope` | The shipped serializers, to subclass when adding a claim to a scope this package already releases |

See {doc}`/how-to-guides/serialize-a-claim`.

## `api.clients`

Also `[server]` only.
The one group here whose operations raise rather than answer `None`—registering a client that already exists has no sensible empty answer.

<!-- Source: backend/src/pas/plugins/identity/api/clients.py -->

| Call | Answers |
|---|---|
| `get(client_id)` | One registered client, or `None` |
| `get_all()` | Every registered client, in registry order |
| `add(client_id, ...)` | The stored client and its plaintext secret |
| `remove(client_id)` | Nothing; raises when the client is not registered |
| `new_secret(client_id)` | A fresh secret, discarding the old one |
| `check(client_id, secret)` | The client, or `None` when authentication fails for any reason |

A minted secret is returned once and hashed on the way in.
It cannot be read back—not here, not from the control panel, not from the registry.

## Nothing in the package imports this

`api` spans every layer, so anything under `core` or `server` importing it would collapse the boundary those layers are kept apart by.
An import-linter contract enforces that, and `make check-imports` runs it.

<!-- Source: backend/pyproject.toml, contract "Nothing imports the api layer" -->

The same is true of `plone.api`, which nothing in Plone core imports.
Inside this package the layers keep importing each other directly; the façade is for consumers.

## Next steps

- Add a field to a Profile and fill it at login: {doc}`/how-to-guides/write-a-profile-enricher`.
- Release a claim about it: {doc}`/how-to-guides/serialize-a-claim`.
- What is settled and what is not: {doc}`stability`.

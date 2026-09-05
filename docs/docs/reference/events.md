---
myst:
  html_meta:
    "description": "The five events pas.plugins.identity fires, and the normalized claim keys they carry."
    "property=og:description": "The five events pas.plugins.identity fires, and the normalized claim keys they carry."
    "property=og:title": "Events"
---

(reference-events)=

# Events

<!-- source: backend/src/pas/plugins/identity/core/events/__init__.py -->

The core layer fires five events. They are the public API of this package: the
audit log, the content layer, and any integration you write are all consumers of
the same contract.

```{important}
This contract is versioned. Changes after 1.0 require a version bump note in the
changelog. See {doc}`stability`.
```

(reference-claims-schema)=

## The normalized claim keys

Every event that carries claims carries them in the shape drivers normalize to.
Consumers read these keys and nothing else.

```{note}
These are claims coming **in**, from a provider. For what this site releases as
an authorization server, see {doc}`claims`.
```

| Key | Type | Value |
|---|---|---|
| `fullname` | `str` | Human-readable name. Empty string when the provider sent none. |
| `email` | `str` | The address the provider reports, **lowercased**. The first entry of `emails`. |
| `email_verified` | `bool` | Whether the provider asserts `email` is verified. Read only when it is literally `True`, and worth something only for a provider the operator marked as trusting. |
| `emails` | `tuple[dict, ...]` | Every address the provider reports, in the order they should be offered: primary first, then verified. Each entry is `{"address": …, "verified": …, "primary": …}`. Empty when the provider sent no address. |
| `picture_url` | `str` | URL of an avatar image. |
| `username` | `str` | The provider-side login name. |
| `raw` | `dict` | The untouched provider payload. |

`emails` is not a claim any provider sends: it is this package's own. A driver
whose provider reports a single address fills it with that one entry, so nothing
downstream branches on how many there are. All of them go onto the person's
profile.

`email_verified` is `True` only when the payload's own `email_verified` **is**
the boolean `True`. A missing key, a `None`, and the string `"true"` are all
unverified. A provider that sends the string is repaired before normalization,
and only when its `accept_string_booleans` setting is on; `raw` still carries the
provider's own words afterwards.

Anything read from `raw` is your own compatibility problem, not this contract's.

See {doc}`/concepts/email-verification` for what `email_verified` is worth.

## The five events

| Event | Fired when | Carries |
|---|---|---|
| `ExternalIdentityAuthenticated` | Every successful external authentication, including the first | `userid`, `provider`, `subject`, `claims`, `is_new_user`, `is_new_identity` |
| `IdentityLinked` | An identity was attached to an account that already existed | `userid`, `provider`, `subject`, `claims` |
| `IdentityUnlinked` | An identity was detached | `userid`, `provider`, `subject` |
| `EmailVerified` | An address was proven to belong to a userid, by that user following a link this site sent to it | `userid`, `address` (lowercased) |
| `UserClaimsRefreshed` | Stored claims were updated outside the sign-in path | `userid`, `provider`, `claims` |

### Attribute meanings

| Attribute | Meaning |
|---|---|
| `userid` | The canonical Plone user id. |
| `provider` | Provider id, as configured in the control panel. |
| `subject` | The provider's own identifier for this person. |
| `claims` | Normalized claims, in the shape above. |
| `is_new_user` | `True` when this sign-in minted the user id. |
| `is_new_identity` | `True` when this sign-in attached the identity. |

`is_new_user` and `is_new_identity` are separate. Linking a second provider to an
existing account is a new identity for an existing user, so a consumer that
conflates the two greets a five-year member as a newcomer.

`IdentityUnlinked` carries no claims: there is no longer a provider answer to
describe.

`EmailVerified` is the only email verification this package trusts for linking
decisions.

## Subscribing

```python
from pas.plugins.identity.core.events import IExternalIdentityAuthenticated
from zope.component import adapter


@adapter(IExternalIdentityAuthenticated)
def welcome(event):
    if not event.is_new_user:
        return
    # Your code here.
```

```xml
<subscriber handler=".subscribers.welcome" />
```

## What is not an event

Refusals.

A callback rejected for a bad state has no user id, no provider answer, and no
successful anything to describe, so there is nothing to hang an event on. The
code that refuses them writes them to the audit log instead.

To react to failures, subscribe to the audit sink rather than waiting for an
event that will not arrive.

## Related

- {doc}`audit-log`—where refusals are recorded
- {doc}`claims`—claims going the other way, out to a relying party
- {doc}`stability`—what this contract promises
- {doc}`/how-to-guides/read-the-audit-log`—reacting to failures

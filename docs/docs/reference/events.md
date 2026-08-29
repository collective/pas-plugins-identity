---
myst:
  html_meta:
    "description": "The five events pas.plugins.identity fires, and the normalized claims schema they carry."
    "property=og:description": "The five events pas.plugins.identity fires, and the normalized claims schema they carry."
    "property=og:title": "Events and the claims schema"
---

(reference-events)=

# Events and the claims schema

The core layer fires five events.
They are the public API of this package: the audit log, the content layer, and any integration you write are all consumers of the same contract, and none of them reaches into the code that fires them.

```{important}
This contract is versioned.
Changes after 1.0 require a version bump note in the changelog.
```

(reference-claims-schema)=

## The claims schema

Every event that carries claims carries them in the shape drivers normalize to.
Consumers read these keys and nothing else.

`fullname`
:   Human-readable name.
    An empty string when the provider did not send one.

`email`
:   Email address as reported by the provider.
    The first entry of `emails`.

`email_verified`
:   Whether the provider asserts `email` is verified.
    Read only when it is literally `True`, and worth something only for a provider the operator marked as trusting -- see {doc}`/concepts/email-verification`.

`emails`
:   Every address the provider reports for the account, in the order they should be offered: primary first, then verified.
    One entry per address, each `{"address": ..., "verified": ..., "primary": ...}`.
    Not a claim any provider sends -- it is this package's own, and a driver whose provider sends a single address fills it with that one entry, so nothing downstream branches on how many there are.
    All of them go onto the person's profile.

`picture_url`
:   URL of an avatar image.

`username`
:   The provider-side login name.

`raw`
:   The untouched provider payload, for driver-specific consumers.
    Anything you read from here is your own compatibility problem, not this contract's.

## The events

### `ExternalIdentityAuthenticated`

Fired on every successful external authentication, including the first.

| Attribute | Meaning |
| --- | --- |
| `userid` | The canonical Plone user id. |
| `provider` | Provider id, as configured in the control panel. |
| `subject` | The provider's own identifier for this person. |
| `claims` | Normalized claims. |
| `is_new_user` | `True` when this sign-in minted the user id. |
| `is_new_identity` | `True` when this sign-in attached the identity. |

`is_new_user` and `is_new_identity` are separate on purpose.
Linking a second provider to an existing account is a new identity for an existing user, and a consumer that conflates the two will greet a five-year member as a newcomer.

### `IdentityLinked`

An external identity was attached to an account that already existed.

Carries `userid`, `provider`, `subject`, and `claims`.

### `IdentityUnlinked`

An external identity was detached.

Carries `userid`, `provider`, and `subject`.
It carries no claims, because there is no longer a provider answer to describe.

### `EmailVerified`

An email address was proven to belong to a user id, by that user following a link this site sent to it.

Carries `userid` and the lowercased `address`.

This is the only email verification this package trusts for linking decisions.
See {doc}`/concepts/email-verification`.

### `UserClaimsRefreshed`

Stored claims were updated outside the sign-in path.

Carries `userid`, `provider`, and the fresh `claims`.

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

A callback rejected for a bad state has no user id, no provider answer, and no successful anything to describe, so there is nothing to hang an event on.
The code that refuses them writes them to the audit log instead.
See {doc}`audit-log`.

To react to failures, subscribe to the audit sink rather than waiting for an event that will not arrive.
See {doc}`/how-to-guides/read-the-audit-log`.

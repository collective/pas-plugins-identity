# The event contract

Five events, fired by the core layer on the things worth knowing about. They
are the public API of this package: the audit log, the profile layer and any
integration you write are all consumers of the same contract, and none of them
reaches into the code that fires them.

That indirection is deliberate and it cuts both ways. An integrator who fires
`IdentityLinked` from their own code gets an audit entry for free — and,
less comfortably but more honestly, anything that forgets to fire an event is
invisible to every consumer.

:::{important}
This contract is versioned. Changes after 1.0 require a version bump note in
the changelog.
:::

## The claims schema

Every event that carries claims carries them in the shape drivers normalize
to. Consumers read these keys and nothing else.

`fullname`
: Human readable name. Empty string when the provider did not send one.

`email`
: Email address as reported by the provider.

`email_verified`
: Whether the provider asserts the address is verified. Only ever trusted
  when it is literally `True`.

`picture_url`
: URL of an avatar image.

`username`
: The provider-side login name.

`raw`
: The untouched provider payload, for driver-specific consumers. Anything you
  read from here is your own compatibility problem, not this contract's.

## The events

### `ExternalIdentityAuthenticated`

Fired on every successful external authentication, including the first.

| Attribute | Meaning |
| --- | --- |
| `userid` | The canonical Plone user id. |
| `provider` | Provider id, as configured in the control panel. |
| `subject` | The provider's own identifier for this person. |
| `claims` | Normalized claims. |
| `is_new_user` | True when this login minted the user id. |
| `is_new_identity` | True when this login attached the identity. |

`is_new_user` and `is_new_identity` are separate on purpose: linking a second
provider to an existing account is a new identity for an existing user, and a
consumer that conflates the two will greet a five-year member as a newcomer.

### `IdentityLinked`

An external identity was attached to an account that already existed. Carries
`userid`, `provider`, `subject` and `claims`.

### `IdentityUnlinked`

An external identity was detached. Carries `userid`, `provider` and `subject`
— no claims, because there is no longer a provider answer to describe.

### `EmailVerified`

An email address was proven to belong to a user id, by that user following a
link this site sent to it. Carries `userid` and the lowercased `address`.

This is the only email verification this package trusts for linking decisions.
A provider asserting `email_verified` is a claim about the provider's own
records, not proof that the person in front of you controls the address.

### `UserClaimsRefreshed`

Stored claims were updated outside the login path. Carries `userid`,
`provider` and the fresh `claims`.

## Subscribing

```python
from pas.plugins.identity.core.events import IExternalIdentityAuthenticated
from zope.component import adapter


@adapter(IExternalIdentityAuthenticated)
def welcome(event):
    if not event.is_new_user:
        return
    ...
```

```xml
<subscriber handler=".subscribers.welcome" />
```

## What is not an event

Refusals. A callback rejected for a bad state has no user id, no provider
answer and no successful anything to describe, so there is nothing to hang an
event on. Those are written to the audit log by the code that refuses them —
see {doc}`audit-log`.

If you need to react to failures, subscribe to the audit sink rather than
waiting for an event that will not arrive.

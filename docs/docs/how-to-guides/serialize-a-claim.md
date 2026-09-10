---
myst:
  html_meta:
    "description": "Register a scope serializer so this authorization server releases a claim of your own to relying parties."
    "property=og:description": "Register a scope serializer so this authorization server releases a claim of your own to relying parties."
    "property=og:title": "How to serialize a claim"
---

(how-to-serialize-a-claim)=

# How to serialize a claim

This guide shows you how to make this site, acting as an authorization server, release a claim it does not ship.

There are two shapes of that job, and they are the same mechanism:

- Add a claim to a scope this package already serves, such as putting a field of your own into `profile`.
- Add a scope of your own, with its own claims.

Both are one registered adapter.

```{note}
This is the `[server]` layer, where Plone *is* the identity provider.
If you want to read a claim *from* a provider and put it on a Profile, you want {doc}`write-a-profile-enricher` instead.
```

## What a scope serializer is

<!-- The contract is IScopeSerializer in
     backend/src/pas/plugins/identity/server/interfaces.py, and the lookup is
     backend/src/pas/plugins/identity/server/serializers/__init__.py. -->

A named multi-adapter on the site and the request, where the name is the scope.
One per scope, because a scope is what a relying party asks in and what a person consents to.

It has two halves, and both are needed.

| Half | Shape | Answers |
| --- | --- | --- |
| Declaration | `claims`, a class attribute | What this scope could release |
| Values | `__call__(user)` | What it releases about one user |

The declaration is read with no user in hand.
Three callers need it that way: `scopes_supported` and `claims_supported` in the discovery document, which is published to an unauthenticated caller, and the consent screen, which lists what a scope releases before anybody has agreed to it.
A scope whose claims the consent screen cannot enumerate tells a person they are releasing less than they are.

## Add a claim to a scope this package ships

Subclass the shipped serializer, call `super().__call__(user)`, and add to the result.
This is the same shape a `plone.restapi` serializer is extended in.

```python
from pas.plugins.identity import api
from pas.plugins.identity.server.serializers.profile import ProfileScope
from ploneorg.idp.behavior.badge import IUserBadge


class ProfileWithBadges(ProfileScope):
    """The `profile` scope, plus the badges this site awards."""

    claims = (*ProfileScope.claims, "badges")

    def __call__(self, user) -> dict:
        """Add the badges to the display claims.

        :param user: The Plone user the token acts for.
        :returns: The inherited claims plus `badges`.
        """
        claims = super().__call__(user)
        profile = api.profile.get(user.getId())
        if profile is not None:
            claims["badges"] = IUserBadge(profile).badges
        return claims
```

`get_profile` wakes the object, which the shipped serializers deliberately avoid: they read Plone user properties so that the `[server]` layer works on a site with no Profiles at all.
Your serializer is not under that constraint, because your package knows its own site has them.
It does cost a ZODB load per login, so read a catalog brain instead where the value you want is indexed.

Register it under the name of the scope it replaces, for your own browser layer:

```xml
<adapter
    name="profile"
    factory=".serializers.claims.ProfileWithBadges"
    for="plone.base.interfaces.IPloneSiteRoot
         ploneorg.idp.interfaces.IPloneorgIdpLayer"
    />
```

The layer is what makes yours win.
It is more specific than the `IBrowserRequest` this package registers for, so the lookup finds it first, and you need no `overrides.zcml`.

Two things that are easy to get wrong:

**Extend `claims`, do not replace it.** `(*ProfileScope.claims, "badges")` keeps what the scope already declared. Writing `claims = ("badges",)` leaves the values arriving and the declaration saying they do not, so the consent screen and the discovery document both understate what you release.

**Call `super()`.** An override that builds its own mapping stops releasing `name`, `email` and the rest to every relying party already reading them, and nothing fails—the claims are simply gone.

## Add a scope of your own

Subclass `api.claims.ScopeSerializer` and register the adapter under a name nothing else uses.

```python
from pas.plugins.identity import api


class PhoneScope(api.claims.ScopeSerializer):
    """The `phone` scope."""

    claims = ("phone_number", "phone_number_verified")

    def __call__(self, user) -> dict:
        """Return the telephone claims for one user.

        :param user: The Plone user the token acts for.
        :returns: Claim name to value.
        """
        number = user.getProperty("phone_number", "")
        if not number:
            return {}
        return {"phone_number": number, "phone_number_verified": False}
```

```xml
<adapter name="phone" factory=".serializers.claims.PhoneScope" />
```

A new scope reaches four places at once, with no further registration:

| Where | What it gets |
| --- | --- |
| The discovery document | The scope in `scopes_supported`, its claims in `claims_supported` |
| The client registration form | The scope offered in the picker |
| The consent screen | The claim names the person is agreeing to |
| An issued token | The values, for a client granted that scope |

Prefer a registered OIDC claim name where one fits what you mean.
A name only your own peers understand costs a relying party a mapping it would not otherwise need, and a relying party that does not know a claim ignores it.

## What you cannot change

<!-- RESERVED_CLAIMS in
     backend/src/pas/plugins/identity/server/claims.py. -->

`sub`, `iss`, `aud`, `exp` and `iat` are this server's own.
A serializer returning one of them is ignored on that key and releases the rest.

`sub` is the one that matters.
It is the join every relying party stores against its local account, so a serializer able to move it would re-identify every federated user at every relying party at once, with nothing to migrate back from.

## Absent, not blank

Return whatever you have.
A value that is `None`, an empty string, an empty list, or an empty mapping is dropped before the token is built.
A relying party can then tell an unknown value from a blank one.

`False` is a value and survives.
That is what lets `email_verified` say the site checked and found nothing, rather than saying nothing at all.

The rule is applied once, for every serializer, so it is not yours to remember.

## Test it

Register the adapter for the test and restore what it displaced.

Registering under a name already in use *replaces* that registration rather than shadowing it.
A test that overrides `profile` and then removes only its own adapter leaves that scope with no serializer for the rest of the run, and the failure lands on a later test.

`backend/tests/server/conftest.py` has a `register_scope` fixture that does the restoring, and `backend/tests/server/test_scope_serializers.py` is the worked example of both shapes.

Assert the reach, not only the value.
A claim that arrives in the token while the consent screen does not list it is released outside the consent:

```python
def test_the_consent_screen_can_enumerate_it(self):
    assert scope_claims("phone") == ("phone_number", "phone_number_verified")
```

## Related

- {doc}`/reference/claims`—every claim this server releases, and where its value comes from
- {doc}`register-an-oauth-client`—granting a client the scope you just added
- {doc}`write-a-profile-enricher`—the other direction: a claim *from* a provider onto a Profile
- {doc}`/concepts/layers`—why the server layer reads Plone user properties rather than a Profile

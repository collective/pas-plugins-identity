---
myst:
  html_meta:
    "description": "Write a named utility that puts data from a provider payload onto a Profile field the property map cannot reach."
    "property=og:description": "Write a named utility that puts data from a provider payload onto a Profile field the property map cannot reach."
    "property=og:title": "How to write a profile enricher"
---

(how-to-write-a-profile-enricher)=

# How to write a profile enricher

This guide shows you how to put data from a provider's payload onto a Profile
field that the claim-to-field property map cannot carry.

An enricher is a named utility that runs on every login, after this package has
written what it knows how to write. It is handed the Profile and the whole
normalized claims mapping, it writes whatever it likes, and it says which fields
it changed.

## When you need one

Reach for the property map first. It carries a value from a provider document to
a Profile field with no code at all, it is edited in the control panel, and
{doc}`configure-a-provider` covers it. It reads dotted paths into the provider's
own payload, so `address.formatted` and `raw` sub-keys are already within reach.

<!-- The three limits below are WRITABLE_FIELDS and _scalar in
     backend/src/pas/plugins/identity/core/subscribers/__init__.py. -->

The map stops at three walls, and an enricher is the way past all three.

| The map cannot | Why |
|---|---|
| Write anything but a scalar | A claim resolving to a list or a mapping is read as *absent*, so an OIDC `address` object is never written into a location field as its Python representation |
| Write a field it does not know | The target must be `fullname`, `home_page`, `description` or `location`; a map naming anything else is ignored |
| Transform a value | It is a copy. Building a URL from a handle, or a list from three keys, is code |

A behavior that adds a **list** field to the Profile hits the first and second
walls at once. That is the case this hook exists for.

## Write the utility

An enricher provides `IProfileEnricher` and implements one method, `enrich`.
A utility that handles more than one kind of provider stays readable when that
method does nothing but dispatch on the driver:

```python
from pas.plugins.identity.core.interfaces import IProfileEnricher
from zope.interface import implementer


@implementer(IProfileEnricher)
class SocialLinks:
    """Put the accounts a provider knows about onto the profile."""

    def enrich(self, profile, claims, provider, memory):
        if provider is None:
            return []

        if handler := getattr(self, f"enrich_{provider.driver_id}", None) is None:
            return []
        return handler(profile, claims, memory)

    def enrich_github(self, profile, claims, memory):
        raw = claims.get("raw") or {}
        links = []
        if handle := raw.get("twitter_username"):
            links.append(f"https://twitter.com/{handle}")
        if blog := raw.get("blog"):
            links.append(blog)

        if not links or memory.get("written") == links:
            return []

        profile.social_links = links
        memory["written"] = list(links)
        return ["social_links"]
```

A detail in that dispatch are load-bearing.

**A handler returns field names, not the mapping.** Returning `memory` is the
easy slip, and it is not caught: the runner can loop over a mapping, so it reads
its *keys* as field names, reports a field called `written` that does not exist, and
fires a modification event for it.

Four arguments arrive, and the last two are the ones people skip.

`profile`
: The Profile, already written to by this package.

`claims`
: The normalized claims. `claims["raw"]` is the provider's payload; the other
keys are the normalized view—`emails`, `username`, `picture_url` and the rest,
listed in {doc}`/reference/claims`.

`provider`
: The provider configuration this login came through, or `None` where there is
none. Check it before reading the payload.

`memory`
: A persistent mapping private to your utility's registered name, for whatever
you need to remember between logins.

Return the names of the fields you changed. An empty list means you wrote
nothing, and no modification event is fired for it.

## Register it under a name

```xml
<utility
    name="plonegovbr.socialmedia"
    provides="pas.plugins.identity.core.interfaces.IProfileEnricher"
    factory=".enrichers.SocialLinks"
    />
```

Every registered name runs, on every login. There is no setting listing them: an
enricher is code a deployment installed, not a destination it configured, so a
site that does not want one does not install it.

The name is also the key your `memory` is stored under, so choose your add-on's
own dotted name and do not change it later. Enrichers run in name order, which
makes a run reproducible and is not permission to depend on each other.

## Remember what you wrote

This is the rule that is easy to leave out and expensive to leave out.

<!-- The package's own fence is _provider_may_write in
     backend/src/pas/plugins/identity/core/subscribers/__init__.py. -->

This package never overwrites a value a user has edited since a provider wrote
it. It decides that by remembering what it last wrote and comparing: if the
current value is still the provider's own, the provider may replace it; once
somebody edits it, the provider is locked out of that field for good.

That comparison is a scalar one and says nothing useful about a list, where the
value on the object and your contribution to it are not the same thing. So the
package does not apply its fence on your behalf—it hands you `memory` and you
decide.

An enricher that skips the question reasserts its value on every login. A user
who deletes an entry gets it back the next time they sign in, for ever, which
reads as a bug and is the failure the fence exists to prevent.

The example above takes the simplest form of the rule: remember what you wrote,
and write nothing when the answer has not changed. A field your user may edit
needs the fuller version—compare the stored value against what you last wrote
and leave it alone when they differ.

## Key on the provider, never on the payload

A payload is only interpretable against the provider that produced it. GitHub's
`twitter_username` and Google's `hd` mean nothing in each other's documents, and
an enricher that looks for a key it hopes is meaningful will one day find it in
a document that meant something else. Every enricher starts by deciding whether
this login is one of its own.

Two fields answer two different questions, and mixing them up is the mistake
worth naming.

| Field | Is | Key on it when |
|---|---|---|
| `provider.driver_id` | The *kind* of provider—`github`, `google`, `oidc` | You are parsing a payload shape |
| `provider.provider_id` | The configured instance—`github`, `github-enterprise` | You mean one deployment in particular |

A site running a public GitHub and a GitHub Enterprise has two provider ids and
one driver id. An enricher reading GitHub's `/user` document wants the driver, so
that both work; an enricher that means the corporate one only wants the provider.

`provider` is `None` on every path that has no provider to name—the same paths
that arrive with an empty `raw`—so the check earns its place twice.

## Know what the payload is

<!-- The id_token / userinfo branch is _claims in
     backend/src/pas/plugins/identity/core/flows/__init__.py. -->

`claims["raw"]` is not always the same document, and an enricher that assumes
one shape works for one provider.

| Provider kind | What `raw` holds |
|---|---|
| Plain OAuth2, such as GitHub | The userinfo document, after the driver's enrichment step |
| Any provider issuing an `id_token` | The token's claims—the userinfo endpoint is never read |
| A magic-link confirmation | Empty |
| An address verification | Empty |
| Either authomatic path | What authomatic stored for that account |

The second row catches people out. A provider that issues an `id_token` has that
preferred, because it is signed and carries the nonce, and its claims are
typically thinner than the same provider's userinfo document. Read `raw`
defensively and do nothing when what you need is not there.

For GitHub specifically, `raw` is the `/user` response. The addresses from
`/user/emails` are folded into `claims["emails"]` instead and are not in `raw`,
so nothing downstream sees a key no provider sent.

### What a migration hands you

<!-- _payload_for in backend/src/pas/plugins/identity/migration/authomatic.py
     and _claims in backend/src/pas/plugins/identity/exportimport/authomatic.py. -->

Both authomatic paths link each identity through the plugin, which fires
`IdentityLinked`, which runs your enricher. The payload is authomatic's own
record for that account, not a fresh provider response: the attributes it parsed
out, layered over the provider document it kept in `data`. The parsed attribute
wins where both carry a key, which is the order authomatic's own property sheet
uses.

That is a fourth shape, and the closest to the first row—a GitHub account
migrated from authomatic carries the `/user` keys it was stored with. It is a
snapshot of whenever that person last signed in to the old site, so it can be
years old and can lack a key the provider sends today. Treat it as the same
defensive read as everything else here.

Credentials never reach you. Authomatic keeps a serialized `Credentials` on
every identity, holding the account's access and refresh tokens, and the
conversion strips it along with the other credential-bearing key names. A claims
snapshot is stored on the identity record and written out again by the exporter,
so anything carried in would be in the database and in every principal document
exported afterwards.

An enricher runs once per identity that the import actually links. An identity
already pointing at the right person is skipped, which is what makes a second
import a no-op—so installing an enricher and re-running an import does not
enrich the accounts that arrived the first time.

## Follow the rules

**Do not raise.** An exception is caught, logged with its stack trace, and the
login carries on without you. That is deliberate: an add-on that fails must not
lock the site's users out, because the administrator who would remove it is one
of them. Do not rely on it—an enricher that fails on every login writes nothing
and fills the log—but know that the login survives you.

**Do not perform I/O.** This runs inside the login request. A call to a slow
host is a slow login for everybody, and a call to an unreachable one is a login
that waits for a timeout.

**Do not write another add-on's fields.** Two enrichers writing one field is
logged as a collision and resolved by name order, which is a coin toss dressed
up as a rule. Write the fields your own behavior owns.

**Know that you run elevated.** The person signing in holds no roles yet, so
enrichers run as `Manager`. What you write is not checked against their
permissions. An enricher is trusted code.

## Test it

Call `enrich_profile` directly against a recorded payload, the way the drivers
are tested. It needs no provider and no network.

```python
from pas.plugins.identity.core.enrichment import enrich_profile

changed = enrich_profile(profile, {"raw": {"twitter_username": "dscully"}})

assert changed == ["social_links"]
assert profile.social_links == ["https://twitter.com/dscully"]
```

Register the utility for the test and unregister it afterwards. One left in the
global registry changes every later test in the run, and it fails somewhere else
entirely.

Two cases are worth asserting beyond the happy path: that a second run with the
same payload writes nothing, which is the `memory` rule, and that an empty `raw`
does nothing rather than raising.

## Next steps

- {doc}`/reference/claims`—the claim names, and what `raw` carries
- {doc}`configure-a-provider`—the property map, which handles the easy cases
- {doc}`write-a-driver`—for a provider this package does not ship
- {doc}`/concepts/profiles-and-groups`—why a provider may only replace what it wrote

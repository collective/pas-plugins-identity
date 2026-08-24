# Writing a driver

A driver is two things: static metadata describing what a kind of provider
needs, and a function turning that provider's answer into the normalized
claims schema. It holds no state and makes no decisions about accounts.

Drivers are registered as named ZCA utilities, and the utility name is the
driver id. This package keeps one module per driver; doing the same in your
own add-on keeps a driver easy to find.

## The pieces

Subclassing `BaseDriver` gives you the OAuth config fields, the subject
extraction and the shared claim normalization, so a driver is usually a few
class attributes and one override:

```python
from pas.plugins.identity.core.drivers.base import BaseDriver
from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.interfaces import JSONDict


class GitLabDriver(BaseDriver):
    """Sign in with a self-hosted GitLab."""

    driver_id = "gitlab"
    title = "GitLab"
    default_scope = ("read_user",)
    subject_keys = ("sub", "id")

    #: Rendered by the control panel. The frontend builds the form from this,
    #: so a field you declare here appears with no frontend change.
    extra_fields = {
        "base_url": {
            "type": "string",
            "title": "GitLab URL",
            "required": True,
            "secret": False,
            # Where it goes in the form. A schema travels as a JSON object
            # with sorted keys, so this is what survives the wire; the
            # inherited fields are spaced by ten to leave room between them.
            "order": 15,
        },
    }

    def normalize_claims(self, payload: JSONDict) -> Claims:
        """Turn GitLab's answer into the documented schema.

        :param payload: The provider's userinfo response.
        :returns: Normalized claims.
        """
        claims = super().normalize_claims(payload)
        claims["picture_url"] = payload.get("avatar_url", "")
        return claims
```

Implementing `IDriver` from scratch works too: the interface asks for
`driver_id`, `title`, `config_schema()`, `subject()` and `normalize_claims()`.

```xml
<utility
    factory=".gitlab.GitLabDriver"
    provides="pas.plugins.identity.core.interfaces.IDriver"
    name="gitlab"
    />
```

## Rules

**Mark a field secret and it stays secret.** Anything you declare as a secret
is masked on the way out of every API surface and omitted from GenericSetup
export. Do not invent your own storage for credentials.

**Every field needs an `order`, and no two may share one.** A config schema
travels as a JSON object, and `plone.restapi` serialises those with sorted
keys — so the order you declare your fields in is gone by the time the
control panel builds a form from them. The number is what survives. The
inherited fields are spaced by ten so you can slot yours between two of them;
a tie fails the driver contract test rather than falling back to the
alphabet, which is the bug this replaced.

**A scope is a list, not a sentence.** `default_scope` is a tuple of
permissions, and the space-delimited form RFC 6749 puts on the wire is built
at the edge, where the request is. A scope typed into one text box is how a
stray comma becomes a permission of its own that the provider rejects as
unknown.

**Seed a mapping with `default_propertymap`, against the normalized claim
names.** It is written into a new provider's attribute mapping as a starting
point, and it may only name member fields a stock site actually has —
`IUserDataSchema` declares `fullname` and `email`, and nothing else is
guaranteed. Write it against the normalized claims (`email`, `fullname`)
rather than your provider's own: `resolve_claim` tries those first, so one
default covers every provider. Name a raw claim only for something
normalization does not already produce.

**`email_verified` must be a boolean, and only `True` counts.** Several
providers send the string `"true"`, and several send `1`. Normalize it. The
auto-link-by-email feature refuses anything that is not literally `True`,
because a forged unverified address that reads as truthy is an account
takeover.

**Never construct protocol messages by hand.** Authorization URLs, token
requests and JWT parsing all go through authlib. This is checked in CI: a
grep-level rule fails the build if protocol construction appears outside the
flow modules. It exists because hand-rolled OAuth is how this goes wrong.

**`raw` is yours, the rest is the contract.** Put the untouched payload in
`raw` and read it in your own consumers if you must. Anything else you invent
at the top level will be ignored.

## Testing a driver

Normalize against recorded payload fixtures rather than live calls. The
drivers shipped here are tested that way: a real captured response, checked
into the test suite, normalized and asserted field by field. It costs nothing
to run, it does not need credentials, and it still catches the case that
matters — a provider changing the shape of its answer.

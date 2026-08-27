---
myst:
  html_meta:
    "description": "Write, register, and test a driver for a provider that pas.plugins.identity does not ship."
    "property=og:description": "Write, register, and test a driver for a provider that pas.plugins.identity does not ship."
    "property=og:title": "How to write a driver"
---

(how-to-write-a-driver)=

# How to write a driver

This guide shows you how to add support for a provider the package does not ship.

A driver is two things: static metadata describing what a kind of provider needs, and a function that turns that provider's answer into the normalized claims schema.
It holds no state and it makes no decisions about accounts.

Drivers are registered as named ZCA utilities, and the utility name is the driver id.
This package keeps one module per driver, and doing the same in your own add-on keeps a driver easy to find.

## Subclass `BaseDriver`

`BaseDriver` gives you the OAuth configuration fields, the subject extraction, and the shared claim normalization.
A driver is usually a few class attributes and one override:

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

If you would rather implement `IDriver` from scratch, the interface asks for `driver_id`, `title`, `config_schema()`, `subject()`, and `normalize_claims()`.

## Register it

```xml
<utility
    factory=".gitlab.GitLabDriver"
    provides="pas.plugins.identity.core.interfaces.IDriver"
    name="gitlab"
    />
```

## Follow the rules

**Mark a field secret and it stays secret.**
Anything you declare as a secret is masked on the way out of every API surface and omitted from GenericSetup export.
Do not invent your own storage for credentials.

**Give every field an `order`, and never let two share one.**
A configuration schema travels as a JSON object, and `plone.restapi` serializes those with sorted keys, so the order you declare your fields in is gone by the time the control panel builds a form from them.
The number is what survives.
The inherited fields are spaced by ten so you can slot yours between two of them.
A tie fails the driver contract test rather than falling back to the alphabet, which is the bug this replaced.

**Treat a scope as a list, not a sentence.**
`default_scope` is a tuple of permissions, and the space-delimited form that RFC 6749 puts on the wire is built at the edge, where the request is.
A scope typed into one text box is how a stray comma becomes a permission of its own that the provider rejects as unknown.

**Seed a mapping with `default_propertymap`, against the normalized claim names.**
The package writes it into a new provider's attribute mapping as a starting point, and it may only name member fields that a stock site actually has.
`IUserDataSchema` declares `fullname` and `email`, and nothing else is guaranteed.
Write it against the normalized claims rather than your provider's own, because `resolve_claim` tries those first, so one default covers every provider.
Name a raw claim only for something normalization does not already produce.

**Say whether your provider has groups, with `default_group_claim`.**
Set it to the claim the groups arrive in, usually `groups`, or leave it empty when the provider has none.
Empty is not a neutral default: it switches the feature off for your driver, so no `group_claim` field appears in the configuration form and nobody is asked to map the groups of a provider that has none.
A map stored against such a provider grants nothing rather than guessing at a claim name.
Operators can override the claim with a dotted path, so a provider nesting them under `realm_access.roles` needs no driver of its own.

**Leave `default_groupmap` empty unless you genuinely know the far end's groups.**
Group names are a fact about one deployment's directory, not about a driver, so seeding this is almost always wrong.
Even the `plone-identity` driver ships it empty, though it knows its peer releases the claim: two Plone sites do not have the same groups just because they run the same package.

**Make `email_verified` a boolean, and count only `True`.**
Several providers send the string `"true"`, and several send `1`.
Normalize it.
Automatic linking by email refuses anything that is not literally `True`, because a forged unverified address that reads as truthy is an account takeover.
See {doc}`/concepts/email-verification`.

**Never construct protocol messages by hand.**
Authorization URLs, token requests, and JWT parsing all go through authlib.
CI checks this: a grep-level rule fails the build if protocol construction appears outside the flow modules.
It exists because hand-rolled OAuth is how this goes wrong.

**Put your own data in `raw` and nowhere else.**
Put the untouched payload in `raw` and read it in your own consumers if you must.
Anything else you invent at the top level is ignored.

For the schema your driver must produce, see {doc}`/reference/events`.

## Test it

Normalize against recorded payload fixtures rather than live calls.

The drivers shipped here are tested that way.
A real captured response is checked into the test suite, normalized, and asserted field by field.
It costs nothing to run, it does not need credentials, and it still catches the case that matters, which is a provider changing the shape of its answer.

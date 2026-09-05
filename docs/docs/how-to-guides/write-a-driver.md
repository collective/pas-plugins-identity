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

First the settings an operator fills in, as an ordinary `zope.schema` interface.
Extend `IOAuth2Settings` and you inherit the client credentials, the scope, the userid source and the two trust switches; add only what your provider needs.

```python
from pas.plugins.identity import _
from pas.plugins.identity.core.drivers.settings import IOAuth2Settings
from plone.autoform import directives
from zope import schema


class IGitLabSettings(IOAuth2Settings):
    """What a self-hosted GitLab needs beyond the OAuth2 fields."""

    base_url = schema.TextLine(
        title=_("GitLab URL"),
        description=_("The root of your GitLab, with no trailing path."),
        required=True,
    )
    # Ahead of the credentials: everything else is read from what this
    # discovers. Position is declared, never spaced out by hand.
    directives.order_before(base_url="client_id")
```

Then the driver, which names it:

```python
from pas.plugins.identity.core.drivers.base import BaseDriver
from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.interfaces import JSONDict


class GitLabDriver(BaseDriver):
    """Sign in with a self-hosted GitLab."""

    driver_id = "gitlab"
    title = "GitLab"
    settings_schema = IGitLabSettings
    default_scope = ("read_user",)
    subject_keys = ("sub", "id")

    def normalize_claims(self, payload: JSONDict) -> Claims:
        """Turn GitLab's answer into the documented schema.

        :param payload: The provider's userinfo response.
        :returns: Normalized claims.
        """
        claims = super().normalize_claims(payload)
        claims["picture_url"] = payload.get("avatar_url", "")
        return claims
```

`@identity-drivers` serializes that interface with `plone.restapi`, so the field appears in the control panel with no frontend change, in the site's language, and validated.

```{tip}
Put translatable strings through `_()`, and let the field type carry the meaning: a `Password` is masked everywhere without a flag, a `Choice` over a vocabulary becomes a select, and a `Tuple` becomes a list.
Defaults that differ per driver—the scope GitLab needs, the userid source—stay on the driver class as `default_scope` and friends, because a subinterface redeclaring a field to change its default gives it a fresh creation order and the field jumps to the end of the form.
```

If you would rather implement `IDriver` from scratch, the interface asks for `driver_id`, `title`, `settings_schema`, `subject()`, and `normalize_claims()`.

## Register it

```xml
<utility
    factory=".gitlab.GitLabDriver"
    provides="pas.plugins.identity.core.interfaces.IDriver"
    name="gitlab"
    />
```

## Follow the rules

There are eight, and they are a checklist rather than a narrative:
{doc}`/reference/driver-contract` lists each one with what enforces it, and
explains the three that surprise people—why `order` is a number, why only a
literal `True` counts as verified, and why an empty `default_group_claim` is not
a neutral default.

Three of them are worth stating here, because they are about code you are about
to write rather than values you are about to declare.

**Report every address the provider knows, not the first one.**
`normalize_claims` fills `emails` with one entry per address -- `address`,
`verified`, `primary` -- and the base class does that for you from the single
address most providers send. Override it only where the provider offers more, and
put them in the order they should be offered: primary first, verified before
unverified. All of them go onto the person's profile, and `email` is the head of
the list.

**Never construct protocol messages by hand.**
Authorization URLs, token requests, and JWT parsing all go through authlib. CI
checks this: a grep-level rule fails the build if protocol construction appears
outside the flow modules. It exists because hand-rolled OAuth is how this goes
wrong.

**Put your own data in `raw` and nowhere else.**
Put the untouched payload in `raw` and read it in your own consumers if you must.
Anything else you invent at the top level is ignored.

For the schema your driver must produce, see {doc}`/reference/events`.

## Test it

Normalize against recorded payload fixtures rather than live calls.

The drivers shipped here are tested that way.
A real captured response is checked into the test suite, normalized, and asserted field by field.
It costs nothing to run, it does not need credentials, and it still catches the case that matters, which is a provider changing the shape of its answer.

## Next steps

- {doc}`/reference/driver-contract`—the eight rules, and what enforces each
- {doc}`/reference/claims`—the claim names to normalize to
- {doc}`/reference/shipped-drivers`—five worked examples
- {doc}`configure-a-provider`—configuring a provider that uses your driver

# Writing a driver

A driver is two things: static metadata describing what a kind of provider
needs, and a function turning that provider's answer into the normalized
claims schema. It holds no state and makes no decisions about accounts.

Drivers are registered as named ZCA utilities.

## The pieces

```python
from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.interfaces import IDriver
from zope.interface import implementer


@implementer(IDriver)
class GitLabDriver:
    """Sign in with a self-hosted GitLab."""

    id = "gitlab"
    title = "GitLab"

    #: Rendered by the control panel. The frontend builds the form from this,
    #: so a field you declare here appears with no frontend change.
    extra_fields = {
        "base_url": {
            "type": "string",
            "title": "GitLab URL",
            "required": True,
        },
    }

    def normalize(self, payload: dict) -> Claims:
        """Turn GitLab's answer into the documented schema.

        :param payload: The provider's userinfo response.
        :returns: Normalized claims.
        """
        return {
            "fullname": payload.get("name", ""),
            "email": payload.get("email", ""),
            "email_verified": payload.get("email_verified") is True,
            "picture_url": payload.get("avatar_url", ""),
            "username": payload.get("username", ""),
            "raw": payload,
        }
```

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

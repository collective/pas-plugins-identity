"""Common behavior shared by every provider driver.

A driver is static metadata plus claim normalization -- it never performs I/O
and never touches the ZODB, which is what makes the whole layer unit-testable
against recorded payload fixtures with no provider in the loop.
"""

from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.interfaces import ClaimsError
from pas.plugins.identity.core.interfaces import IDriver
from pas.plugins.identity.core.interfaces import JSONDict
from zope.interface import implementer


def text(payload: JSONDict, *keys: str) -> str:
    """Return the first non-empty string among ``keys``.

    :param payload: Provider payload.
    :param keys: Candidate keys, in order of preference.
    :returns: The value, or an empty string when none is usable.
    """
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


#: Config fields every OAuth2/OIDC driver needs.
#:
#: Every descriptor carries an ``order``, because a schema travels as a JSON
#: object and plone.restapi serialises those with ``sort_keys=True`` -- so the
#: order these are declared in is gone by the time a form is built from them.
#: The numbers are spaced by ten so a driver can slot a field of its own
#: between two of these without renumbering anything.
OAUTH_FIELDS: dict[str, JSONDict] = {
    "client_id": {
        "type": "string",
        "title": "Client ID",
        "required": True,
        "secret": False,
        "order": 20,
    },
    "client_secret": {
        "type": "string",
        "title": "Client secret",
        "required": True,
        "secret": True,
        "order": 30,
    },
    "scope": {
        "type": "list",
        "title": "Scope",
        "description": (
            "One permission per entry. They are joined with spaces when the "
            "authorize URL is built, which is the encoding OAuth 2 defines "
            "-- a scope containing a space is not one scope."
        ),
        "required": False,
        "secret": False,
        "order": 40,
    },
}


@implementer(IDriver)
class BaseDriver:
    """Common behavior for drivers.

    Subclasses declare :attr:`driver_id`, :attr:`title`, the extra config
    fields they need, and how to read a subject out of a payload.
    """

    driver_id: str = ""
    title: str = ""

    #: Default value for the ``scope`` config field, one token per entry.
    #:
    #: A tuple rather than the space-joined string OAuth 2 puts on the wire:
    #: a scope is a list of permissions, and typing them into one text box is
    #: how a trailing space or a comma becomes a scope of its own that the
    #: provider then rejects as unknown.
    default_scope: tuple[str, ...] = ()

    #: Keys tried, in order, to find the provider-side subject.
    subject_keys: tuple[str, ...] = ("sub",)

    #: Extra config fields beyond :data:`OAUTH_FIELDS`.
    extra_fields: dict[str, JSONDict] = {}  # noqa: RUF012

    #: Seeded into a new provider's attribute mapping.
    #:
    #: Written against the *normalized* claim names rather than any one
    #: provider's -- ``resolve_claim`` tries those before the raw payload, so
    #: ``fullname`` reaches GitHub's ``login`` fallback and an OIDC
    #: ``preferred_username`` alike without either being named here. Only the
    #: two fields ``IUserDataSchema`` actually declares are mapped: a stock
    #: site has no ``username`` member field for a third to be written to.
    default_propertymap: dict[str, str] = {  # noqa: RUF012
        "email": "email",
        "fullname": "fullname",
    }

    def config_schema(self) -> JSONDict:
        """Return the configuration schema for this driver.

        :returns: Mapping of field name to descriptor. Secret fields are
            flagged so every API surface can mask them.
        """
        schema: JSONDict = {k: dict(v) for k, v in OAUTH_FIELDS.items()}
        schema["scope"]["default"] = list(self.default_scope)
        # Off by default, and even when on it is only ever honoured against
        # this package's own magic-link-verified addresses -- never against
        # another provider's word for it.
        schema["auto_link_by_email"] = {
            "type": "bool",
            "title": "Attach to an existing account with the same verified email",
            "description": (
                "Only matches addresses this site verified itself with a "
                "magic link. A provider asserting email_verified is not "
                "enough."
            ),
            "required": False,
            "secret": False,
            "default": False,
            "order": 60,
        }
        schema["userid_source"] = {
            "type": "choice",
            "title": "Userid taken from",
            "description": (
                "What the Plone userid is minted from the first time "
                "somebody signs in with this provider. A random id is the "
                "safe default: it leaks nothing and never has to change. "
                "The others are readable, which matters when a person has "
                "to be recognised in Plone -- and they are claims, so two "
                "providers can offer the same one. A userid already in use "
                "is never handed out: the new one gets a numeric suffix."
            ),
            "required": False,
            "secret": False,
            "default": "uuid",
            "order": 50,
            "choices": [
                ["uuid", "A random id"],
                ["username", "The provider's username"],
                ["email", "The email address"],
                ["subject", "The provider's subject identifier"],
            ],
        }
        for name, descriptor in self.extra_fields.items():
            schema[name] = dict(descriptor)
        return schema

    def subject(self, payload: JSONDict) -> str:
        """Extract the immutable provider-side subject identifier.

        :param payload: Raw provider payload.
        :returns: The subject as a string.
        :raises ClaimsError: When no usable subject is present.
        """
        for key in self.subject_keys:
            value = payload.get(key)
            # Providers are inconsistent about numeric ids; normalize to str.
            if isinstance(value, int) and not isinstance(value, bool):
                return str(value)
            if isinstance(value, str) and value.strip():
                return value.strip()
        raise ClaimsError(
            f"{self.driver_id}: payload carries no subject "
            f"(tried {', '.join(self.subject_keys)})"
        )

    def normalize_claims(self, payload: JSONDict) -> Claims:
        """Map a provider payload onto the documented claims schema.

        :param payload: Raw provider payload.
        :returns: Normalized claims. ``raw`` always carries the input verbatim.
        """
        return {
            "fullname": text(payload, "name", "fullname"),
            "email": text(payload, "email").lower(),
            "email_verified": self._email_verified(payload),
            "picture_url": text(payload, "picture", "avatar_url"),
            "username": text(payload, "preferred_username", "login", "username"),
            "raw": dict(payload),
        }

    def _email_verified(self, payload: JSONDict) -> bool:
        """Decide whether the provider asserts the address is verified.

        Only a literal boolean ``True`` counts: a missing key, ``None``, or
        the string ``"true"`` are all treated as unverified, because a forged
        or sloppy payload must never satisfy the link-by-email gate.

        :param payload: Raw provider payload.
        :returns: Whether the address is verified.
        """
        return payload.get("email_verified") is True

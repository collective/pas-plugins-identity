"""Provider drivers (§4.4).

A driver is static metadata plus claim normalization -- it never performs I/O
and never touches the ZODB, which is what makes the whole layer unit-testable
against recorded payload fixtures with no provider in the loop.

Drivers are registered as named ZCA utilities (D9); the name is the
``driver_id``. Third parties add drivers by registering their own utility.
"""

from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.interfaces import ClaimsError
from pas.plugins.identity.core.interfaces import IDriver
from typing import Any
from zope.component import getUtilitiesFor
from zope.component import queryUtility
from zope.interface import implementer


def _text(payload: dict[str, Any], *keys: str) -> str:
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
_OAUTH_FIELDS: dict[str, dict[str, Any]] = {
    "client_id": {
        "type": "string",
        "title": "Client ID",
        "required": True,
        "secret": False,
    },
    "client_secret": {
        "type": "string",
        "title": "Client secret",
        "required": True,
        "secret": True,
    },
    "scope": {
        "type": "string",
        "title": "Scope",
        "required": False,
        "secret": False,
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

    #: Default value for the ``scope`` config field.
    default_scope: str = ""

    #: Keys tried, in order, to find the provider-side subject.
    subject_keys: tuple[str, ...] = ("sub",)

    #: Extra config fields beyond :data:`_OAUTH_FIELDS`.
    extra_fields: dict[str, dict[str, Any]] = {}  # noqa: RUF012

    def config_schema(self) -> dict[str, Any]:
        """Return the configuration schema for this driver.

        :returns: Mapping of field name to descriptor. Secret fields are
            flagged so every API surface can mask them (I4).
        """
        schema = {k: dict(v) for k, v in _OAUTH_FIELDS.items()}
        schema["scope"]["default"] = self.default_scope
        # S2. Off by default, and even when on it is only ever honoured
        # against this package's own magic-link-verified addresses -- never
        # against another provider's word for it.
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
        }
        for name, descriptor in self.extra_fields.items():
            schema[name] = dict(descriptor)
        return schema

    def subject(self, payload: dict[str, Any]) -> str:
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

    def normalize_claims(self, payload: dict[str, Any]) -> Claims:
        """Map a provider payload onto the documented claims schema.

        :param payload: Raw provider payload.
        :returns: Normalized claims. ``raw`` always carries the input verbatim.
        """
        return {
            "fullname": _text(payload, "name", "fullname"),
            "email": _text(payload, "email").lower(),
            "email_verified": self._email_verified(payload),
            "picture_url": _text(payload, "picture", "avatar_url"),
            "username": _text(payload, "preferred_username", "login", "username"),
            "raw": dict(payload),
        }

    def _email_verified(self, payload: dict[str, Any]) -> bool:
        """Decide whether the provider asserts the address is verified.

        Only a literal boolean ``True`` counts (S2): a missing key, ``None``,
        or the string ``"true"`` are all treated as unverified, because a
        forged or sloppy payload must never satisfy the link-by-email gate.

        :param payload: Raw provider payload.
        :returns: Whether the address is verified.
        """
        return payload.get("email_verified") is True


class GitHubDriver(BaseDriver):
    """GitHub OAuth2.

    GitHub is not an OIDC provider: the subject is the numeric ``id`` from
    ``/user``, and verification of the address comes from ``/user/emails``,
    which the flow merges into the payload as ``email_verified``.
    """

    driver_id = "github"
    title = "GitHub"
    default_scope = "read:user user:email"
    subject_keys = ("id", "node_id")

    extra_fields = {  # noqa: RUF012
        "allowed_groups": {
            "type": "list",
            "title": "Allowed groups",
            "required": False,
            "secret": False,
            "description": "When set, only members of these groups may log in.",
        },
    }

    def normalize_claims(self, payload: dict[str, Any]) -> Claims:
        """Normalize a GitHub ``/user`` payload.

        :param payload: Raw payload.
        :returns: Normalized claims.
        """
        claims = super().normalize_claims(payload)
        # GitHub calls the display name "name" and the login "login"; when a
        # user has set no display name, fall back to the login so the account
        # is not created with an empty fullname.
        if not claims["fullname"]:
            claims["fullname"] = claims["username"]
        return claims


class GoogleDriver(BaseDriver):
    """Google OIDC."""

    driver_id = "google"
    title = "Google"
    default_scope = "openid email profile"
    subject_keys = ("sub",)

    extra_fields = {  # noqa: RUF012
        "hosted_domain": {
            "type": "string",
            "title": "Hosted domain",
            "required": False,
            "secret": False,
            "description": "When set, restrict logins to this Workspace domain.",
        },
        "allowed_groups": {
            "type": "list",
            "title": "Allowed groups",
            "required": False,
            "secret": False,
        },
    }


class GenericOIDCDriver(BaseDriver):
    """Any OIDC provider reachable through discovery."""

    driver_id = "oidc-generic"
    title = "OpenID Connect"
    default_scope = "openid email profile"
    subject_keys = ("sub",)

    extra_fields = {  # noqa: RUF012
        "issuer": {
            "type": "string",
            "title": "Issuer URL",
            "required": True,
            "secret": False,
            "description": "Discovery is fetched from "
            "<issuer>/.well-known/openid-configuration.",
        },
        "allowed_groups": {
            "type": "list",
            "title": "Allowed groups",
            "required": False,
            "secret": False,
        },
        "groups_claim": {
            "type": "string",
            "title": "Groups claim",
            "required": False,
            "secret": False,
            "default": "groups",
        },
    }


class EmailDriver(BaseDriver):
    """Email as an identity source: magic-link login (§1 item 3).

    There is no OAuth client here -- the "provider" is the mailbox -- so the
    config schema drops the OAuth fields entirely and the subject is the
    address itself.
    """

    driver_id = "email"
    title = "Email"
    subject_keys = ("email",)

    def config_schema(self) -> dict[str, Any]:
        """Return the configuration schema for magic-link login.

        :returns: Mapping of field name to descriptor; no secrets, since the
            signing key lives with the plugin rather than in the registry.
        """
        return {
            "token_ttl": {
                "type": "int",
                "title": "Link lifetime (seconds)",
                "required": False,
                "secret": False,
                "default": 900,
            },
            "rate_limit_per_hour": {
                "type": "int",
                "title": "Links per address per hour",
                "required": False,
                "secret": False,
                "default": 5,
            },
        }

    def subject(self, payload: dict[str, Any]) -> str:
        """Return the address, lowercased.

        :param payload: Payload carrying an ``email`` key.
        :returns: The lowercased address.
        :raises ClaimsError: When no address is present.
        """
        return super().subject(payload).lower()

    def normalize_claims(self, payload: dict[str, Any]) -> Claims:
        """Normalize a confirmed magic-link payload.

        Reaching this code means the address was proven by delivery, so
        ``email_verified`` is unconditionally true.

        :param payload: Payload carrying an ``email`` key.
        :returns: Normalized claims.
        """
        claims = super().normalize_claims(payload)
        claims["email_verified"] = True
        return claims


def get_driver(driver_id: str) -> BaseDriver | None:
    """Look up a registered driver.

    :param driver_id: The driver id, e.g. ``github``.
    :returns: The driver utility, or ``None`` when not registered.
    """
    return queryUtility(IDriver, name=driver_id)


def all_drivers() -> dict[str, BaseDriver]:
    """Return every registered driver, keyed by id.

    :returns: Mapping of driver id to driver utility.
    """
    return dict(getUtilitiesFor(IDriver))

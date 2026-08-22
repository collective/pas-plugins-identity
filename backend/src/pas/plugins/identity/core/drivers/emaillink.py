"""The email driver, behind magic-link login.

The module is not called ``email`` because that is the name of a standard
library package, and a driver module that shadows it would be a trap for
anything later added to this package.
"""

from pas.plugins.identity.core.drivers.base import BaseDriver
from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.interfaces import JSONDict


class EmailDriver(BaseDriver):
    """Email as an identity source: magic-link login.

    There is no OAuth client here -- the "provider" is the mailbox -- so the
    config schema drops the OAuth fields entirely and the subject is the
    address itself.
    """

    driver_id = "email"
    title = "Email"
    subject_keys = ("email",)

    def config_schema(self) -> JSONDict:
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

    def subject(self, payload: JSONDict) -> str:
        """Return the address, lowercased.

        :param payload: Payload carrying an ``email`` key.
        :returns: The lowercased address.
        :raises ClaimsError: When no address is present.
        """
        return super().subject(payload).lower()

    def normalize_claims(self, payload: JSONDict) -> Claims:
        """Normalize a confirmed magic-link payload.

        Reaching this code means the address was proven by delivery, so
        ``email_verified`` is unconditionally true.

        :param payload: Payload carrying an ``email`` key.
        :returns: Normalized claims.
        """
        claims = super().normalize_claims(payload)
        claims["email_verified"] = True
        return claims

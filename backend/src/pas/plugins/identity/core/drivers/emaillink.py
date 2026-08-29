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

    #: No link form on the identities page.
    #:
    #: The address a magic link proves is whatever was typed into the box, so
    #: a free-text field there is a way to attach *any* mailbox to your
    #: account -- including one you merely have momentary access to. The
    #: addresses this site will verify are the ones already listed on your
    #: profile, and ``POST @identities`` enforces that; dropping the form is
    #: the same rule stated where a person can see it.
    supports_manual_link = False

    # A mailbox asserts an address and nothing else, so seeding a fullname
    # mapping would only ever resolve to nothing.
    default_propertymap = {"email": "email"}  # noqa: RUF012

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
                "order": 10,
            },
            "rate_limit_per_hour": {
                "type": "int",
                "title": "Links per address per hour",
                "required": False,
                "secret": False,
                "default": 5,
                "order": 20,
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

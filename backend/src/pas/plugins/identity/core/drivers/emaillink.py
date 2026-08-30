"""The email driver, behind magic-link login.

The module is not called ``email`` because that is the name of a standard
library package, and a driver module that shadows it would be a trap for
anything later added to this package.
"""

from pas.plugins.identity.core.drivers.base import BaseDriver
from pas.plugins.identity.core.drivers.settings import IEmailSettings
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
    settings_schema = IEmailSettings
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
        # And in the list too, which the base class built before this line
        # raised the flag. Nothing acts on it -- redeeming the link is what
        # writes the identity that *is* the verification -- but a claims
        # snapshot that says verified in one place and not the other is the
        # kind of disagreement somebody eventually reads as a bug.
        claims["emails"] = self.reported_addresses(claims["email"], True)
        return claims

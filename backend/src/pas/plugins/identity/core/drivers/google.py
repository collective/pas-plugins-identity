"""The Google driver."""

from pas.plugins.identity.core.drivers.base import BaseDriver


class GoogleDriver(BaseDriver):
    """Google OIDC."""

    driver_id = "google"
    title = "Google"
    icon_resource = "pas.plugins.identity.core.drivers:icons/google.svg"
    default_scope = ("openid", "email", "profile")
    subject_keys = ("sub",)

    #: Google's, and not an operator's to type.
    #:
    #: The settings schema asks for no issuer, so this is the only place it
    #: could come from. Discovery still happens against it exactly as it does
    #: for a provider whose issuer somebody configured.
    issuer = "https://accounts.google.com"

    #: Google verifies an address before it will call it verified.
    #:
    #: ``email_verified`` on a Google id_token is false for an address the
    #: account has not proved, and Google does not hand out an account with a
    #: verified address somebody else owns. So an address it vouches for is
    #: recorded as verified here -- the operator can still say otherwise, per
    #: provider.
    default_trust_email_verification = True

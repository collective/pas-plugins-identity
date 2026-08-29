"""The Google driver."""

from pas.plugins.identity.core.drivers.base import BaseDriver


class GoogleDriver(BaseDriver):
    """Google OIDC."""

    driver_id = "google"
    title = "Google"
    default_scope = ("openid", "email", "profile")
    subject_keys = ("sub",)

    #: Google verifies an address before it will call it verified.
    #:
    #: ``email_verified`` on a Google id_token is false for an address the
    #: account has not proved, and Google does not hand out an account with a
    #: verified address somebody else owns. So an address it vouches for is
    #: recorded as verified here -- the operator can still say otherwise, per
    #: provider.
    default_trust_email_verification = True

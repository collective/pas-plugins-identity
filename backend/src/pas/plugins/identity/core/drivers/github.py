"""The GitHub driver."""

from pas.plugins.identity.core.drivers.base import BaseDriver
from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.interfaces import JSONDict


class GitHubDriver(BaseDriver):
    """GitHub OAuth2.

    GitHub is not an OIDC provider: it issues no ``id_token``, so the flow
    falls back to the userinfo endpoint and the subject is the numeric ``id``
    from ``GET /user``.

    **That one call is all this driver gets.** ``/user`` omits the address
    entirely for a user who has set their email to private, and it carries no
    ``email_verified`` at all, so a GitHub identity is never treated as having
    a verified address. ``GET /user/emails`` would answer both -- the scope to
    call it is already requested -- and nothing calls it. Two consequences
    worth knowing rather than discovering:

    * a user with a private address arrives with no email claim, so their
      profile is created ``incomplete`` and the required-information flow asks
      them for one;
    * link-by-verified-email never matches a GitHub identity, whatever the
      account's own verification state.
    """

    driver_id = "github"
    title = "GitHub"
    default_scope = ("read:user", "user:email")
    subject_keys = ("id", "node_id")

    #: The GitHub login, rather than a random id.
    #:
    #: A GitHub login is already the name the person is known by wherever
    #: this site's users talk about each other, and it is unique across the
    #: provider -- so mirroring it produces a Plone userid a human can
    #: recognise instead of 32 hex characters. It is a claim rather than the
    #: subject, so it can change and it can collide with a userid this site
    #: already holds; both are handled where the userid is minted, and the
    #: numeric ``id`` remains the key the identity is stored under either
    #: way.
    default_userid_source = "username"

    def normalize_claims(self, payload: JSONDict) -> Claims:
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

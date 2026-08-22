"""The GitHub driver."""

from pas.plugins.identity.core.drivers.base import BaseDriver
from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.interfaces import JSONDict


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

"""The GitHub driver."""

from pas.plugins.identity.core.drivers.base import BaseDriver
from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.interfaces import JSONDict


class GitHubDriver(BaseDriver):
    """GitHub OAuth2.

    GitHub is not an OIDC provider: it issues no ``id_token``, so the flow
    falls back to the userinfo endpoint and the subject is the numeric ``id``
    from ``GET /user``.

    ``/user`` is not the whole story. It omits the address entirely for a
    user who has marked it private, and it carries no ``email_verified`` at
    all -- so on that call alone a GitHub identity arrives with no email
    claim and is never treated as having a verified address, which also means
    link-by-verified-email can never match one.

    ``GET /user/emails`` answers both, and the ``user:email`` scope needed to
    call it has always been requested here. So the driver names it as its
    enrichment endpoint and :mod:`pas.plugins.identity.core.flows` fetches it
    after userinfo; :meth:`merge_enrichment` folds the chosen address in. The
    driver still performs no I/O of its own.

    A GitHub account may hold several addresses. The primary verified one is
    preferred, then any verified one, and an unverified primary last -- an
    address is worth having even when nobody will auto-link on it.

    The call is best-effort. A token whose scope an operator narrowed answers
    403, and a login is not the moment to fail over an address: the payload is
    then exactly what ``/user`` gave, which is where this driver started.
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

    def enrichment_endpoint(self, metadata: JSONDict) -> str:
        """Return GitHub's address list endpoint.

        :param metadata: The provider's resolved metadata.
        :returns: The ``emails_endpoint`` URL, or empty when the metadata
            predates it.
        """
        return metadata.get("emails_endpoint") or ""

    def merge_enrichment(self, payload: JSONDict, data: object) -> JSONDict:
        """Fold the best address from ``GET /user/emails`` into the payload.

        :param payload: The ``/user`` payload.
        :param data: The decoded address list.
        :returns: The payload, with ``email`` and ``email_verified`` set from
            the chosen address. Unchanged when the answer carries no usable
            address, so a surprising shape costs nothing rather than raising
            in the middle of a login.
        """
        chosen = self._best_address(data)
        if chosen is None:
            return payload
        return {
            **payload,
            "email": chosen.get("email", ""),
            "email_verified": chosen.get("verified") is True,
        }

    @staticmethod
    def _best_address(data: object) -> JSONDict | None:
        """Choose which of an account's addresses to believe.

        :param data: The decoded ``/user/emails`` answer.
        :returns: The chosen entry, or ``None`` when there is nothing usable.
        """
        if not isinstance(data, list):
            return None
        entries = [
            entry
            for entry in data
            if isinstance(entry, dict) and str(entry.get("email", "")).strip()
        ]
        if not entries:
            return None
        for match in (
            lambda e: e.get("primary") is True and e.get("verified") is True,
            lambda e: e.get("verified") is True,
            lambda e: e.get("primary") is True,
        ):
            for entry in entries:
                if match(entry):
                    return entry
        return None

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

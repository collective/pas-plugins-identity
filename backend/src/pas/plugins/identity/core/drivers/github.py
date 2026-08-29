"""The GitHub driver."""

from pas.plugins.identity.core.drivers.base import BaseDriver
from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.interfaces import ProviderEmail


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

    A GitHub account may hold several addresses, and all of them go onto the
    person's Profile. The account's own primary comes first, then the verified
    ones, and that order is only the order they are *offered* in: once
    somebody has arranged their addresses, theirs is the one that stands.

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

    #: GitHub verifies an address before it will call it verified.
    #:
    #: ``GET /user/emails`` reports ``verified`` per address, and GitHub sets
    #: it only once the account has answered mail there. So an address it
    #: vouches for is recorded as verified here -- the operator can still say
    #: otherwise, per provider.
    default_trust_email_verification = True

    def enrichment_endpoint(self, metadata: JSONDict) -> str:
        """Return GitHub's address list endpoint.

        :param metadata: The provider's resolved metadata.
        :returns: The ``emails_endpoint`` URL, or empty when the metadata
            predates it.
        """
        return metadata.get("emails_endpoint") or ""

    #: Key the address list is carried under between the two steps.
    #:
    #: ``merge_enrichment`` cannot return claims -- it hands a *payload* to
    #: ``normalize_claims``, which is the only place that builds claims -- so
    #: the addresses ride in the payload under a name no provider sends.
    #: Prefixed and named for this package so it cannot collide with a real
    #: GitHub field, and stripped out of ``raw`` again on the way through, so
    #: nothing downstream sees an invented key in "the untouched payload".
    ADDRESSES_KEY = "_pas_plugins_identity_addresses"

    def merge_enrichment(self, payload: JSONDict, data: object) -> JSONDict:
        """Fold ``GET /user/emails`` into the payload, all of it.

        Every address the account holds is carried, because every one of them
        goes onto the person's Profile. This used to carry the list only when
        there was more than one and leave ``email`` empty in that case -- the
        address was a question nobody could answer for the user, so they were
        held on a form until they did. They have a list now, so there is
        nothing to withhold: all the addresses are theirs, and which of them
        stands for them is an order they can change rather than a question
        blocking their first login (Érico, 2026-08-29).

        ``email`` is the head of the list, which is the account's own primary
        address where GitHub named one.

        :param payload: The ``/user`` payload.
        :param data: The decoded address list.
        :returns: The payload with the addresses folded in, under ``email``
            and under :attr:`ADDRESSES_KEY`. Unchanged when the answer carries
            no usable address, so a surprising shape costs nothing rather than
            raising in the middle of a login.
        """
        entries = self._addresses(data)
        if not entries:
            return payload
        head = entries[0]
        return {
            **payload,
            "email": head["address"],
            "email_verified": head["verified"],
            self.ADDRESSES_KEY: entries,
        }

    @staticmethod
    def _addresses(data: object) -> list[ProviderEmail]:
        """Normalize ``GET /user/emails`` into addresses worth offering.

        Ordered the way they should be offered: the account's primary address
        first, verified ones ahead of unverified, and GitHub's own order
        preserved within each group so a stable list stays stable.

        :param data: The decoded ``/user/emails`` answer.
        :returns: The addresses, empty when there is nothing usable.
        """
        if not isinstance(data, list):
            return []
        entries: list[ProviderEmail] = []
        seen: set[str] = set()
        for entry in data:
            if not isinstance(entry, dict):
                continue
            address = str(entry.get("email", "")).strip().lower()
            if not address or address in seen:
                continue
            seen.add(address)
            entries.append({
                "address": address,
                "verified": entry.get("verified") is True,
                "primary": entry.get("primary") is True,
            })
        # `sorted` is stable, so equal keys keep the provider's order.
        return sorted(entries, key=lambda e: (not e["primary"], not e["verified"]))

    def normalize_claims(self, payload: JSONDict) -> Claims:
        """Normalize a GitHub ``/user`` payload.

        :param payload: Raw payload.
        :returns: Normalized claims. ``emails`` carries every address the
            account holds when ``GET /user/emails`` was reachable, and the one
            entry the base class synthesizes from ``/user`` alone when it was
            not.
        """
        claims = super().normalize_claims(payload)
        reported = payload.get(self.ADDRESSES_KEY)
        if isinstance(reported, list) and reported:
            claims["emails"] = tuple(reported)
            # `raw` is documented as the untouched provider payload, so the
            # key this package added on the way through does not belong in it.
            claims["raw"] = {
                key: value
                for key, value in claims.get("raw", {}).items()
                if key != self.ADDRESSES_KEY
            }
        # GitHub calls the display name "name" and the login "login"; when a
        # user has set no display name, fall back to the login so the account
        # is not created with an empty fullname.
        if not claims["fullname"]:
            claims["fullname"] = claims["username"]
        return claims

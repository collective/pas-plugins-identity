"""The GitHub driver."""

from pas.plugins.identity.core.drivers.base import BaseDriver
from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.interfaces import EmailChoice
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
        """Fold ``GET /user/emails`` into the payload without choosing.

        **One address is an answer; several are a question.** An account with
        a single usable address has nothing to decide, so it fills ``email``
        exactly as a provider that sent one would. An account with more than
        one is the case this exists for: picking the primary, or the first
        verified one, is a guess made on the user's behalf about which
        identity they are here as -- and the address decides which existing
        account a verified-email link would attach to. So the list is carried
        forward and the user is asked, on their profile, once they are in.

        :param payload: The ``/user`` payload.
        :param data: The decoded address list.
        :returns: The payload, with either the single address folded in or
            the whole list attached under :attr:`ADDRESSES_KEY`. Unchanged
            when the answer carries no usable address, so a surprising shape
            costs nothing rather than raising in the middle of a login.
        """
        entries = self._addresses(data)
        if not entries:
            return payload
        if len(entries) == 1:
            only = entries[0]
            return {
                **payload,
                "email": only["address"],
                "email_verified": only["verified"],
            }
        return {**payload, self.ADDRESSES_KEY: entries}

    @staticmethod
    def _addresses(data: object) -> list[EmailChoice]:
        """Normalize ``GET /user/emails`` into addresses worth offering.

        Ordered the way the choice should be presented: the account's primary
        address first, verified ones ahead of unverified, and the provider's
        own order preserved within each group so a stable list stays stable.

        :param data: The decoded ``/user/emails`` answer.
        :returns: The addresses, empty when there is nothing usable.
        """
        if not isinstance(data, list):
            return []
        entries: list[EmailChoice] = []
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
        :returns: Normalized claims. ``email_choices`` is populated, and
            ``email`` deliberately left empty, when the account offers more
            than one address: the user is asked which one on their profile
            rather than having one picked for them here.
        """
        claims = super().normalize_claims(payload)
        choices = payload.get(self.ADDRESSES_KEY)
        if isinstance(choices, list) and choices:
            claims["email_choices"] = tuple(choices)
            # No address until the user names one. Leaving a guess in here is
            # exactly what the choice exists to avoid, and an empty `email`
            # is what makes the profile `incomplete` and holds them on the
            # form that asks.
            claims["email"] = ""
            claims["email_verified"] = False
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

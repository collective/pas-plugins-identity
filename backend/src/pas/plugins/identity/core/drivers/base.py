"""Common behavior shared by every provider driver.

A driver is static metadata plus claim normalization -- it never performs I/O
and never touches the ZODB, which is what makes the whole layer unit-testable
against recorded payload fixtures with no provider in the loop.
"""

from pas.plugins.identity.core.drivers.settings import IDriverSettings
from pas.plugins.identity.core.drivers.settings import IOAuth2Settings
from pas.plugins.identity.core.interfaces import Claims
from pas.plugins.identity.core.interfaces import ClaimsError
from pas.plugins.identity.core.interfaces import IDriver
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.interfaces import ProviderEmail
from zope.interface import implementer


def text(payload: JSONDict, *keys: str) -> str:
    """Return the first non-empty string among ``keys``.

    :param payload: Provider payload.
    :param keys: Candidate keys, in order of preference.
    :returns: The value, or an empty string when none is usable.
    """
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


@implementer(IDriver)
class BaseDriver:
    """Common behavior for drivers.

    Subclasses declare :attr:`driver_id`, :attr:`title`, the extra config
    fields they need, and how to read a subject out of a payload.
    """

    driver_id: str = ""
    title: str = ""

    #: The schema an operator fills in for a provider using this driver.
    #:
    #: An ``Interface``, serialized by ``@identity-drivers`` through
    #: ``plone.restapi``'s own machinery -- so a form is built from it the way
    #: a form is built from anything else in Plone, in the site's language,
    #: with validation, and by Classic UI as readily as by Volto. See
    #: :mod:`pas.plugins.identity.core.drivers.settings` for what replaced the
    #: hand-built dict this used to be.
    settings_schema: type[IDriverSettings] = IOAuth2Settings

    #: Default for the ``userid_source`` config field.
    #:
    #: A class attribute rather than a field default in the schema, so a
    #: driver that knows something about its provider can move it. A random
    #: id is right for a provider this site has no particular trust in; a peer
    #: running this same package is a different case.
    default_userid_source: str = "uuid"

    #: Default value for the ``scope`` config field, one token per entry.
    #:
    #: A tuple rather than the space-joined string OAuth 2 puts on the wire:
    #: a scope is a list of permissions, and typing them into one text box is
    #: how a trailing space or a comma becomes a scope of its own that the
    #: provider then rejects as unknown.
    default_scope: tuple[str, ...] = ()

    #: Keys tried, in order, to find the provider-side subject.
    subject_keys: tuple[str, ...] = ("sub",)

    #: Claim this provider's groups arrive in, or ``""`` for none.
    #:
    #: Empty on the base class, and that is what switches the whole feature
    #: off for a driver: no ``group_claim`` field appears in the config
    #: schema, so an operator is not offered a mapping for a provider that
    #: has no groups to map. GitHub organisations and a magic link are both
    #: this case.
    default_group_claim: str = ""

    #: Seeded into a new provider's group map.
    #:
    #: Almost always empty, and honestly so: group names are a fact about one
    #: deployment's directory, not about a driver. A driver only fills this in
    #: when it knows the far end ships a group by that name.
    default_groupmap: dict[str, str] = {}  # noqa: RUF012

    #: Whether this provider's own ``email_verified`` is worth anything here.
    #:
    #: False on the base class, which is the answer for a provider nobody has
    #: said anything about: its word is carried and shown, and it proves
    #: nothing. A driver sets this where the provider actually does verify --
    #: Google and GitHub both do, and both refuse to call an address verified
    #: until the account has answered mail at it.
    #:
    #: It is only the *default* for the ``trust_email_verification`` config
    #: field, because whether a given deployment trusts a given provider is a
    #: fact about the deployment. An operator running a permissive OIDC
    #: provider of their own can switch it on; one who does not trust GitHub
    #: can switch it off.
    default_trust_email_verification: bool = False

    #: Whether a user may start a link against this provider from a form.
    #:
    #: True for every redirect flow: the identities page offers a button, the
    #: browser goes to the provider, and what comes back is proof. False for
    #: a driver whose subject is something the *user types* -- an address --
    #: because a free-text box there is a box for verifying any address at
    #: all, not one of your own. Magic link is that case, and its addresses
    #: come from the profile instead.
    supports_manual_link: bool = True

    #: Seeded into a new provider's attribute mapping.
    #:
    #: Written against the *normalized* claim names rather than any one
    #: provider's -- ``resolve_claim`` tries those before the raw payload, so
    #: ``fullname`` reaches GitHub's ``login`` fallback and an OIDC
    #: ``preferred_username`` alike without either being named here.
    #:
    #: Only the two claims every provider offers are mapped here. A site's
    #: member schema carries more than that -- ``home_page``, ``location``,
    #: ``portrait`` -- but which of them a given provider can actually fill
    #: is a fact about the provider, so a driver that knows adds them. What
    #: no driver may add is ``username``: providers publish it, Plone has no
    #: member field for it, and the mapping would resolve to nothing on every
    #: login while looking correct in the form.
    default_propertymap: dict[str, str] = {  # noqa: RUF012
        "email": "email",
        "fullname": "fullname",
    }

    def subject(self, payload: JSONDict) -> str:
        """Extract the immutable provider-side subject identifier.

        :param payload: Raw provider payload.
        :returns: The subject as a string.
        :raises ClaimsError: When no usable subject is present.
        """
        for key in self.subject_keys:
            value = payload.get(key)
            # Providers are inconsistent about numeric ids; normalize to str.
            if isinstance(value, int) and not isinstance(value, bool):
                return str(value)
            if isinstance(value, str) and value.strip():
                return value.strip()
        raise ClaimsError(
            f"{self.driver_id}: payload carries no subject "
            f"(tried {', '.join(self.subject_keys)})"
        )

    def enrichment_endpoint(self, metadata: JSONDict) -> str:
        """Return a second endpoint whose answer completes the payload.

        Some providers do not put everything on their userinfo endpoint.
        A driver names the extra endpoint here and merges its answer in
        :meth:`merge_enrichment`; the fetch itself belongs to
        :mod:`pas.plugins.identity.core.flows`, because a driver performs no
        I/O -- that is what lets every driver be tested against a recorded
        payload with no provider in the loop.

        :param metadata: The provider's resolved metadata.
        :returns: An absolute URL, or an empty string for the providers whose
            userinfo endpoint is the whole story.
        """
        return ""

    def merge_enrichment(self, payload: JSONDict, data: object) -> JSONDict:
        """Fold the enrichment answer into the payload.

        :param payload: The userinfo payload.
        :param data: Whatever :meth:`enrichment_endpoint` answered, decoded.
        :returns: The payload to normalize claims from.
        """
        return payload

    def normalize_claims(self, payload: JSONDict) -> Claims:
        """Map a provider payload onto the documented claims schema.

        :param payload: Raw provider payload.
        :returns: Normalized claims. ``raw`` always carries the input verbatim,
            and ``emails`` always carries a list -- one entry for the single
            address most providers send, so nothing downstream has to branch
            on how many a provider happens to offer.
        """
        email = text(payload, "email").lower()
        verified = self._email_verified(payload)
        return {
            "fullname": text(payload, "name", "fullname"),
            "email": email,
            "email_verified": verified,
            "emails": self.reported_addresses(email, verified),
            "picture_url": text(payload, "picture", "avatar_url"),
            "username": text(payload, "preferred_username", "login", "username"),
            "raw": dict(payload),
        }

    @staticmethod
    def reported_addresses(email: str, verified: bool) -> tuple[ProviderEmail, ...]:
        """Return the address list for a provider that sends one address.

        The common case, and the reason it is a list at all: a Profile takes
        every address a provider reports, so a driver that offers several --
        GitHub does -- and one that offers one hand the same shape to the same
        code.

        :param email: The normalized address, or the empty string.
        :param verified: Whether the provider says it checked it.
        :returns: One entry, or none at all when the provider sent no address.
        """
        if not email:
            return ()
        return ({"address": email, "verified": verified, "primary": True},)

    def _email_verified(self, payload: JSONDict) -> bool:
        """Decide whether the provider asserts the address is verified.

        Only a literal boolean ``True`` counts: a missing key, ``None``, or
        the string ``"true"`` are all treated as unverified, because a forged
        or sloppy payload must never satisfy the link-by-email gate.

        :param payload: Raw provider payload.
        :returns: Whether the address is verified.
        """
        return payload.get("email_verified") is True

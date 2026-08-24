"""Interfaces and typed structures for the core layer.

Everything a consumer of this package needs to talk to the identity store, to
write a driver, or to plug in an audit sink is declared here.
"""

from typing import Protocol
from typing import TypedDict
from zope.interface import Attribute
from zope.interface import Interface


#: Any value that survives a JSON round trip.
type JSONValue = (
    str | int | float | bool | list[JSONValue] | dict[str, JSONValue] | None
)

#: A JSON object: a provider payload, a driver's config schema, a reply body.
type JSONDict = dict[str, JSONValue]


class Claims(TypedDict, total=False):
    """Driver-normalized claims about an external identity.

    Drivers map provider payloads onto this schema; consumers -- the claims
    sync subscriber, the audit log, the events -- read only these keys.

    :ivar fullname: Human readable name, empty string when unknown.
    :ivar email: Email address as reported by the provider.
    :ivar email_verified: Whether the provider asserts the address is verified.
    :ivar picture_url: URL of an avatar image.
    :ivar username: Provider-side login name.
    :ivar raw: The untouched provider payload, for driver-specific consumers.
    """

    fullname: str
    email: str
    email_verified: bool
    picture_url: str
    username: str
    raw: JSONDict


class IDriver(Interface):
    """A provider driver: static metadata plus claim normalization.

    Drivers are registered as named utilities, under their ``driver_id``. A
    driver is stateless: it describes *how* to talk to a family of providers,
    while the per-site configuration lives in the registry.
    """

    driver_id = Attribute("Unique id, e.g. ``github``. Matches the utility name.")

    title = Attribute("Human readable title shown in the control panel.")

    default_propertymap = Attribute(
        "Claim path to user field, seeded into a new provider's mapping. "
        "Written against the normalized claim names where it can be, so a "
        "driver only names a raw claim for something normalization does not "
        "already produce."
    )

    def config_schema() -> JSONDict:
        """Return the configuration schema for this driver.

        :returns: Mapping of field name to a descriptor with at least
            ``type``, ``title``, ``required`` and ``secret`` keys. The Volto
            control panel widget is generated from this.
        """

    def normalize_claims(payload: JSONDict) -> Claims:
        """Map a provider payload onto the documented claims schema.

        :param payload: Raw userinfo/profile payload from the provider.
        :returns: Normalized claims.
        """

    def subject(payload: JSONDict) -> str:
        """Extract the immutable provider-side subject identifier.

        :param payload: Raw userinfo/profile payload from the provider.
        :returns: The subject, stable for the lifetime of the account.
        :raises ValueError: When the payload carries no usable subject.
        """


class IIdentityStore(Interface):
    """Bidirectional map between external identities and canonical userids.

    ``(provider, subject)`` resolves to exactly one userid; a userid owns
    zero or more identity records. Implementations persist inside the PAS
    plugin object.
    """

    def userid_for(provider: str, subject: str) -> str | None:
        """Resolve an external identity to a canonical userid.

        :param provider: Provider id, e.g. ``github``.
        :param subject: Provider-side subject identifier.
        :returns: The userid, or ``None`` when the identity is unknown.
        """

    def identities_for(userid: str) -> tuple:
        """Return every identity record owned by a userid.

        :param userid: Canonical Plone userid.
        :returns: Tuple of :class:`~pas.plugins.identity.core.store.IdentityRecord`.
        """

    def add(provider: str, subject: str, userid: str, claims: Claims):
        """Link an external identity to a userid.

        :param provider: Provider id.
        :param subject: Provider-side subject identifier.
        :param userid: Canonical Plone userid.
        :param claims: Normalized claims snapshot.
        :returns: The stored record.
        :raises IdentityCollision: When the identity is already owned by a
            different userid.
        """

    def remove(provider: str, subject: str) -> None:
        """Unlink an external identity.

        :param provider: Provider id.
        :param subject: Provider-side subject identifier.
        :raises KeyError: When the identity is unknown.
        """

    def touch(provider: str, subject: str, claims: Claims):
        """Record a successful login against an existing identity.

        :param provider: Provider id.
        :param subject: Provider-side subject identifier.
        :param claims: Fresh normalized claims, replacing the stored ones.
        :returns: The updated record.
        """


class IAuditSink(Interface):
    """Destination for authentication events."""

    def record(
        userid: str | None,
        event: str,
        provider: str,
        success: bool,
        detail: JSONDict | None = None,
    ) -> None:
        """Append one authentication event.

        :param userid: Userid the event concerns, ``None`` when unresolved.
        :param event: Event name, e.g. ``authenticated`` or ``link-collision``.
        :param provider: Provider id involved.
        :param success: Whether the attempt succeeded.
        :param detail: Extra, non-credential context. Never tokens.
        """

    def entries(userid: str | None = None) -> list:
        """Return recorded entries, newest first.

        :param userid: Restrict to one user; ``None`` returns site-wide.
        :returns: List of audit entries.
        """


class IOwnsUserProperties(Interface):
    """Marker for a PAS plugin that owns where user properties are stored.

    Declared in core and implemented by an optional layer, which is the only
    direction the import-linter contract allows -- and the only one that makes
    sense: core has to be able to ask the question on a site where nothing
    answers it.

    A plugin claiming this says two things. Its property sheet is the
    authoritative one for the users it serves, and it applies the provider's
    property map to them itself. Core's own
    :meth:`~pas.plugins.identity.core.pas.plugin.IdentityPlugin._apply_property_map`
    therefore stands aside rather than writing through the sheet: both would
    be writing the same fields from the same map, and only one of them knows
    which of those fields a human has since edited.
    """


class IIdentityPlugin(Interface):
    """Marker for the PAS plugin provided by this package."""


class IdentityCollision(Exception):
    """An external identity is already linked to a different userid."""


class LockoutRefused(Exception):
    """Unlinking would leave the account with no way to authenticate."""


class ClaimsError(ValueError):
    """A provider payload could not be normalized."""


class FlowError(Exception):
    """An OAuth/OIDC flow failed a security precondition."""


class RateLimited(Exception):
    """A rate-limited endpoint refused the request."""


class DriverProtocol(Protocol):
    """Static-typing counterpart to :class:`IDriver`."""

    driver_id: str
    title: str
    default_propertymap: dict[str, str]

    def config_schema(self) -> JSONDict: ...

    def normalize_claims(self, payload: JSONDict) -> Claims: ...

    def subject(self, payload: JSONDict) -> str: ...

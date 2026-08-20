"""Interfaces and typed structures for the core layer.

Everything a consumer of this package needs to talk to the identity store, to
write a driver, or to plug in an audit sink is declared here.
"""

from typing import Any
from typing import Protocol
from typing import TypedDict
from zope.interface import Attribute
from zope.interface import Interface


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
    raw: dict[str, Any]


class IDriver(Interface):
    """A provider driver: static metadata plus claim normalization.

    Drivers are registered as named utilities (D9). A driver is stateless: it
    describes *how* to talk to a family of providers, while the per-site
    configuration lives in the registry (§4.5).
    """

    driver_id = Attribute("Unique id, e.g. ``github``. Matches the utility name.")

    title = Attribute("Human readable title shown in the control panel.")

    def config_schema() -> dict[str, Any]:
        """Return the configuration schema for this driver.

        :returns: Mapping of field name to a descriptor with at least
            ``type``, ``title``, ``required`` and ``secret`` keys. The Volto
            control panel widget is generated from this.
        """

    def normalize_claims(payload: dict[str, Any]) -> Claims:
        """Map a provider payload onto the documented claims schema.

        :param payload: Raw userinfo/profile payload from the provider.
        :returns: Normalized claims.
        """

    def subject(payload: dict[str, Any]) -> str:
        """Extract the immutable provider-side subject identifier.

        :param payload: Raw userinfo/profile payload from the provider.
        :returns: The subject, stable for the lifetime of the account.
        :raises ValueError: When the payload carries no usable subject.
        """


class IIdentityStore(Interface):
    """Bidirectional map between external identities and canonical userids.

    ``(provider, subject)`` resolves to exactly one userid (I3); a userid owns
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
            different userid (I3, S3).
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
        :param claims: Fresh normalized claims, stored per D2.
        :returns: The updated record.
        """


class IAuditSink(Interface):
    """Destination for authentication events (§4.6)."""

    def record(
        userid: str | None,
        event: str,
        provider: str,
        success: bool,
        detail: dict[str, Any] | None = None,
    ) -> None:
        """Append one authentication event.

        :param userid: Userid the event concerns, ``None`` when unresolved.
        :param event: Event name, e.g. ``authenticated`` or ``link-collision``.
        :param provider: Provider id involved.
        :param success: Whether the attempt succeeded.
        :param detail: Extra, non-credential context. Never tokens (I4).
        """

    def entries(userid: str | None = None) -> list:
        """Return recorded entries, newest first.

        :param userid: Restrict to one user; ``None`` returns site-wide.
        :returns: List of audit entries.
        """


class IIdentityPlugin(Interface):
    """Marker for the PAS plugin provided by this package."""


class IdentityCollision(Exception):
    """An external identity is already linked to a different userid (I3)."""


class LockoutRefused(Exception):
    """Unlinking would leave the account with no way to authenticate (S4)."""


class ClaimsError(ValueError):
    """A provider payload could not be normalized."""


class FlowError(Exception):
    """An OAuth/OIDC flow failed a security precondition (S1)."""


class RateLimited(Exception):
    """A rate-limited endpoint refused the request (S5)."""


class DriverProtocol(Protocol):
    """Static-typing counterpart to :class:`IDriver`."""

    driver_id: str
    title: str

    def config_schema(self) -> dict[str, Any]: ...

    def normalize_claims(self, payload: dict[str, Any]) -> Claims: ...

    def subject(self, payload: dict[str, Any]) -> str: ...

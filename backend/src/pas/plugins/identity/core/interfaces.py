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


class IUserContent(Interface):
    """Marker for a Dexterity content type whose objects *are* users.

    Declared in core and provided by an optional layer's content type, which
    is the direction the import-linter contract allows and the only one that
    works: core has to be able to create such an object on a site whose type
    it has never heard of.

    A type claiming this promises three attributes and one thing about
    where its objects live, and core reads nothing else.

    ``userid`` is the canonical Plone userid, assigned once and never
    changed, because an identity, a local role assignment and a catalog
    entry all point at it. ``login`` is the name the person signs in with.
    ``group_ids`` names the groups the user belongs to -- membership lives on
    the *member*, because ``getGroupsForPrincipal`` runs on every permission
    check that touches a local role while listing a group's members does not.

    The object's **id within its container is the userid**. That is what lets
    core find a user in one traversal instead of a scan, and it is not a
    constraint invented for this interface: an opaque userid never changes,
    so the object never has to be renamed, and a rename is the one operation
    that strands a URL somebody bookmarked.

    A layer that stores membership some other way should implement
    ``IGroupManagement`` itself rather than claim this.

    Core checks the marker before creating anything, so a registry record
    naming a ``Document`` is refused rather than producing an object that
    every user-facing query would then have to tolerate.

    Providing this does *not* make a type a credential store. Where the
    password lives is a separate question with a separate answer -- see
    :attr:`~pas.plugins.identity.core.controlpanel.interfaces.IIdentitySettings.user_content_type`.
    """

    userid = Attribute("The canonical Plone userid. Assigned once.")
    login = Attribute("The name this user signs in with.")
    group_ids = Attribute("Ids of the groups this user belongs to.")


class ICredentialStorage(Interface):
    """An object that can hold its own password.

    Optional, and off unless a site opts in. Core writes a new user's
    password to ``source_users`` by default, because a Dexterity *field*
    holding a credential is serialized by ``plone.restapi``, exported by
    GenericSetup, indexable, and snapshotted by versioning -- four separate
    paths that each fail by disclosing it, and each of which has to be
    remembered separately.

    A layer that would rather keep the credential with the rest of the user
    provides this instead, takes on those four questions deliberately, and
    core then has nothing to delegate.

    Adapted from the created object, so a site decides per content type
    rather than globally.
    """

    def set_password(password: str) -> None:
        """Store a password, hashed.

        :param password: The plaintext, as PAS was given it.
        """

    def check_password(password: str) -> bool:
        """Report whether a password matches the stored one.

        :param password: The plaintext to check.
        :returns: Whether it matches. False when nothing is stored.
        """


class IGroupContent(Interface):
    """Marker for a Dexterity content type whose objects *are* groups.

    The counterpart of :class:`IUserContent`, and the same bargain: core
    declares it, an optional layer's type provides it, and core creates and
    deletes such objects without knowing what they are.

    ``group_id`` is the canonical group id, and as with a user the object's
    id within its container is that value.

    A group does **not** carry its members. They are named by each user's
    ``group_ids``, which is the direction Plone asks the question in.

    Group nesting is out of scope, and core refuses it rather than storing
    something it cannot answer: a group whose members are groups makes
    ``getGroupsForPrincipal`` recursive, and a recursive answer computed from
    catalog metadata stops being a single lookup.
    """

    group_id = Attribute("The canonical group id. Assigned once.")


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


class ProviderUnusable(FlowError):
    """A provider cannot start a redirect flow at all.

    Distinct from its parent, and from a network failure, because the
    condition is permanent: the driver publishes no authorization endpoint,
    or the operator has configured no issuer to discover one from. Retrying
    changes nothing, so a caller must not be told the provider is
    temporarily unavailable.
    """


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


class IProfileSupport(Interface):
    """What the optional ``[profile]`` layer answers for core.

    Core may not import that layer -- an import-linter contract says so, and
    the reason is that ``core`` has to install and run without it. But core
    genuinely has three questions whose answer *changes* when the layer is
    there: where a user's Profile is, which picture represents them, and
    where a picture should be stored.

    A utility rather than a soft import inside a function. That was how the
    first two were answered, and it broke the contract: import-linter reads
    function bodies too, so the boundary was violated in fact while looking
    like it was being respected. This is the same shape the back-channel
    logout already uses to reach the ``[server]`` layer -- core declares
    what it needs, the layer registers something that provides it, and the
    dependency points the way the contract requires.

    Absent on a site without the extra, and
    :func:`~zope.component.queryUtility` returning ``None`` is the answer
    "there is no profile layer here" -- which is exactly what the soft
    import's ``ImportError`` used to mean.
    """

    def profile_url(userid: str) -> str | None:
        """Return the URL of a user's Profile.

        :param userid: Canonical Plone userid.
        :returns: The absolute URL, or ``None`` when the user has none.
        """

    def picture_url(userid: str) -> str | None:
        """Return the URL of the picture held on a user's Profile.

        :param userid: Canonical Plone userid.
        :returns: An absolute URL, or ``None`` when the Profile has no
            picture -- which is what makes the member portrait the fallback
            rather than something this has to know about.
        """

    def store_provider_picture(userid: str, data: bytes, url: str) -> bool:
        """Store a provider's avatar on a user's Profile.

        :param userid: Canonical Plone userid.
        :param data: The image bytes, already fetched and vetted.
        :param url: The ``picture_url`` claim they came from, remembered so
            a later sync can tell its own picture from one the user chose.
        :returns: Whether it was stored. ``False`` means the user has no
            Profile, or has a picture of their own there -- and in both
            cases the caller stores the member portrait instead.
        """

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


class ProviderEmail(TypedDict):
    """One address a provider reports for an account.

    :ivar address: The address itself, lowercased.
    :ivar verified: Whether the provider says it checked it. What that is
        worth here is the operator's decision, per provider: see
        ``trust_email_verification`` in
        :attr:`~pas.plugins.identity.core.drivers.base.BaseDriver.settings_schema`.
        A provider the site does not trust still has its word carried and
        shown; it simply proves nothing.
    :ivar primary: Whether the provider calls it the account's main address.
        It orders the list a Profile is seeded from, and nothing after that:
        once somebody has arranged their own addresses, the order is theirs.
    """

    address: str
    verified: bool
    primary: bool


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
    :ivar emails: Every address the provider reports for this account, in the
        order it should be offered -- the account's own primary first, then
        the ones it says it verified. Not a claim any provider sends and not
        an OIDC name: it is this package's own, and a driver whose provider
        sends a single address fills it with that one entry so nothing
        downstream has to ask which shape it is looking at. ``email`` stays
        the headline address and is the first entry.

        A person has more than one address, and picking one of them for them
        is a decision about which identity they are here as. So all of them
        go onto the Profile and the person arranges them; see
        :func:`~pas.plugins.identity.core.subscribers.sync_addresses`.
    """

    fullname: str
    email: str
    email_verified: bool
    picture_url: str
    username: str
    raw: JSONDict
    emails: tuple[ProviderEmail, ...]


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

    default_group_claim = Attribute(
        'Claim the provider\'s groups arrive in, or ``""`` when it has '
        "none. Empty switches the feature off for the driver: no "
        "``group_claim`` field is offered, so nobody is asked to map groups "
        "for a provider that has none."
    )

    default_groupmap = Attribute(
        "Provider group name to local group id, seeded into a new provider's "
        "map. Almost always empty: group names are a fact about one "
        "deployment's directory, not about a driver."
    )

    settings_schema = Attribute(
        "The ``Interface`` an operator fills in for a provider using this "
        "driver. Serialized by ``@identity-drivers`` through "
        "``plone.restapi``'s own schema machinery, so a form is built from it "
        "the way a form is built from anything else in Plone -- translated, "
        "validated, and by Classic UI as readily as by Volto. Extend "
        "``IOAuth2Settings`` for an OAuth2 provider, or ``IDriverSettings`` "
        "for something that is not one."
    )

    default_trust_email_verification = Attribute(
        "Whether this provider's own ``email_verified`` is worth anything "
        "here, as the default for the ``trust_email_verification`` config "
        "field. False unless a driver knows the provider really checks; "
        "whether a given deployment agrees is the operator's to say."
    )

    supports_manual_link = Attribute(
        "Whether a user may start a link against this provider from a form "
        "on their identities page. True for every redirect flow; false for a "
        "driver whose subject is something the user types, since a free-text "
        "box there verifies any value rather than one already known to be "
        "theirs."
    )

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
    property map to them itself.

    **Core no longer asks.** It used to: a fallback on the login path wrote
    the mapped claims into ``portal_memberdata`` for a user nobody had
    claimed, and this marker is what made it stand aside for one who had.
    Every authenticated user gets a Profile now -- the layer that mints them
    is not optional -- so the fallback was unreachable and was removed rather
    than left as a branch no site can take.

    The marker stays because it is the *layer's* declaration about its own
    sheet, and it is still true: a sheet at the top of the
    ``IPropertiesPlugin`` order that wins reads is saying exactly this. What
    it no longer does is switch off a second writer, because there is no
    second writer.
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
    A type gets it from the
    :class:`~pas.plugins.identity.core.behaviors.membership.IGroupMembership` behavior
    rather than by declaring the field again.

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
    # ``group_ids`` is deliberately *not* an ``Attribute`` here, though the
    # contract above promises it. Dexterity answers a missing attribute from
    # the schema's field default, and it finds the type's own schema first --
    # so an ``Attribute`` inherited from this marker shadows the behavior's
    # real field, and the lookup then dies on ``Attribute.default``, which
    # does not exist. The symptom is ``profile.group_ids`` raising
    # AttributeError on an object that has simply never had one written.


class ICredentialStorage(Interface):
    """An object that can hold its own password.

    Optional, and off unless a site opts in. Core writes a new user's
    password to ``source_users`` by default, because a Dexterity *field*
    holding a credential is serialized by ``plone.restapi``, exported by
    GenericSetup, indexable, and snapshotted by versioning -- four separate
    paths that each fail by disclosing it, and each of which has to be
    remembered separately. An annotation closes the first three by
    construction; versioning needs a guard, which
    :mod:`pas.plugins.identity.core.versioning` installs.

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

    ``group_ids`` on a *group* is the other end of the same idea: the groups
    this group is nested inside. Everybody in the inner group is in every
    group it names, so membership stays a fact stored on the member whether
    the member is a person or a group, and the transitive answer is a walk
    over one field rather than a second kind of edge. See
    :mod:`pas.plugins.identity.core.utils.nesting`.
    """

    group_id = Attribute("The canonical group id. Assigned once.")
    # ``group_ids`` is not declared here either, for the reason spelled out
    # on :class:`IUserContent`.


class IIdentityPlugin(Interface):
    """Marker for the PAS plugin provided by this package."""


class IdentityCollision(Exception):
    """An external identity is already linked to a different userid."""


class LockoutRefused(Exception):
    """Unlinking would leave the account with no way to authenticate."""


class PrincipalUnavailable(Exception):
    """Authentication succeeded and produced a userid nothing can serve.

    A login mints a userid and something is supposed to become the account
    the rest of Plone can see: a ``source_users`` row on an ordinary site,
    and on a site that keeps its users as content, the object -- created by
    whatever the site configured to claim it. When nothing does, PAS still
    answers with a principal and every later lookup of it returns ``None``.

    That state is a site configuration this package cannot fix from inside a
    login, and it is raised rather than returned because the alternative is
    what it replaced: an ``AttributeError`` on ``NoneType`` from whichever
    line happened to touch the user first.
    """


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
    settings_schema: type[Interface]
    default_propertymap: dict[str, str]
    default_group_claim: str
    default_groupmap: dict[str, str]
    default_scope: tuple[str, ...]
    default_userid_source: str
    default_trust_email_verification: bool

    def normalize_claims(self, payload: JSONDict) -> Claims: ...

    def subject(self, payload: JSONDict) -> str: ...


class IIdentityCatalogued(Interface):
    """Marker for anything filed in the dedicated identity catalog.

    Both content types this package defines carry it, so the indexing
    subscribers are registered once for the pair rather than twice for each.
    """


class IUserProfile(IIdentityCatalogued):
    """Marker for the UserProfile content type.

    Applied through the class rather than the FTI so that the catalog
    subscribers bind to it however the object was constructed -- including by
    a test that instantiates it directly.
    """


class IUserGroup(IIdentityCatalogued):
    """Marker for the UserGroup content type."""


class IIdentityProfileCatalog(Interface):
    """Marker for the dedicated Profile catalog tool.

    The tool is looked up by this interface rather than by id, so a
    deployment may replace it wholesale.
    """

"""Which content types this site keeps its users and groups in.

``UserProfile`` and ``UserGroup`` are this package's own types, and a site may
replace either with one of its own by naming it in a registry record. Every
path that creates, finds or walks principals asks here rather than naming the
type itself, so a site running its own user type gets its own objects
catalogued, enumerated, exported and checked -- not a ``UserProfile`` created
beside each of them.

An empty record reads as this package's own type. That is a statement about
*where to look*, and it is not the same question as whether adding a user or a
group creates content at all: the adder paths in
:class:`~pas.plugins.identity.core.pas.plugin.IdentityPlugin` read the record
itself, and an empty one there still hands the job to ``source_users`` or
``source_groups``. A site with no content groups therefore searches for
``UserGroup`` objects and finds none, which is the right answer.

A type the Profile layer manages has to provide
:class:`~pas.plugins.identity.core.interfaces.IUserProfile` (or
``IUserGroup``): that is what the indexers and the catalog subscribers are
registered for. :func:`type_provides` answers that from the FTI, before
anything is created.

A leaf module, importing nothing from this package, because both the catalog
and the PAS plugin need it and the plugin already imports the catalog.
"""

from plone import api
from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.schema import SCHEMA_CACHE
from plone.dexterity.utils import resolveDottedName
from zope.interface.interface import InterfaceClass


#: ``portal_type`` of this package's own Profile content type.
PROFILE_PORTAL_TYPE = "UserProfile"

#: ``portal_type`` of this package's own Group content type.
GROUP_PORTAL_TYPE = "UserGroup"

#: Portal type created for a new user. Seeded with ``UserProfile`` at install
#: -- see
#: :func:`~pas.plugins.identity.core.subscribers.principals.seed_type_records`
#: -- and a record rather than a constant so a site may substitute a user type
#: of its own. A type that does not provide
#: :class:`~pas.plugins.identity.core.interfaces.IUserContent` is refused
#: rather than created.
USER_CONTENT_TYPE_RECORD = "pas.plugins.identity.user_content_type"

#: Portal type created for a new group, ``UserGroup`` unless a site says
#: otherwise.
GROUP_CONTENT_TYPE_RECORD = "pas.plugins.identity.group_content_type"


def _configured(record: str, default: str) -> str:
    """Read a type record, falling back to this package's own type.

    :param record: Full dotted record name.
    :param default: The type to answer when the record is empty or missing.
    :returns: A portal type id.
    """
    # A missing record -- a site mid-install, or one this add-on was removed
    # from -- answers the default rather than raising.
    value = api.portal.get_registry_record(record, default="")
    return (value or "").strip() or default


def user_portal_type() -> str:
    """Return the portal type this site keeps its users in.

    :returns: A portal type id; ``UserProfile`` unless the site names another.
    """
    return _configured(USER_CONTENT_TYPE_RECORD, PROFILE_PORTAL_TYPE)


def group_portal_type() -> str:
    """Return the portal type this site keeps its groups in.

    :returns: A portal type id; ``UserGroup`` unless the site names another.
    """
    return _configured(GROUP_CONTENT_TYPE_RECORD, GROUP_PORTAL_TYPE)


def catalogued_types() -> tuple[str, str]:
    """Return every type filed in the identity catalog.

    :returns: The user type and the group type, in that order.
    """
    return (user_portal_type(), group_portal_type())


def type_provides(portal_type: str, marker: InterfaceClass) -> bool:
    """Report whether objects of a portal type will provide a marker.

    Asked of the FTI rather than of an instance, so the answer is known before
    anything is created.

    The marker may arrive by any of the routes Dexterity offers, and a site
    bringing its own type is most likely to use one this package does not:
    the type's own schema, as ``UserProfile`` does; a behavior, as its schema
    or as its marker; or the content class, through ``<class><implements>``.

    :param portal_type: The type to check.
    :param marker: The interface objects of that type must provide.
    :returns: Whether they will. ``False`` for a type that does not exist, is
        not a Dexterity type, or whose schema or class will not load.
    """
    fti = getattr(api.portal.get_tool("portal_types"), portal_type, None)
    if not IDexterityFTI.providedBy(fti):
        return False
    try:
        schema = fti.lookupSchema()
        klass = resolveDottedName(fti.klass)
    except (AttributeError, ImportError, ValueError):
        # A broken FTI must not break adding a user, a group or a login.
        return False
    if schema.isOrExtends(marker) or marker.implementedBy(klass):
        return True
    return any(
        iface.isOrExtends(marker)
        for registration in SCHEMA_CACHE.behavior_registrations(portal_type)
        for iface in (registration.interface, registration.marker)
        if iface is not None
    )


__all__ = [
    "GROUP_CONTENT_TYPE_RECORD",
    "GROUP_PORTAL_TYPE",
    "PROFILE_PORTAL_TYPE",
    "USER_CONTENT_TYPE_RECORD",
    "catalogued_types",
    "group_portal_type",
    "type_provides",
    "user_portal_type",
]

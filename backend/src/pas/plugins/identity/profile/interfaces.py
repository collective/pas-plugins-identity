"""Interfaces for the ``[profile]`` layer.

Kept in one module so the GenericSetup profile, the catalog tool and the
subscribers can all name them without importing each other.
"""

from pas.plugins.identity import _
from zope import schema
from zope.interface import Interface
from zope.publisher.interfaces.browser import IDefaultBrowserLayer


class IIdentityProfileLayer(IDefaultBrowserLayer):
    """Browser layer installed by the ``profile`` GenericSetup profile.

    Registrations that must not exist in a core-only site are bound to this
    layer, which is what keeps the extra genuinely optional at runtime even
    though its ZCML is always loaded.
    """


class IIdentityCatalogued(Interface):
    """Marker for anything filed in the dedicated identity catalog.

    Both content types this layer defines carry it, so the indexing
    subscribers are registered once for the pair rather than twice for each.
    """


class IProfile(IIdentityCatalogued):
    """Marker for the Profile content type.

    Applied through the FTI rather than the class so that the catalog
    subscribers can be registered for the marker and stay indifferent to how
    the object was constructed.
    """


class IIdentityGroup(IIdentityCatalogued):
    """Marker for the Group content type."""


class IIdentityProfileCatalog(Interface):
    """Marker for the dedicated Profile catalog tool.

    The tool is looked up by this interface rather than by id, so a
    deployment may replace it wholesale.
    """


class IProfileSettings(Interface):
    """Settings the ``profile`` GenericSetup profile installs.

    Every record lives under the ``pas.plugins.identity`` prefix, and this is
    the single description of what each one is for; the profile imports the
    schema rather than declaring the fields a second time.
    """

    profile_container_parent = schema.TextLine(
        title=_("Profile container parent"),
        description=_(
            "Path of the folder the profile container lives in, relative to "
            "the site root. Empty means the site root itself."
        ),
        required=False,
        default="",
    )

    profile_container_id = schema.TextLine(
        title=_("Profile container id"),
        description=_("Id of the folder holding user profiles."),
        required=False,
        default="identity-profiles",
    )

    profile_container_title = schema.TextLine(
        title=_("Profile container title"),
        description=_(
            "Title given to the profile container when this add-on creates "
            "it. Changing it later does not rename an existing folder."
        ),
        required=False,
        default="Identity Profiles",
    )

    profile_container_type = schema.TextLine(
        title=_("Profile container type"),
        description=_(
            "Portal type used when this add-on creates the profile container."
        ),
        required=False,
        default="Folder",
    )

    profile_enumeration_states = schema.Tuple(
        title=_("Enumeration-active states"),
        description=_(
            "Profiles in these workflow states are visible to user "
            "enumeration and to the properties plugin."
        ),
        value_type=schema.TextLine(),
        required=False,
        default=("incomplete", "complete"),
    )

    group_enumeration_states = schema.Tuple(
        title=_("Enumeration-active group states"),
        description=_(
            "Groups in these workflow states are visible to group "
            "enumeration and grant membership."
        ),
        value_type=schema.TextLine(),
        required=False,
        default=("active",),
    )

    profile_sync_portraits = schema.Bool(
        title=_("Copy provider avatars into portrait storage"),
        description=_(
            "Off by default. When on, the backend fetches the picture_url "
            "claim over HTTPS and stores it as the user's portrait. The URL "
            "comes from the provider and may be user-supplied; read the "
            "documentation before enabling this on a site with private "
            "network services."
        ),
        required=False,
        default=False,
    )

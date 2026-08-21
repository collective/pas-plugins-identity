"""Interfaces for the ``[profile]`` layer (§4.7).

Kept in one module so the GenericSetup profile, the catalog tool and the
subscribers can all name them without importing each other.
"""

from zope.interface import Interface
from zope.publisher.interfaces.browser import IDefaultBrowserLayer


class IIdentityProfileLayer(IDefaultBrowserLayer):
    """Browser layer installed by the ``profile`` GenericSetup profile.

    Registrations that must not exist in a core-only site are bound to this
    layer, which is what keeps the extra genuinely optional at runtime even
    though its ZCML is always loaded (§4.9).
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
    """Marker for the Group content type (Gate 6d)."""


class IIdentityProfileCatalog(Interface):
    """Marker for the dedicated Profile catalog tool.

    The tool is looked up by this interface rather than by id, so a
    deployment may replace it wholesale.
    """

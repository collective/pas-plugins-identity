"""GenericSetup import and export for the dedicated Profile catalog.

GenericSetup has known how to read a ZCatalog out of XML for twenty years, and
:class:`~Products.GenericSetup.ZCatalog.exportimport.ZCatalogXMLAdapter`
already adapts this one: it is registered for ``IZCatalog``, which every
ZCatalog provides, rather than for a tool interface. What was missing was
never the adapter. It was a *step* pointing at this tool.

``Products.CMFCore.exportimport.catalog.importCatalogTool`` resolves its
target with ``queryUtility(ICatalogTool)``. That answers ``portal_catalog``
and nothing else -- the Profile catalog is looked up by
:class:`~pas.plugins.identity.core.interfaces.IIdentityProfileCatalog` and is
registered as no utility at all -- so the stock ``catalog`` step cannot reach
a second catalog even in principle. Worse, a ``catalog.xml`` shipped in this
package's profile would not be ignored: it would be applied to
``portal_catalog``, silently, adding this package's indexes to the site
catalog. That is the reason for a different filename, not tidiness.

So the two handlers below do what the CMFCore ones do, against the tool this
package owns, and the adapter is subclassed for one line: ``name``, which is
what :func:`~Products.GenericSetup.utils.importObjects` turns into the
filename. The base class says ``catalog``; this says ``identity-catalog``.

The registration is more specific than the base one -- ``IIdentityProfileCatalog``
against ``IZCatalog`` -- so it wins for this tool and changes nothing for any
other catalog in the site.
"""

from pas.plugins.identity.core.catalog import CATALOG_ID
from pas.plugins.identity.core.catalog import IdentityProfileCatalog
from pas.plugins.identity.core.interfaces import IIdentityProfileCatalog
from Products.GenericSetup.interfaces import ISetupEnviron
from Products.GenericSetup.utils import exportObjects
from Products.GenericSetup.utils import importObjects
from Products.GenericSetup.ZCatalog.exportimport import ZCatalogXMLAdapter
from zope.component import adapts


class IdentityCatalogXMLAdapter(ZCatalogXMLAdapter):
    """Read and write the Profile catalog as ``identity-catalog.xml``.

    Everything except the filename is inherited, deliberately: the base class
    already creates indexes and columns only when they are missing, honours
    ``remove="True"`` on either, builds a ZCTextIndex's ``extra`` record from
    its child nodes, and round-trips sub-objects such as the lexicon and its
    pipeline. Reimplementing any of that here would be a second copy to keep
    correct.
    """

    adapts(IIdentityProfileCatalog, ISetupEnviron)

    _LOGGER_ID = "identity-catalog"

    #: The filename, minus the ``.xml`` suffix the base class appends. It is
    #: the whole reason this subclass exists: the inherited value is
    #: ``catalog``, and two catalogs answering to one file would mean the site
    #: catalog and this one overwriting each other's configuration.
    name = "identity-catalog"


def import_identity_catalog(context) -> None:
    """Read ``identity-catalog.xml`` into the Profile catalog.

    Does nothing in a site that has no such catalog, which is every site that
    has not applied this package's profile: the step is registered
    instance-wide and runs during every add-on installation in every site, so
    answering "not here" quietly is the whole of its behaviour there.

    :param context: The setup tool running the import.
    """
    catalog = _catalog(context)
    if catalog is None:
        context.getLogger("identity-catalog").debug("Nothing to import.")
        return
    importObjects(catalog, "", context)


def export_identity_catalog(context) -> None:
    """Write the Profile catalog out as ``identity-catalog.xml``.

    :param context: The setup tool running the export.
    """
    catalog = _catalog(context)
    if catalog is None:
        context.getLogger("identity-catalog").debug("Nothing to export.")
        return
    exportObjects(catalog, "", context)


def _catalog(context) -> IdentityProfileCatalog | None:
    """Return the Profile catalog of the site being set up, or ``None``.

    Acquired from the *context's* site rather than looked up from the current
    one, which is what
    :func:`~pas.plugins.identity.core.catalog.catalog_for` does from an object
    and for the same reason: the thread-local site is a different question
    that merely happens to have the same answer most of the time.

    :param context: The import or export context.
    :returns: The catalog tool, or ``None`` when the site has not got one.
    """
    return getattr(context.getSite(), CATALOG_ID, None)


__all__ = [
    "IdentityCatalogXMLAdapter",
    "export_identity_catalog",
    "import_identity_catalog",
]

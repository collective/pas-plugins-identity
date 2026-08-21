"""Install and uninstall of the ``profile`` GenericSetup profile.

The catalog tool itself is added and removed by ``toolset.xml``; what cannot
be done declaratively is its *contents*. GenericSetup's ``catalog`` import step
is hard-wired to ``portal_catalog`` -- it fetches that tool by name and has no
notion of a second catalog -- so the indexes, the lexicon and the metadata
columns are built here instead, idempotently, from the declarations in
:mod:`pas.plugins.identity.profile.catalog`.

Uninstall removes the catalog and the browser layer. It deliberately leaves
the Profile objects and their container alone: uninstalling an add-on is a
configuration change, not an instruction to delete everyone's account data.
The same reasoning already governs provider deletion in the control panel.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.profile.catalog import CATALOG_ID
from pas.plugins.identity.profile.catalog import INDEXES
from pas.plugins.identity.profile.catalog import METADATA
from pas.plugins.identity.profile.catalog import query_catalog
from pas.plugins.identity.profile.container import get_container
from plone import api
from Products.GenericSetup.tool import SetupTool
from Products.ZCTextIndex.PipelineFactory import element_factory
from Products.ZCTextIndex.ZCTextIndex import PLexicon
from typing import Any


#: Marker file the ``profile`` profile ships, so that import steps declared
#: by this package can tell "our profile is being imported" from "somebody
#: else's is".
MARKER = "pas.plugins.identity-profile.txt"

#: Lexicon used by the ``SearchableText`` index. Named and configured exactly
#: as Plone's own so that the splitting and accent-folding behaviour a site
#: already relies on in search applies to user search too.
LEXICON_ID = "plone_lexicon"

#: Pipeline of the lexicon, as ``(group, name)`` pairs.
LEXICON_PIPELINE = (
    ("Word Splitter", "Unicode Whitespace splitter"),
    ("Case Normalizer", "Unicode Ignoring Accents Case Normalizer"),
)

#: ``extra`` record for the ZCTextIndex, mirroring ``portal_catalog``.
ZCTEXT_EXTRA = {"index_type": "Okapi BM25 Rank", "lexicon_id": LEXICON_ID}


class _Extra:
    """Carrier for ZCTextIndex's ``extra`` argument.

    ``addIndex`` reads attributes off this object rather than keys off a
    mapping, which is why a plain dict will not do.
    """

    def __init__(self, **kwargs: str) -> None:
        """Store the keyword arguments as attributes.

        :param kwargs: Attribute names and values.
        """
        self.__dict__.update(kwargs)


def add_lexicon(catalog: Any) -> None:
    """Create the ZCTextIndex lexicon if it is missing.

    :param catalog: The Profile catalog.
    """
    if LEXICON_ID in catalog.objectIds():
        return
    catalog._setObject(LEXICON_ID, PLexicon(LEXICON_ID, "", *_pipeline_elements()))


def _pipeline_elements() -> tuple[Any, ...]:
    """Build the lexicon pipeline from the registered ZCTextIndex plugins.

    :returns: Instantiated pipeline elements, in order.
    """
    return tuple(
        element_factory.instantiate(group, name) for group, name in LEXICON_PIPELINE
    )


def add_indexes(catalog: Any) -> None:
    """Create the declared indexes if they are missing.

    :param catalog: The Profile catalog.
    """
    existing = set(catalog.indexes())
    for name, meta_type in INDEXES:
        if name in existing:
            continue
        if meta_type == "ZCTextIndex":
            catalog.addIndex(name, meta_type, extra=_Extra(**ZCTEXT_EXTRA))
        else:
            catalog.addIndex(name, meta_type)
        logger.info("Added index %s (%s) to %s", name, meta_type, CATALOG_ID)


def add_metadata(catalog: Any) -> None:
    """Create the declared metadata columns if they are missing.

    :param catalog: The Profile catalog.
    """
    existing = set(catalog.schema())
    for column in METADATA:
        if column not in existing:
            catalog.addColumn(column)
            logger.info("Added metadata %s to %s", column, CATALOG_ID)


def post_install(context: SetupTool) -> None:
    """Build the catalog and the Profile container.

    :param context: The setup tool running the import.
    """
    catalog = api.portal.get_tool(CATALOG_ID)
    add_lexicon(catalog)
    add_indexes(catalog)
    add_metadata(catalog)
    get_container(create=True)


def rebuild_catalog(context: SetupTool) -> None:
    """Clear the Profile catalog and index every Profile again (§4.7).

    Registered as a re-runnable GenericSetup import step rather than as an
    upgrade step: drift is not tied to a version bump, and an operator who has
    just been handed a list of findings by
    :func:`~pas.plugins.identity.profile.doctor.check` needs to be able to run
    this now and again next week.

    Guarded by the marker file so that it runs for this package's ``profile``
    profile and no other. Without the guard GenericSetup would run it during
    *every* add-on installation in the site, each one silently clearing and
    rebuilding a catalog that had nothing wrong with it.

    :param context: The setup tool running the import.
    """
    if context.readDataFile(MARKER) is None:
        return
    catalog = query_catalog()
    if catalog is None:
        return
    catalog.clearFindAndRebuild()


def post_uninstall(context: SetupTool) -> None:
    """Nothing to undo beyond what the uninstall profile declares.

    Present so that the ``uninstall-profile`` profile has the same shape as
    every other profile in this package (I8), and so that the decision *not*
    to delete Profile content has somewhere to be written down rather than
    being inferred from an absence.

    :param context: The setup tool running the import.
    """
    logger.info("Uninstalled the profile layer; Profile content was left in place.")

"""Building the dedicated Profile catalog at install time.

The catalog tool itself is added and removed by ``toolset.xml``; what cannot
be done declaratively is its *contents*. GenericSetup's ``catalog`` import
step is hard-wired to ``portal_catalog`` -- it fetches that tool by name and
has no notion of a second catalog -- so the indexes, the lexicon and the
metadata columns are built here instead, idempotently, from the declarations
in :mod:`pas.plugins.identity.core.catalog`.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.catalog import CATALOG_ID
from pas.plugins.identity.core.catalog import IdentityProfileCatalog
from pas.plugins.identity.core.catalog import INDEXES
from pas.plugins.identity.core.catalog import METADATA
from Products.ZCTextIndex.PipelineFactory import element_factory
from Products.ZCTextIndex.ZCTextIndex import PLexicon


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


def add_lexicon(catalog: IdentityProfileCatalog) -> None:
    """Create the ZCTextIndex lexicon if it is missing.

    :param catalog: The Profile catalog.
    """
    if LEXICON_ID in catalog.objectIds():
        return
    catalog._setObject(LEXICON_ID, PLexicon(LEXICON_ID, "", *_pipeline_elements()))


def _pipeline_elements() -> tuple[object, ...]:
    """Build the lexicon pipeline from the registered ZCTextIndex plugins.

    :returns: Instantiated pipeline elements, in order.
    """
    return tuple(
        element_factory.instantiate(group, name) for group, name in LEXICON_PIPELINE
    )


def add_indexes(catalog: IdentityProfileCatalog) -> None:
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


def add_metadata(catalog: IdentityProfileCatalog) -> None:
    """Create the declared metadata columns if they are missing.

    :param catalog: The Profile catalog.
    """
    existing = set(catalog.schema())
    for column in METADATA:
        if column not in existing:
            catalog.addColumn(column)
            logger.info("Added metadata %s to %s", column, CATALOG_ID)


__all__ = [
    "LEXICON_ID",
    "LEXICON_PIPELINE",
    "ZCTEXT_EXTRA",
    "add_indexes",
    "add_lexicon",
    "add_metadata",
]

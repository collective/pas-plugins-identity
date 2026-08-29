"""The dedicated Profile catalog.

A separate catalog rather than extra indexes on ``portal_catalog``, for three
reasons that all point the same way: PAS enumeration runs on requests where
waking content is unacceptable, the queries are unrelated to site search, and
a rebuild here must not be a site-wide reindex.

It subclasses Plone's own :class:`~Products.CMFPlone.CatalogTool.CatalogTool`
so that the standard indexing machinery -- ``IIndexableObject`` wrappers,
``plone.indexer`` adapters, the workflow-aware ``review_state`` indexer --
applies unchanged. That inheritance brings two behaviours that are wrong here
and are overridden below:

``searchResults``
    filters by ``allowedRolesAndUsers`` and ``effectiveRange``. Enumeration is
    not a content search; it runs for PAS, often as an anonymous or
    low-privilege user, and must return every active Profile. Callers in this
    layer use :meth:`unrestrictedSearchResults`, which CMFCore leaves
    unfiltered. ``searchResults`` is left as inherited: a deployment that
    queries this catalog as content gets content semantics.

``clearFindAndRebuild``
    walks the entire portal with ``ZopeFindAndApply`` and reindexes anything
    with a ``reindexObject``, which for this catalog would mean cataloguing
    every Document in the site. It is replaced with a walk that indexes
    Profiles only.

``indexObject`` / ``reindexObject`` / ``unindexObject``
    hand the object to CMFCore's *global* indexing queue, which on commit
    dispatches to the registered ``IIndexQueueProcessor`` utilities. There is
    exactly one of those and it is ``portal_catalog``, so through the queue an
    object bound for this catalog silently lands in the site catalog instead
    and nothing is raised. They are overridden to call CMFCore's underscore
    variants, which do the work here and now.
"""

from AccessControl.class_init import InitializeClass
from Acquisition import aq_inner
from Acquisition import aq_parent
from pas.plugins.identity import logger
from pas.plugins.identity.core.interfaces import IIdentityProfileCatalog
from plone import api
from Products.CMFCore.CMFCatalogAware import CMFCatalogAware
from Products.CMFPlone.CatalogTool import CatalogTool
from Products.ZCatalog.CatalogBrains import AbstractCatalogBrain
from zope.interface import implementer


#: Id of the catalog tool in the portal. Looked up by interface everywhere in
#: this package; the id exists because GenericSetup's ``toolset.xml`` needs
#: one and because the ZMI has to call it something.
CATALOG_ID = "portal_identity_catalog"

#: ``portal_type`` of the Profile content type. Lives here rather than in
#: ``core.contents.profile`` because the catalog and the subscribers both need
#: it and neither should have to import the class to get it.
PROFILE_PORTAL_TYPE = "UserProfile"

#: ``portal_type`` of the Group content type.
GROUP_PORTAL_TYPE = "UserGroup"

#: Every type filed in this catalog. Used by the rebuild, which must find
#: them all, and nowhere else -- see :func:`brains_of_type`.
CATALOGUED_TYPES = (PROFILE_PORTAL_TYPE, GROUP_PORTAL_TYPE)

#: Indexes the catalog is created with. ``login`` is lowercased at index time
#: by the indexer in :mod:`pas.plugins.identity.core.indexers` and must be
#: lowercased at query time by every caller -- login names are
#: case-insensitive in Plone, FieldIndex is not.
INDEXES = (
    ("portal_type", "FieldIndex"),
    ("userid", "FieldIndex"),
    ("login", "FieldIndex"),
    ("group_id", "FieldIndex"),
    ("group_ids", "KeywordIndex"),
    # Every address a person has, not only the one ``email`` resolves to. A
    # Keyword index because the field is a list and because the question
    # asked of it -- "whose profile carries this address" -- is an exact
    # match on one entry.
    ("emails", "KeywordIndex"),
    ("review_state", "FieldIndex"),
    ("path", "ExtendedPathIndex"),
    ("SearchableText", "ZCTextIndex"),
)

#: Metadata columns. These are the whole point of the catalog: the PAS
#: property sheet and the enumeration results are served from brains alone,
#: so every field a property sheet exposes has to be here.
METADATA = (
    "portal_type",
    "Title",
    "review_state",
    "userid",
    "login",
    "fullname",
    "email",
    "emails",
    "verified_emails",
    "home_page",
    "description",
    "location",
    "group_id",
    "group_ids",
)

#: Columns that mean something on a Profile. The catalog holds one schema for
#: both types, so a Profile's ``group_id`` is empty and a Group's ``login`` is
#: -- which matters only to the consistency check, which would otherwise
#: report every one of them as drift.
PROFILE_METADATA = (
    "portal_type",
    "Title",
    "review_state",
    "userid",
    "login",
    "fullname",
    "email",
    "emails",
    "verified_emails",
    "home_page",
    "description",
    "location",
    "group_ids",
)

#: Columns that mean something on a Group.
GROUP_METADATA = (
    "portal_type",
    "Title",
    "review_state",
    "group_id",
    "description",
)


@implementer(IIdentityProfileCatalog)
class IdentityProfileCatalog(CatalogTool):
    """Catalog of Profile objects only."""

    id = CATALOG_ID
    meta_type = "Identity Profile Catalog"
    title = "Identity Profile Catalog"

    def indexObject(self, object: CMFCatalogAware) -> None:
        """Index an object in this catalog, immediately.

        :param object: The object to index.
        """
        self._indexObject(object)

    def reindexObject(
        self,
        object: CMFCatalogAware,
        idxs: list[str] | None = None,
        update_metadata: int = 1,
        uid: str | None = None,
    ) -> None:
        """Reindex an object in this catalog, immediately.

        :param object: The object to reindex.
        :param idxs: Indexes to update; all of them when empty.
        :param update_metadata: Whether to refresh the metadata record.
        :param uid: Catalog uid, defaulting to the object's physical path.
        """
        self._reindexObject(
            object,
            idxs=idxs if idxs is not None else [],
            update_metadata=update_metadata,
            uid=uid,
        )

    def unindexObject(self, object: CMFCatalogAware) -> None:
        """Remove an object from this catalog, immediately.

        :param object: The object to unindex.
        """
        self._unindexObject(object)

    def clearFindAndRebuild(self) -> None:
        """Empty the catalog and reindex every Profile in the site.

        Deliberately narrower than the inherited implementation, which would
        catalogue the whole portal. Walks ``portal_catalog`` for Profiles
        rather than the object tree: the site catalog already knows where they
        are, and a Profile that is missing from *both* catalogs is a
        :mod:`~pas.plugins.identity.core.doctor` finding, not something a
        rebuild should paper over.
        """
        self.manage_catalogClear()
        portal = aq_parent(aq_inner(self))
        count = 0
        for brain in portal.portal_catalog.unrestrictedSearchResults(
            portal_type=CATALOGUED_TYPES
        ):
            obj = brain._unrestrictedGetObject()
            self.catalog_object(obj, "/".join(obj.getPhysicalPath()))
            count += 1
        logger.info("Rebuilt %s with %d objects", CATALOG_ID, count)


InitializeClass(IdentityProfileCatalog)


def get_catalog() -> IdentityProfileCatalog:
    """Return the Profile catalog of the current site.

    :returns: The catalog tool.
    :raises api.exc.InvalidParameterError: If the ``profile`` GenericSetup
        profile has not been applied to this site.
    """
    return api.portal.get_tool(CATALOG_ID)


def query_catalog() -> IdentityProfileCatalog | None:
    """Return the Profile catalog, or ``None`` when the layer is not installed.

    This layer's PAS plugins run in every site of the Zope instance,
    including sites that never applied the ``profile`` profile. They ask this
    rather than :func:`get_catalog` so that "not installed here" is an ordinary
    answer instead of an exception.

    :returns: The catalog tool, or ``None``.
    """
    try:
        return get_catalog()
    except api.exc.InvalidParameterError:
        return None


def brains_of_type(
    catalog: IdentityProfileCatalog, portal_type: str
) -> list[AbstractCatalogBrain]:
    """Return every brain of one content type.

    Profiles and Groups share this catalog, which is why almost nothing wants
    :func:`all_brains`: a caller that forgets to narrow gets the other type's
    records back and, in a consistency check, reports every one of them as an
    orphan.

    :param catalog: The Profile catalog.
    :param portal_type: The type to return.
    :returns: Matching brains.
    """
    return list(catalog.unrestrictedSearchResults(portal_type=portal_type))


def profile_brains(catalog: IdentityProfileCatalog) -> list[AbstractCatalogBrain]:
    """Return every Profile brain.

    :param catalog: The Profile catalog.
    :returns: Profile brains.
    """
    return brains_of_type(catalog, PROFILE_PORTAL_TYPE)


def group_brains(catalog: IdentityProfileCatalog) -> list[AbstractCatalogBrain]:
    """Return every Group brain.

    :param catalog: The Profile catalog.
    :returns: Group brains.
    """
    return brains_of_type(catalog, GROUP_PORTAL_TYPE)


def all_brains(catalog: IdentityProfileCatalog) -> list[AbstractCatalogBrain]:
    """Return every brain in the Profile catalog.

    A ZCatalog query with no criteria returns *nothing*, not everything, and
    does so without complaining -- which reads as "the catalog is empty" and is
    how a consistency check can be written that passes because it looked at
    zero records. Rooting the query at the portal path is the cheapest query
    that genuinely means "all of them".

    :param catalog: The Profile catalog.
    :returns: All brains.
    """
    portal_path = "/".join(api.portal.get().getPhysicalPath())
    return list(catalog.unrestrictedSearchResults(path=portal_path))

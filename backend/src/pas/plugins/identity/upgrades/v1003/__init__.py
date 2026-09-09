"""Take a site to profile version 1003.

Two index changes, and neither is carried by re-importing anything.

``identity-catalog.xml`` gained a ``sortable_title`` index. Re-importing the
``identity-catalog`` step creates it, empty. An index added to a catalog holds
nothing until something reindexes the objects that belong in it, exactly as one
added in Python would, so a site that upgraded and stopped there would have the
index, no error, and a group membership listing ordered by whatever the catalog
happened to return.

``SearchableText`` **in the site catalog** now says something different about a
Profile. Both indexers used to be registered for the object alone, which
registers them against every catalog, so ``portal_catalog`` held a Profile's
full name, login and email and never its biography. It now holds the title, the
userid and the biography. That is a change to what an existing entry should
say, and nothing recomputes an index because the code behind it changed -- so
every Profile already in the site catalog keeps the old words until this step
reindexes them.

Both halves are the same shape of problem, which is why they are one step: an
import that is necessary and is not sufficient.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.catalog import query_catalog
from Products.GenericSetup.tool import SetupTool


#: The profile this step re-imports from.
PROFILE = "profile-pas.plugins.identity:default"

#: The index this upgrade exists to create and fill.
INDEX = "sortable_title"


def add_sortable_title(context: SetupTool) -> None:
    """Create the ``sortable_title`` index and fill it.

    Reindexes that one index rather than rebuilding the catalog. The rest of
    the catalog is already correct and a full rebuild walks the site; naming
    the index is what keeps this proportional to the change.

    :param context: The setup tool running the upgrade.
    """
    from plone import api

    setup = api.portal.get_tool("portal_setup")
    setup.runImportStepFromProfile(PROFILE, "identity-catalog")

    catalog = query_catalog()
    if catalog is None:
        # The layer is not installed in this site. Nothing to fill, and
        # saying so beats raising out of an upgrade step.
        logger.info("No identity catalog in this site; nothing to reindex.")
        return

    if INDEX not in catalog.indexes():
        # The import above should have created it. If it did not, reindexing
        # would silently do nothing, so this is worth being loud about.
        raise ValueError(
            f"The {INDEX!r} index is still missing after re-importing the "
            f"identity-catalog step. The upgrade would have reported success "
            f"and changed nothing."
        )

    catalog.reindexIndex(INDEX, None)
    logger.info("Reindexed %r for %s objects.", INDEX, len(catalog))

    _refresh_site_searchable_text()


def _refresh_site_searchable_text() -> None:
    """Reindex ``SearchableText`` for the Profiles in the site catalog.

    The words changed, not the index. A Profile already catalogued in
    ``portal_catalog`` keeps whatever the previous indexer wrote until
    something asks for it again, and nothing does that on its own because the
    objects have not been touched.

    Only Profiles, and only that one index: the site catalog belongs to the
    whole site, and an upgrade to this package has no business rebuilding it.
    """
    from plone import api

    site = api.portal.get_tool("portal_catalog")
    brains = site.unrestrictedSearchResults(portal_type=PROFILE_PORTAL_TYPE)
    for brain in brains:
        obj = brain.getObject()
        site.reindexObject(obj, idxs=["SearchableText"], update_metadata=0)
    logger.info(
        "Refreshed SearchableText for %s Profiles in the site catalog.", len(brains)
    )

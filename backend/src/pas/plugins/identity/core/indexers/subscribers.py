"""Filing a Profile in the identity catalog as it moves and changes.

The subscribers follow CMFCore's own pattern rather than inventing one:
unindex on ``IObjectWillBeMovedEvent`` while the object is still at its old
path, index on ``IObjectMovedEvent`` once it is at the new one. That is what
makes rename and move correct without either handler having to reconstruct a
path from the event -- and because both events are dispatched to sublocations,
it also covers a Profile carried along inside a folder somebody moved.
"""

from OFS.interfaces import IObjectWillBeMovedEvent
from pas.plugins.identity.core.catalog import catalog_for
from pas.plugins.identity.core.catalog import IdentityProfileCatalog
from pas.plugins.identity.core.catalog import query_catalog
from pas.plugins.identity.core.contents.profile import UserProfile
from zope.lifecycleevent.interfaces import IObjectModifiedEvent
from zope.lifecycleevent.interfaces import IObjectMovedEvent


def _catalog_for(obj: UserProfile) -> IdentityProfileCatalog | None:
    """Return the Profile catalog this object should be filed in.

    Acquired from the object, which is the only thing here that knows which
    site the object is in. Asking the *current* site instead gave the same
    answer on every request and a wrong one everywhere else: a ``zconsole``
    script that never called ``setSite``, and the deletion of a site from the
    Zope root, where there is no current site and the lookup raised out of the
    handler rather than answering.

    :param obj: A Profile.
    :returns: The catalog tool, or ``None`` when the layer is not installed in
        the site the object belongs to.
    """
    return catalog_for(obj) or query_catalog()


def profile_moved(obj: UserProfile, event: IObjectMovedEvent) -> None:
    """Index a Profile that has arrived at a path.

    Covers creation, move and rename alike. ``newParent`` is ``None`` when the
    object is on its way out of the site, which is the removal case and is
    already handled by :func:`profile_will_be_moved`.

    :param obj: The Profile.
    :param event: The move event.
    """
    if event.newParent is None:
        return
    catalog = _catalog_for(obj)
    if catalog is not None:
        catalog.indexObject(obj)


def profile_will_be_moved(obj: UserProfile, event: IObjectWillBeMovedEvent) -> None:
    """Unindex a Profile that is about to leave its path.

    Runs before the move so that ``getPhysicalPath`` still yields the entry
    actually present in the catalog. ``oldParent`` is ``None`` when the object
    is being added, which has nothing to unindex.

    :param obj: The Profile.
    :param event: The pending-move event.
    """
    if event.oldParent is None:
        return
    catalog = _catalog_for(obj)
    if catalog is not None:
        catalog.unindexObject(obj)


#: Attributes indexed under their own name and feeding no other index. An event
#: that names only these reindexes only them. Anything else reindexes every
#: index, because a field's name need not be an index's: ``fullname`` feeds
#: ``sortable_title`` and ``SearchableText`` as well.
SELF_INDEXED = frozenset({"group_ids"})


def _indexes_for(event: IObjectModifiedEvent) -> list[str] | None:
    """Return the indexes an event's descriptions confine a reindex to.

    :param event: The modification or transition event.
    :returns: Index names, or ``None`` for all of them.
    """
    names = {
        name
        for description in getattr(event, "descriptions", ())
        for name in getattr(description, "attributes", ())
    }
    if names and names <= SELF_INDEXED:
        return sorted(names)
    return None


def profile_modified(obj: UserProfile, event: IObjectModifiedEvent) -> None:
    """Reindex a Profile whose fields or workflow state changed.

    Registered for both ``IObjectModifiedEvent`` and CMFCore's
    ``IAfterTransitionEvent``: a transition changes ``review_state``, which is
    both an index and a metadata column, and nothing else notices.

    A membership change names ``group_ids`` and reindexes that index alone,
    with the metadata record. The other indexes would be rewritten with the
    values they already hold.

    :param obj: The Profile.
    :param event: The modification or transition event.
    """
    catalog = _catalog_for(obj)
    if catalog is not None:
        catalog.reindexObject(obj, idxs=_indexes_for(event))

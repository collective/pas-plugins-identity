"""Keeping the Profile catalog honest.

Two subscribers and two indexers, and between them they are the whole reason
the churn test can assert ``catalog count == Profile count`` after any
sequence of operations.

The subscribers follow CMFCore's own pattern rather than inventing one:
unindex on ``IObjectWillBeMovedEvent`` while the object is still at its old
path, index on ``IObjectMovedEvent`` once it is at the new one. That is what
makes rename and move correct without either handler having to reconstruct a
path from the event -- and because both events are dispatched to sublocations,
it also covers a Profile carried along inside a folder somebody moved.
"""

from OFS.interfaces import IObjectWillBeMovedEvent
from pas.plugins.identity.content.catalog import IdentityProfileCatalog
from pas.plugins.identity.content.catalog import query_catalog
from pas.plugins.identity.content.interfaces import IUserProfile
from pas.plugins.identity.content.profile import UserProfile
from plone.indexer.decorator import indexer
from zope.lifecycleevent.interfaces import IObjectModifiedEvent
from zope.lifecycleevent.interfaces import IObjectMovedEvent


def _catalog_for(obj: UserProfile) -> IdentityProfileCatalog | None:
    """Return the Profile catalog this object should be filed in.

    :param obj: A Profile.
    :returns: The catalog tool, or ``None`` when the layer is not installed in
        the site the object belongs to.
    """
    return query_catalog()


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


def profile_modified(obj: UserProfile, event: IObjectModifiedEvent) -> None:
    """Reindex a Profile whose fields or workflow state changed.

    Registered for both ``IObjectModifiedEvent`` and CMFCore's
    ``IAfterTransitionEvent``: a transition changes ``review_state``, which is
    both an index and a metadata column, and nothing else notices.

    :param obj: The Profile.
    :param event: The modification or transition event.
    """
    catalog = _catalog_for(obj)
    if catalog is not None:
        catalog.reindexObject(obj)


@indexer(IUserProfile)
def login_index(obj: UserProfile) -> str:
    """Index the login name in lower case.

    Login names are case-insensitive in Plone; ``FieldIndex`` is not. Folding
    here means every query has to fold too, which is why the PAS plugin goes
    through a single helper rather than querying the index directly.

    :param obj: The Profile.
    :returns: The lowercased login, or an empty string.
    """
    return (obj.login or "").lower()


@indexer(IUserProfile)
def searchable_text_index(obj: UserProfile) -> str:
    """Index full name, login and email as one text blob.

    Deliberately not the biography: a Sharing-tab search for a user should not
    match somebody who happens to mention them in their own bio.

    :param obj: The Profile.
    :returns: Space-joined searchable text.
    """
    return " ".join(value for value in (obj.fullname, obj.login, obj.email) if value)

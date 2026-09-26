"""Indexers that fold or compute what a Profile field holds.

Each names this package's catalog as well as the object, so it applies where
enumeration reads and nowhere else: a Profile is ordinary content and is
catalogued in ``portal_catalog`` too.
"""

from pas.plugins.identity.core.completeness import missing_fields
from pas.plugins.identity.core.contents.profile import UserProfile
from pas.plugins.identity.core.interfaces import IIdentityProfileCatalog
from pas.plugins.identity.core.interfaces import IUserProfile
from plone.indexer.decorator import indexer


@indexer(IUserProfile, IIdentityProfileCatalog)
def missing_fields_index(obj: UserProfile) -> tuple[str, ...]:
    """Store what this Profile is still waiting for, as the object sees it.

    A metadata column rather than an index: nothing queries on it, and the
    point of it is to be *read back* without waking the object.

    The catalog is the only place the two answers can be made to agree.
    :func:`~pas.plugins.identity.core.completeness.missing_fields` can ask
    whether a field's owner may write it, because it has the object and the
    permission is granted per profile;
    :func:`~pas.plugins.identity.core.completeness.missing_from_brain` cannot,
    and used to answer by scanning columns for emptiness -- so it named fields
    the object had already stopped counting, and named any required field that
    is not a column at all. The gate's message is built from that answer, which
    made it ask people for things their form does not show them.

    Recomputed on every reindex, which is every write and every transition --
    the same moments
    :func:`~pas.plugins.identity.core.completeness.reconcile` runs at. So the
    column and ``review_state`` are always written together, and a brain can no
    longer report a state and a reason that disagree.

    **It can go stale, and only two things do that.** Granting or revoking a
    field's write permission on one profile, and editing
    ``required_profile_fields`` in the registry. Neither fires an event on the
    profiles it changes the answer for, and neither did before: ``review_state``
    was already left over from the last write. The remedy is the same for both
    and already exists -- apply the ``rebuild-catalog`` profile.

    :param obj: The Profile.
    :returns: Field names, in schema order.
    """
    return missing_fields(obj)


@indexer(IUserProfile, IIdentityProfileCatalog)
def login_index(obj: UserProfile) -> str:
    """Index the login name in lower case.

    Login names are case-insensitive in Plone; ``FieldIndex`` is not. Folding
    here means every query has to fold too, which is why the PAS plugin goes
    through a single helper rather than querying the index directly.

    :param obj: The Profile.
    :returns: The lowercased login, or an empty string.
    """
    return (obj.login or "").lower()

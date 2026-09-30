"""``@group-members`` -- who is in a group, including through a nesting.

plone.restapi already answers part of this. ``GET @groups/<id>`` carries a
batched ``members`` list, and because it goes through PlonePAS's
``getGroupMemberIds`` it picks up this package's nesting for free -- a member
of an inner group is in that list without anything here being asked.

What it does not do is what a group *page* needs:

* the members are bare userids, so rendering a list of people costs one
  ``@users/<id>`` request each;
* there is no way to search *within* a group, only to search for groups;
* nothing says which group somebody arrived through, so a page cannot explain
  why a person is on it.

So this is the contextual version rather than a replacement: the same
membership, answered from the Profile catalog in one query, with enough per
person to draw a row and with the nesting made visible.

Every read is from catalog metadata. That is not an optimisation here so much
as the reason the endpoint can exist at all: a group with a thousand members
would otherwise be a thousand object loads on a page view.

That was not true until recently, and the way it was untrue is worth keeping in
mind: the row called a userid-keyed URL helper -- since removed -- to fill one
key, which searched the catalog again and then woke the object to ask its URL.
A brain already knows its own URL. The row is now
:class:`~pas.plugins.identity.core.serializers.groupmember.GroupMemberSerializer`,
which is also where a deployment adds a field to it.
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.catalog import query_catalog
from pas.plugins.identity.core.pas.profile import PLUGIN_ID as PROFILE_PLUGIN_ID
from pas.plugins.identity.core.principal_types import user_portal_type
from pas.plugins.identity.core.utils.nesting import members_of
from pas.plugins.identity.core.utils.plugins import get as get_plugin
from Products.CMFCore.permissions import ManageUsers
from Products.ZCatalog.CatalogBrains import AbstractCatalogBrain


#: What a caller needs to read a group's membership without being in it.
MANAGE_PERMISSION = ManageUsers


def get_profile_plugin():
    """Return the profile PAS plugin, or ``None``.

    :returns: The plugin, or ``None`` when this package's profile has not been
        applied to the site -- in which case there are no content-backed
        groups to answer about.
    """
    plugin = get_plugin(PROFILE_PLUGIN_ID)
    if plugin is None:
        logger.debug("No %s plugin in this site", PROFILE_PLUGIN_ID)
    return plugin


def member_brains(group_id: str, plugin) -> list[AbstractCatalogBrain]:
    """Return the Profile brains of everybody in a group.

    The nesting is resolved into a list of group ids first and the catalog is
    asked for all of them at once: ``group_ids`` is a KeywordIndex, so one
    query covers every level.

    :param group_id: The group asked about.
    :param plugin: The profile PAS plugin.
    :returns: Profile brains, ordered by ``sortable_title`` -- the name each
        person is shown under, decided by the catalog rather than here.
    """
    catalog = query_catalog()
    if catalog is None:
        return []
    feeding = members_of(group_id, plugin.group_edges())
    if not feeding:
        return []
    states = plugin.enumeration_states()
    return [
        brain
        for brain in catalog.unrestrictedSearchResults(
            portal_type=user_portal_type(),
            group_ids=list(feeding),
            # Ordered by the catalog rather than in Python. The previous
            # version read every member of the group and sorted the whole list
            # to render a page of it, which is the sort of thing that is
            # invisible on a group of twelve.
            sort_on="sortable_title",
        )
        if brain.review_state in states
    ]


def search_members(
    brains: list[AbstractCatalogBrain], search: str
) -> list[AbstractCatalogBrain]:
    """Narrow a group's members to the ones a search matches.

    Filtered here rather than in the query: the fields a person is recognised
    by are metadata, not indexes, and adding indexes for a substring search
    over a group's own membership would be indexing the whole site to narrow a
    list somebody is already looking at. It also leaves the whole membership
    in hand, which is what the group's totals are counted from.

    :param brains: The members, as :func:`member_brains` returns them.
    :param search: Case-insensitive substring matched against full name and
        login. Empty matches everybody.
    :returns: The matching brains, in the order given -- so still sorted.
    """
    term = search.strip().lower()
    if not term:
        return brains
    return [
        brain
        for brain in brains
        if term in (brain.fullname or "").lower() or term in (brain.login or "").lower()
    ]


def direct_members(
    group_id: str, brains: list[AbstractCatalogBrain]
) -> list[AbstractCatalogBrain]:
    """Keep the members who are in a group itself rather than through another.

    :param group_id: The group asked about.
    :param brains: Its members, nested memberships included.
    :returns: The brains whose own ``group_ids`` name the group.
    """
    return [
        brain
        for brain in brains
        if group_id in (getattr(brain, "group_ids", None) or ())
    ]


__all__ = [
    "MANAGE_PERMISSION",
    "direct_members",
    "get_profile_plugin",
    "member_brains",
    "search_members",
]

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
"""

from pas.plugins.identity import logger
from pas.plugins.identity.core.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.core.catalog import query_catalog
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.pas.profile import PLUGIN_ID as PROFILE_PLUGIN_ID
from pas.plugins.identity.core.subscribers import profile_url
from pas.plugins.identity.core.utils.nesting import members_of
from plone import api
from Products.CMFCore.permissions import ManageUsers
from Products.ZCatalog.CatalogBrains import AbstractCatalogBrain


#: What a caller needs to read a group's membership without being in it.
MANAGE_PERMISSION = ManageUsers


def member_row(brain: AbstractCatalogBrain, base: str) -> JSONDict:
    """Render one member from a Profile brain.

    :param brain: The Profile brain.
    :param base: URL of the listing this row belongs to.
    :returns: JSON-ready mapping. Enough to draw a row and to follow through
        to the person; no address, because a membership listing is not a
        directory of contact details.
    """
    return {
        "@id": f"{base}/{brain.userid}",
        "id": brain.userid,
        "fullname": brain.fullname or brain.login or brain.userid,
        "login": brain.login,
        "profile_url": profile_url(brain.userid),
        # Which groups this person is actually in. A page listing an outer
        # group's people can then say where each of them came from, rather
        # than presenting one flat list nobody can account for.
        "through": sorted(getattr(brain, "group_ids", None) or ()),
    }


def get_profile_plugin():
    """Return the profile PAS plugin, or ``None``.

    :returns: The plugin, or ``None`` when this package's profile has not been
        applied to the site -- in which case there are no content-backed
        groups to answer about.
    """
    acl = api.portal.get_tool("acl_users")
    plugin = getattr(acl, PROFILE_PLUGIN_ID, None)
    if plugin is None:
        logger.debug("No %s plugin in this site", PROFILE_PLUGIN_ID)
    return plugin


def member_brains(
    group_id: str, plugin, search: str = ""
) -> list[AbstractCatalogBrain]:
    """Return the Profile brains of everybody in a group.

    The nesting is resolved into a list of group ids first and the catalog is
    asked for all of them at once: ``group_ids`` is a KeywordIndex, so one
    query covers every level.

    :param group_id: The group asked about.
    :param plugin: The profile PAS plugin.
    :param search: Case-insensitive substring matched against full name and
        login. Empty returns everybody.
    :returns: Profile brains, sorted by the name they are shown under.
    """
    catalog = query_catalog()
    if catalog is None:
        return []
    feeding = members_of(group_id, plugin.group_edges())
    if not feeding:
        return []
    states = plugin.enumeration_states()
    brains = [
        brain
        for brain in catalog.unrestrictedSearchResults(
            portal_type=PROFILE_PORTAL_TYPE, group_ids=list(feeding)
        )
        if brain.review_state in states
    ]
    term = search.strip().lower()
    if term:
        # Filtered here rather than in the query: the fields a person is
        # recognised by are metadata, not indexes, and adding indexes for a
        # substring search over a group's own membership would be indexing the
        # whole site to narrow a list somebody is already looking at.
        brains = [
            brain
            for brain in brains
            if term in (brain.fullname or "").lower()
            or term in (brain.login or "").lower()
        ]
    return sorted(brains, key=lambda b: (b.fullname or b.login or "").lower())


__all__ = [
    "MANAGE_PERMISSION",
    "get_profile_plugin",
    "member_brains",
    "member_row",
]

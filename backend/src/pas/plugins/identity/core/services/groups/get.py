"""``GET @group-members/<id>`` -- the people in one group."""

from pas.plugins.identity.core.interfaces import IGroupMemberSerializer
from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.services.base import IdentityService
from pas.plugins.identity.core.services.groups import CHANGE_MEMBERS_PERMISSION
from pas.plugins.identity.core.services.groups import direct_member_groups
from pas.plugins.identity.core.services.groups import direct_members
from pas.plugins.identity.core.services.groups import get_profile_plugin
from pas.plugins.identity.core.services.groups import MANAGE_PERMISSION
from pas.plugins.identity.core.services.groups import member_brains
from pas.plugins.identity.core.services.groups import search_members
from plone import api
from plone.restapi.batching import HypermediaBatch
from Products.CMFCore.permissions import ManagePortal
from Products.CMFPlone.Portal import PloneSite
from zope.component import getMultiAdapter
from zope.interface import implementer
from zope.publisher.interfaces import IPublishTraverse
from ZPublisher.HTTPRequest import HTTPRequest


@implementer(IPublishTraverse)
class GroupMembersGet(IdentityService):
    """List the members of a group, nested memberships included."""

    def __init__(self, context: PloneSite, request: HTTPRequest) -> None:
        """Bind the service and prepare to consume a path segment.

        :param context: The context the service was traversed on.
        :param request: The current request.
        """
        super().__init__(context, request)
        self.segments: list[str] = []

    def publishTraverse(self, request: HTTPRequest, name: str) -> "GroupMembersGet":
        """Collect ``<group id>`` from the URL.

        :param request: The current request.
        :param name: The next path segment.
        :returns: This service.
        """
        self.segments.append(name)
        return self

    def reply(self) -> JSONDict:
        """List a group's members.

        Who may read it: a manager, somebody who may change the group's
        members, or somebody who is in the group. A membership list is
        personal data about other people, and the callers that legitimately
        want it are an administrator and a member looking at their own team.

        ``direct=1`` lists what a change of members acts on instead: the
        groups nested here through their own field, then the people in this
        group itself. ``b_size`` and ``b_start`` page either listing, as
        plone.restapi pages everything else.

        :returns: The listing, or an error body.
        """
        if api.user.is_anonymous():
            return self._error(401, "Not authenticated", "Log in first.")
        if len(self.segments) != 1:
            return self._error(400, "Bad request", "Expected @group-members/<group id>")
        group_id = self.segments[0]

        plugin = get_profile_plugin()
        if plugin is None or group_id not in plugin.getGroupIds():
            # One answer for "no such group" and "not a content group": which
            # groups a site has is not worth probing for.
            return self._error(404, "Unknown group", repr(group_id))

        refusal = self._refuse_unless_allowed(group_id)
        if refusal is not None:
            return refusal

        everybody = member_brains(group_id, plugin)
        query = self.request.form.get("query", "") or ""
        # Once, not once per row: the adapter is stateless and the lookup is
        # the only part of rendering a row that is not a dictionary literal.
        serialize = getMultiAdapter(
            (self.context, self.request), IGroupMemberSerializer
        )
        if self._direct():
            # The members somebody can remove: the groups nested here through
            # their own field, then the people in this group itself. Groups
            # first, because there are few of them and each stands for many.
            groups = direct_member_groups(group_id, plugin, query)
            people = search_members(direct_members(group_id, everybody), query)
            rows = [(self._render_group_row, b) for b in groups] + [
                (serialize, b) for b in people
            ]
        else:
            rows = [(serialize, b) for b in search_members(everybody, query)]
        batch = HypermediaBatch(self.request, rows)
        result = {
            "@id": batch.canonical_url,
            "group": group_id,
            "items_total": batch.items_total,
            "items": [render(brain) for render, brain in batch],
            # The size of the group whatever was searched for, so a page can
            # say how many people are in it without listing them. Counted from
            # the membership the search narrowed, so it costs no second query.
            "members_total": len(everybody),
            "direct_members_total": len(direct_members(group_id, everybody)),
            # The nesting, so a group page can say what feeds into it without
            # a second request per level.
            "nested_groups": self._render_groups(
                plugin.getNestedGroupIds(group_id), plugin
            ),
            "parent_groups": self._render_groups(
                plugin.getGroupParentIds(group_id), plugin
            ),
            # Whether plone.restapi's ``PATCH @groups/<id>`` would accept a
            # change of members from this caller, so a page knows whether to
            # offer one without trying it.
            "can_manage": self._can_manage(group_id),
        }
        if batch.links:
            result["batching"] = batch.links
        return result

    def _direct(self) -> bool:
        """Say whether the caller asked for direct members only.

        :returns: ``True`` for ``direct=1`` (or ``true``), ``False`` otherwise.
        """
        value = str(self.request.form.get("direct", "") or "").strip().lower()
        return value in ("1", "true", "yes", "on")

    def _can_manage(self, group_id: str) -> bool:
        """Say whether the caller may change this group's members.

        The same two questions plone.restapi's ``PATCH @groups/<id>`` asks:
        the site-wide permission, and -- for somebody who does not manage the
        portal -- that the group does not hold the ``Manager`` role, because
        adding a person to it would be granting that role.

        :param group_id: The group being read.
        :returns: Whether a change of members would be accepted.
        """
        if not api.user.has_permission(CHANGE_MEMBERS_PERMISSION):
            return False
        if api.user.has_permission(ManagePortal):
            return True
        group = api.group.get(groupname=group_id)
        return group is None or "Manager" not in group.getRoles()

    def _render_group_row(self, brain) -> JSONDict:
        """Render a directly nested group as a row of a direct listing.

        The keys a person's row has, so a list of members can draw both
        without asking which is which until it has to.

        :param brain: A Group brain.
        :returns: JSON-ready mapping.
        """
        url = brain.getURL()
        return {
            "@id": url,
            "id": brain.group_id,
            "fullname": brain.Title or brain.group_id,
            "login": None,
            "profile_url": url,
            "through": sorted(getattr(brain, "group_ids", None) or ()),
            "type": "group",
        }

    def _refuse_unless_allowed(self, group_id: str) -> JSONDict | None:
        """Return an error body unless the caller may read this membership.

        :param group_id: The group being read.
        :returns: The error body, or ``None`` when the caller is allowed.
        """
        if api.user.has_permission(MANAGE_PERMISSION):
            return None
        # Somebody who may change the members may see them. A Site
        # Administrator holds this and not ``Manage users``, and could
        # otherwise edit a membership through ``@groups`` they cannot read.
        if api.user.has_permission(CHANGE_MEMBERS_PERMISSION):
            return None
        caller = api.user.get_current().getId()
        # The closed answer, so somebody in an inner group may read the outer
        # group they are thereby a member of.
        if group_id in {g.getId() for g in api.group.get_groups(username=caller)}:
            return None
        return self._error(
            403,
            "Not allowed",
            "Reading a group's members needs the "
            f"{MANAGE_PERMISSION!r} or {CHANGE_MEMBERS_PERMISSION!r} "
            "permission, or membership of it.",
        )

    def _render_groups(self, group_ids: tuple[str, ...], plugin) -> list[JSONDict]:
        """Render a list of group ids with their titles and pages.

        The page comes from the brain, as a member row's ``profile_url`` does:
        a brain already knows its own URL, so naming a group costs no object
        load.

        :param group_ids: The groups to render.
        :param plugin: The profile PAS plugin.
        :returns: One entry per group, in the order given. ``group_url`` is
            ``None`` for a group the catalog holds no active entry for, which
            is also the group whose title falls back to its id.
        """
        base = f"{self.context.absolute_url()}/@group-members"
        brains = {brain.group_id: brain for brain in plugin.active_group_brains()}
        entries = []
        for group_id in group_ids:
            brain = brains.get(group_id)
            entries.append({
                "@id": f"{base}/{group_id}",
                "id": group_id,
                "title": brain.Title if brain is not None else group_id,
                # The group's own page, for a reader to follow. ``@id`` is this
                # listing for that group: an API resource, not a page.
                "group_url": brain.getURL() if brain is not None else None,
            })
        return entries

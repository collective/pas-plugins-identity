"""``GET @group-members/<id>`` -- the people in one group."""

from pas.plugins.identity.core.interfaces import JSONDict
from pas.plugins.identity.core.services.base import IdentityService
from pas.plugins.identity.core.services.groups import get_profile_plugin
from pas.plugins.identity.core.services.groups import MANAGE_PERMISSION
from pas.plugins.identity.core.services.groups import member_brains
from pas.plugins.identity.core.services.groups import member_row
from plone import api
from plone.restapi.batching import HypermediaBatch
from Products.CMFPlone.Portal import PloneSite
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

        Who may read it: a manager, or somebody who is in the group. A
        membership list is personal data about other people, and the two
        callers that legitimately want it are an administrator and a member
        looking at their own team.

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

        base = f"{self.context.absolute_url()}/@group-members/{group_id}"
        brains = member_brains(
            group_id, plugin, search=self.request.form.get("query", "") or ""
        )
        batch = HypermediaBatch(self.request, brains)
        result = {
            "@id": batch.canonical_url,
            "group": group_id,
            "items_total": batch.items_total,
            "items": [member_row(brain, base) for brain in batch],
            # The nesting, so a group page can say what feeds into it without
            # a second request per level.
            "nested_groups": self._render_groups(
                plugin.getNestedGroupIds(group_id), plugin
            ),
            "parent_groups": self._render_groups(
                plugin.getGroupParentIds(group_id), plugin
            ),
        }
        if batch.links:
            result["batching"] = batch.links
        return result

    def _refuse_unless_allowed(self, group_id: str) -> JSONDict | None:
        """Return an error body unless the caller may read this membership.

        :param group_id: The group being read.
        :returns: The error body, or ``None`` when the caller is allowed.
        """
        if api.user.has_permission(MANAGE_PERMISSION):
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
            f"{MANAGE_PERMISSION!r} permission, or membership of it.",
        )

    def _render_groups(self, group_ids: tuple[str, ...], plugin) -> list[JSONDict]:
        """Render a list of group ids with their titles.

        :param group_ids: The groups to render.
        :param plugin: The profile PAS plugin.
        :returns: One entry per group, in the order given.
        """
        base = f"{self.context.absolute_url()}/@group-members"
        titles = {brain.group_id: brain.Title for brain in plugin.active_group_brains()}
        return [
            {
                "@id": f"{base}/{group_id}",
                "id": group_id,
                "title": titles.get(group_id, group_id),
            }
            for group_id in group_ids
        ]

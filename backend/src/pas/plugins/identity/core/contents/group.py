"""The ``UserGroup`` content type.

A group is a piece of content, and membership is a field on the *Profile*
rather than a list on the group. That is the direction Plone asks questions
in: ``getGroupsForPrincipal`` is called constantly and
``getGroupMembers`` rarely, so keeping membership on the member means the hot
question is answered by one brain and the rare one by a catalog query.

Membership lives on the Profile, and a group is never edited to change it.
Core implements ``IGroupManagement`` over this type -- creating and removing
the content, and writing membership to the *user* -- so a group can be added
through ``api.group.create`` like any other.

**Groups nest, two ways, and they mean one thing.** A group may be *filed
inside* another group -- the FTI allows ``UserGroup`` within ``UserGroup`` --
and it also carries ``group_ids``, from the same
:class:`~pas.plugins.identity.core.behaviors.membership.IGroupMembership` behavior a
Profile carries. Both say the group belongs to another group, so everybody in
an inner group is in the outer one, the way a GitHub child team inherits its
parent's access.

The two are unioned rather than ranked. Containment is what an operator
reaches for -- drag a team into a team and the hierarchy is the tree they can
see -- and the field is what a provider's group map writes and what expresses
an edge across the tree. A group can use either or both, and a group that does
both contributes the edge once.

This was refused once, on the grounds that a group whose members are groups
makes ``getGroupsForPrincipal`` recursive and that a recursive answer computed
from brains stops being a single lookup. The first half is true; the second
turned out not to matter, because the recursion is not over the thing that is
large. A site has as many groups as it has teams, the whole graph is in
catalog metadata, and one query returns it -- so the cost grows with the
number of teams rather than with the number of people. See
:mod:`pas.plugins.identity.core.utils.nesting`, which also says what happens to a
cycle.
"""

from pas.plugins.identity import _
from pas.plugins.identity import logger
from pas.plugins.identity.core.interfaces import IGroupContent
from plone.dexterity.content import Container
from plone.supermodel import model
from zope import schema
from zope.interface import implementer


class IUserGroupSchema(model.Schema, IGroupContent):
    """Schema of the UserGroup content type.

    Extends :class:`~pas.plugins.identity.core.interfaces.IGroupContent`,
    which is how core knows objects of this type are groups and may create
    and remove them. ``group_id`` was already declared here; claiming the
    marker states the contract rather than adding to it, and carries the
    placement clause the user side does -- the object's id within its
    container is the group id.

    ``group_ids`` -- the groups this group is nested inside -- comes from the
    :class:`~pas.plugins.identity.core.behaviors.membership.IGroupMembership` behavior
    the FTI enables, which is the same behavior the Profile type enables.
    """

    title = schema.TextLine(
        title=_("Title"),
        description=_("Shown wherever the group is listed."),
        required=True,
    )

    description = schema.Text(
        title=_("Description"),
        required=False,
    )


@implementer(IUserGroupSchema)
class UserGroup(Container):
    """A user group.

    Folderish because a group holds groups: the FTI allows ``UserGroup``
    inside ``UserGroup`` and nothing else, and a group filed inside another is
    a member of it. See :mod:`pas.plugins.identity.core.utils.nesting`.

    A group id is the object's own id, so it is unique within a folder and
    nothing more -- which stopped being enough the moment there was more than
    one folder groups can live in. Local roles, sharing entries and every
    ``group_ids`` value in the site are written in terms of that id, so a
    second group claiming one is refused on the way in by
    :func:`~pas.plugins.identity.core.subscribers.refuse_duplicate_group`.
    """

    @property
    def group_id(self) -> str:
        """Return the canonical group id, which is the object's own id.

        Computed rather than stored, for the reason a Profile's ``userid``
        is: two values that had to be equal, with nothing making them so.
        Local roles and sharing settings store this id, so a group whose
        field and object id had drifted apart kept its sharing entries and
        stopped being findable by the plugin that has to remove it.

        :returns: The group id.
        """
        return self.getId()

    @group_id.setter
    def group_id(self, value: str) -> None:
        """Accept a write of the derived id, and discard it.

        Nothing may change this value -- it is the object's id -- but a
        great deal of code writes it: Dexterity's factory setattrs every
        keyword it is handed, and every payload exported before it became
        derived still carries the key. Raising would turn each of those into
        a failed creation or a failed import for a value that was already
        correct.

        A write that *disagrees* with the id is a different matter, and is
        logged: it is somebody trying to reassign a principal, which is
        exactly what this property exists to make impossible.

        :param value: The value being written, which is ignored.
        """
        if value and value != self.getId():
            logger.warning(
                "Ignoring an attempt to set a group id to %r on %r; it is "
                "derived from the object id",
                value,
                self.getId(),
            )

    def Title(self) -> str:
        """Return the display title.

        :returns: The title, falling back to the group id.
        """
        return self.title or self.group_id or ""

    def Description(self) -> str:
        """Return the description.

        :returns: The description, or an empty string.
        """
        return self.description or ""

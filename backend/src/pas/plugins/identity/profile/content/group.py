"""The ``IdentityGroup`` content type (§4.7, Gate 6d).

A group is a piece of content, and membership is a field on the *Profile*
rather than a list on the group. That is the direction Plone asks questions
in: ``getGroupsForPrincipal`` is called constantly and
``getGroupMembers`` rarely, so keeping membership on the member means the hot
question is answered by one brain and the rare one by a catalog query.

Membership is changed by editing a Profile and nothing else. ``IGroupManagement``
is explicitly out of scope for v1 (§7), so there is no write API here and no
way to acquire one by accident.

No nesting in v1 either: a group whose members are groups makes
``getGroupsForPrincipal`` recursive, and a recursive answer computed from
brains stops being a single lookup.
"""

from pas.plugins.identity import _
from plone.dexterity.content import Container
from plone.supermodel import model
from zope import schema
from zope.interface import implementer


class IGroupSchema(model.Schema):
    """Schema of the Group content type."""

    group_id = schema.TextLine(
        title=_("Group ID"),
        description=_(
            "The id Plone knows this group by. Assigned once and never "
            "changed: it is what local roles and sharing settings store."
        ),
        required=True,
    )

    title = schema.TextLine(
        title=_("Title"),
        description=_("Shown wherever the group is listed."),
        required=True,
    )

    description = schema.Text(
        title=_("Description"),
        required=False,
    )


@implementer(IGroupSchema)
class Group(Container):
    """A Group.

    Folderish for the same reason a Profile is: a deployment may want to file
    content under a group. Nothing in this layer puts anything inside one.
    """

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

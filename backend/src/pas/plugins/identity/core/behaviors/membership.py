"""Group membership, as a behavior.

``group_ids`` used to be a field on the Profile schema. It is the same field
and the same storage -- a schema-only behavior stores its attributes on the
content object, so a Profile still answers ``profile.group_ids`` and the
catalog still indexes it -- but it is now something a *type* opts into rather
than something one type owns.

Two things follow, and the second is the reason for the move.

**A site with its own user type gets membership without reimplementing it.**
:class:`~pas.plugins.identity.core.interfaces.IUserContent` promises the
attribute, and before this the only way to promise it was to declare the field
again, with the same vocabulary and the same two permissions, and keep them in
step by hand.

**A group can belong to a group.** The behavior is enabled on the Group type
as well, and there ``group_ids`` means the groups this *group* is a member of.
That is what makes nesting work in the same direction everything else here
does: membership is always a fact stored on the member, whether the member is
a person or a group, so the transitive answer is a walk over the same field
rather than a second kind of edge. See
:mod:`pas.plugins.identity.core.utils.nesting`.

**Ordering matters on the form, not in the data.** The field lives in a
``groups`` fieldset so that a Profile's edit form keeps the personal fields
together and puts membership on its own tab, where it is also the only field
carrying a different write permission -- the owner of a profile may edit it
and may not grant themselves a group.
"""

from pas.plugins.identity import _
from pas.plugins.identity.core.vocabularies.groups import GROUPS_VOCABULARY
from plone.autoform.directives import read_permission
from plone.autoform.directives import write_permission
from plone.supermodel import model
from zope import schema


#: Name the fieldset is registered under, and the id a form renders it with.
FIELDSET = "groups"


class IGroupMembership(model.Schema):
    """The groups a principal belongs to.

    Enabled on both principal types. On a user it is the groups that user is
    in; on a group it is the groups that group is in, which is nesting.
    """

    model.fieldset(
        FIELDSET,
        label=_("Groups"),
        fields=["group_ids"],
    )

    group_ids = schema.Tuple(
        title=_("Groups"),
        description=_(
            "The groups this principal belongs to. Membership is kept on the "
            "member rather than on the group, so editing this field and "
            "calling api.group.add_user are two ways to the same place. On a "
            "group, this nests it: everybody in this group is also in every "
            "group named here."
        ),
        # A vocabulary rather than free text. The value is a group id and
        # nothing checked that it named a group: the groups plugin filters an
        # unknown id out rather than failing, so a typo produced a membership
        # that silently granted nothing.
        value_type=schema.Choice(vocabulary=GROUPS_VOCABULARY),
        required=False,
        missing_value=(),
        default=(),
    )
    # Not ``.edit``: see permissions.zcml. The owner of a profile holds the
    # edit permission on it, and this field is what grants roles.
    write_permission(group_ids="pas.plugins.identity.content.editgroups")
    read_permission(group_ids="pas.plugins.identity.content.view")


__all__ = ["FIELDSET", "IGroupMembership"]

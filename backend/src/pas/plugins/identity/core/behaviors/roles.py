"""A group's global roles, as a field that stores nothing.

Global roles for a group are set in the groups control panel, which writes
them through ``portal_groups``. There was no way to carry them in content, so
an import that created a group could not give it a role: every restored site
needed somebody to reopen the control panel and redo by hand what the export
already knew.

**Nothing is stored on the content object, and that is the whole design.**
A stored copy would be a second source of truth, and the moment anybody
touched the groups control panel the two would disagree -- with no way to tell
which was right, because both would look authoritative. So this is a *factory*
behavior rather than a schema-only one: the adapter reads and writes the real
store, and there is no second copy to drift.

That is the same shape as
:attr:`~pas.plugins.identity.core.contents.profile.UserProfile.email`, whose
getter derives from the identity store and whose setter accepts a write and
pushes it into that store rather than keeping a value of its own. The reason
a setter exists at all is the same too: the Dexterity factory setattrs every
keyword it is handed, and an import payload carries the key.

**Writing this field grants roles**, which is why it carries a permission of
its own and why that permission is ``Manager`` and nothing else. Without it,
anybody able to edit a group could write ``Manager``, add themselves to the
group, and be done -- the same shape of hole that
:data:`~pas.plugins.identity.core.behaviors.membership.FIELDSET` exists to
close for ``group_ids``, one step further along: that field decides who is in
a group, this one decides what the group is allowed to do.

**And the field only reaches a form because of the marker below.** Enabling a
behavior on a type does not put its fields on a form: ``@types`` and every
autoform-built form ask for the behaviors marked ``IFormFieldProvider`` and
skip the rest, silently.
"""

from pas.plugins.identity import _
from plone import api
from plone.api.exc import GroupNotFoundError
from plone.autoform.directives import write_permission
from plone.autoform.interfaces import IFormFieldProvider
from plone.supermodel import model
from zope import schema
from zope.component import adapter
from zope.interface import implementer
from zope.interface import provider


#: Name the fieldset is registered under, and the id a form renders it with.
FIELDSET = "roles"

#: Roles nobody is granted and nobody can be granted.
#:
#: ``Authenticated`` is computed from having a session and PlonePAS adds it to
#: every decorated group; ``Anonymous`` is its opposite. Neither is an
#: assignment, so neither is reported here -- and ``plone.api`` raises rather
#: than granting them, which is the same judgement made one layer down.
COMPUTED_ROLES = frozenset({"Anonymous", "Authenticated"})


# What makes the field appear on a form at all; see the module docstring.
@provider(IFormFieldProvider)
class IGlobalRoles(model.Schema):
    """The site-wide roles a group grants its members."""

    model.fieldset(
        FIELDSET,
        label=_("Roles"),
        fields=["global_roles"],
    )

    global_roles = schema.Tuple(
        title=_("Global roles"),
        description=_(
            "Site-wide roles every member of this group holds. The same "
            "roles the groups control panel sets, readable and writable here "
            "so that an export carries them and an import restores them."
        ),
        required=False,
        default=(),
        missing_value=(),
        value_type=schema.Choice(vocabulary="plone.app.vocabularies.Roles"),
    )

    write_permission(global_roles="pas.plugins.identity.content.editroles")


@implementer(IGlobalRoles)
@adapter(IGlobalRoles)
class GlobalRoles:
    """Read and write a group's global roles where the site keeps them.

    Holds no state. Every read asks ``portal_groups`` and every write goes
    to it, so this adapter cannot disagree with the control panel.
    """

    def __init__(self, context) -> None:
        """Bind to the group whose roles these are.

        :param context: The group content object.
        """
        self.context = context

    @property
    def _group_id(self) -> str:
        """Return the group id PAS knows this object by.

        :returns: The group id.
        """
        return self.context.group_id

    @property
    def global_roles(self) -> tuple[str, ...]:
        """Return the site-wide roles assigned to this group.

        Sorted, so that a form, an export and a diff all agree on the order
        of something the site stores as a set.

        :returns: Role names, empty when the group holds none -- and empty
            when PAS cannot resolve the group at all, which is the state
            between creating the content object and its being indexed.
        """
        try:
            assigned = api.group.get_roles(groupname=self._group_id)
        except GroupNotFoundError:
            return ()
        return tuple(sorted(set(assigned) - COMPUTED_ROLES))

    @global_roles.setter
    def global_roles(self, value: tuple[str, ...] | None) -> None:
        """Set the group's roles to exactly what is written.

        A field write replaces, so this grants what is newly named and
        revokes what is no longer named. Computed roles are dropped rather
        than passed on: ``plone.api`` raises on being asked to grant one, and
        a payload that happens to carry ``Authenticated`` -- an export of
        ``getRoles()`` taken by hand, say -- should not fail an import over a
        value that was never an assignment.

        :param value: The roles this group should hold.
        """
        wanted = {role for role in (value or ()) if role not in COMPUTED_ROLES}
        try:
            current = set(api.group.get_roles(groupname=self._group_id))
        except GroupNotFoundError:
            # No group to grant to yet. Nothing is stored here to apply
            # later, deliberately: a pending value would be the second
            # source of truth this design exists to avoid.
            return
        current -= COMPUTED_ROLES
        if wanted == current:
            return
        if granted := wanted - current:
            api.group.grant_roles(groupname=self._group_id, roles=sorted(granted))
        if revoked := current - wanted:
            api.group.revoke_roles(groupname=self._group_id, roles=sorted(revoked))


__all__ = [
    "COMPUTED_ROLES",
    "FIELDSET",
    "GlobalRoles",
    "IGlobalRoles",
]

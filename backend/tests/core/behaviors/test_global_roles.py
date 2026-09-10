"""A group's global roles, read and written where the site keeps them.

The interesting property is a negative one: there is no second copy. Two of
these tests exist to prove that changing the roles *outside* the field is
visible *through* the field, and the other way round -- which is the whole
reason this is a factory behavior rather than a stored one.
"""

from pas.plugins.identity.core.behaviors.roles import COMPUTED_ROLES
from pas.plugins.identity.core.behaviors.roles import IGlobalRoles
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID

import pytest


class GroupCase:
    """A content group with a PAS group behind it."""

    def roles_of(self, group) -> tuple[str, ...]:
        """Return the roles the behavior reports.

        :param group: The group content object.
        :returns: The roles.
        """
        return IGlobalRoles(group).global_roles

    def set_roles(self, group, *roles: str) -> None:
        """Write roles through the behavior.

        :param group: The group content object.
        :param roles: The roles it should hold.
        """
        IGlobalRoles(group).global_roles = tuple(roles)


class TestReading(GroupCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_group) -> None:
        self.portal = portal
        self.group = make_group("editors")

    def test_a_new_group_holds_none(self):
        """Empty rather than ``None``: a caller iterating should not guard."""
        assert self.roles_of(self.group) == ()

    def test_it_reports_what_the_control_panel_granted(self):
        """The no-drift property, in the direction that breaks a stored field.

        Nothing here touches the content object, so a stored copy would still
        be reporting the empty tuple.
        """
        api.group.grant_roles(groupname="editors", roles=["Editor"])

        assert self.roles_of(self.group) == ("Editor",)

    def test_it_is_sorted(self):
        """The site stores a set; a form, an export and a diff want an
        order."""
        api.group.grant_roles(groupname="editors", roles=["Reviewer", "Editor"])

        assert self.roles_of(self.group) == ("Editor", "Reviewer")

    def test_computed_roles_are_not_reported(self):
        """``Authenticated`` is not an assignment.

        PlonePAS adds it to every decorated group, so reporting it would put a
        value in the field that cannot be written back -- ``plone.api`` raises
        rather than granting it.
        """
        api.group.grant_roles(groupname="editors", roles=["Editor"])

        assert not COMPUTED_ROLES & set(self.roles_of(self.group))


class TestWriting(GroupCase):
    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_group) -> None:
        self.portal = portal
        self.group = make_group("editors")

    def test_a_write_grants(self):
        """The import case."""
        self.set_roles(self.group, "Editor")

        assert "Editor" in api.group.get_roles(groupname="editors")

    def test_the_control_panel_sees_it(self):
        """The no-drift property in the other direction."""
        self.set_roles(self.group, "Editor", "Reviewer")

        granted = set(api.group.get_roles(groupname="editors"))

        assert {"Editor", "Reviewer"} <= granted

    def test_a_write_replaces_rather_than_adds(self):
        """A field write means "these are the roles", not "these as well"."""
        self.set_roles(self.group, "Editor", "Reviewer")

        self.set_roles(self.group, "Editor")

        assert self.roles_of(self.group) == ("Editor",)
        assert "Reviewer" not in api.group.get_roles(groupname="editors")

    def test_an_empty_write_revokes_everything(self):
        """Clearing the field is an instruction, unlike an absent import key."""
        self.set_roles(self.group, "Editor")

        self.set_roles(self.group)

        assert self.roles_of(self.group) == ()

    def test_writing_the_same_roles_changes_nothing(self):
        """Idempotent, so a re-import is not a permission rewrite."""
        self.set_roles(self.group, "Editor")
        self.set_roles(self.group, "Editor")

        assert self.roles_of(self.group) == ("Editor",)

    def test_a_computed_role_in_the_payload_is_dropped(self):
        """Rather than raising.

        ``plone.api`` refuses to grant ``Authenticated``, and an export taken
        by hand from ``getRoles()`` carries it. Failing the import over a
        value that was never an assignment would be the wrong answer.
        """
        self.set_roles(self.group, "Editor", "Authenticated")

        assert self.roles_of(self.group) == ("Editor",)

    def test_nothing_is_stored_on_the_content_object(self):
        """The design, asserted directly.

        A factory behavior keeps no attribute. If this ever starts passing
        with a value, there is a second source of truth and the drift is back.
        """
        self.set_roles(self.group, "Editor")

        assert "global_roles" not in self.group.__dict__


class TestThePermission(GroupCase):
    """Writing this field grants roles, so it is not an ordinary edit.

    A Site Administrator may edit a group and may not grant it a role: anyone
    who could would be able to grant ``Manager`` and then join the group.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, portal, make_group) -> None:
        self.portal = portal
        self.group = make_group("editors")

    def test_a_manager_may_write_it(self):
        """The role the permission is granted to."""
        setRoles(self.portal, TEST_USER_ID, ["Manager"])

        assert api.user.has_permission(
            "pas.plugins.identity: Edit Group Global Roles",
            obj=self.group,
        )

    def test_a_site_administrator_may_not(self):
        """Stricter than the membership permission beside it.

        Delegating group membership to a Site Administrator is a normal
        arrangement. Delegating the power to mint administrators is not.
        """
        setRoles(self.portal, TEST_USER_ID, ["Site Administrator"])

        assert not api.user.has_permission(
            "pas.plugins.identity: Edit Group Global Roles",
            obj=self.group,
        )

    def test_an_ordinary_member_may_not(self):
        """The hole this closes: edit a group, grant it Manager, join it."""
        setRoles(self.portal, TEST_USER_ID, ["Member"])

        assert not api.user.has_permission(
            "pas.plugins.identity: Edit Group Global Roles",
            obj=self.group,
        )

    def test_it_is_stricter_than_editing_the_group(self):
        """A Site Administrator can still edit the group itself.

        Which is the point: the field is fenced off, not the object.
        """
        setRoles(self.portal, TEST_USER_ID, ["Site Administrator"])

        assert api.user.has_permission("Modify portal content", obj=self.group)
        assert not api.user.has_permission(
            "pas.plugins.identity: Edit Group Global Roles",
            obj=self.group,
        )

    @pytest.mark.parametrize("transition", ["deactivate"])
    def test_not_in_any_other_state_either(self, transition: str):
        """The workflow states it in both states, so there is none in which
        it falls back to being acquired from the container."""
        setRoles(self.portal, TEST_USER_ID, ["Site Administrator"])
        with api.env.adopt_roles(["Manager"]):
            api.content.transition(obj=self.group, transition=transition)

        assert not api.user.has_permission(
            "pas.plugins.identity: Edit Group Global Roles",
            obj=self.group,
        )


class TestTheFieldIsGuardedByIt:
    """The declaration and the permission have to be the same one.

    Asserted rather than assumed, because the failure is silent both ways: a
    field naming a permission nobody manages acquires its answer from wherever
    the group happens to be filed, and a permission no field names guards
    nothing at all. Every test in ``TestThePermission`` above would pass in
    either case.
    """

    def test_global_roles_names_the_permission(self):
        """The field's write permission is the one the rolemap and the
        workflow state."""
        from plone.autoform.interfaces import WRITE_PERMISSIONS_KEY

        permissions = IGlobalRoles.queryTaggedValue(WRITE_PERMISSIONS_KEY)

        assert permissions["global_roles"] == "pas.plugins.identity.content.editroles"

    def test_it_is_not_the_ordinary_edit_permission(self):
        """The whole point. If these ever become the same string, editing a
        group and granting it Manager are the same action again."""
        from plone.autoform.interfaces import WRITE_PERMISSIONS_KEY

        permissions = IGlobalRoles.queryTaggedValue(WRITE_PERMISSIONS_KEY)

        assert permissions["global_roles"] != "pas.plugins.identity.content.edit"

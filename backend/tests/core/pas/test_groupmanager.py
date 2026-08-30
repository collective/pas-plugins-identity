"""Managing groups on a site that keeps its groups as content.

The counterpart of :mod:`tests.core.pas.test_useradder`, and deliberately
asymmetric with it, because PAS is: there is no ``IGroupAdderPlugin``. Group
creation goes through PlonePAS's ``GroupTool``, which loops over
``IGroupManagement`` plugins and stops at the first that returns true -- the
same "decline and fall through" the user adder relies on, reached through a
different interface in a different package.

Of the six methods the interface declares, the tool calls four. ``addGroup``,
``removeGroup``, ``addPrincipalToGroup`` and ``removePrincipalFromGroup`` are
tested here. ``updateGroup`` and ``setRolesForGroup`` are never reached -- the
tool edits a group through the group object and routes roles to a role
manager -- so they refuse rather than report a success nobody performed.

Membership is written to the **member**, not to the group. That is the
direction Plone asks the question in, and it is why ``IUserContent`` promises
``group_ids``. The member may itself be a group, which nests it: the same
write on the same side, so the transitive answer is a walk over one field
rather than a second kind of edge.
"""

from .stubs import add_type
from .stubs import GROUP_TYPE
from .stubs import GROUPS
from .stubs import install_enumerator
from .stubs import IStubGroupSchema
from .stubs import IStubUserSchema
from .stubs import USER_TYPE
from .stubs import USERS
from pas.plugins.identity.core.pas import PLUGIN_ID
from pas.plugins.identity.core.pas.plugin import GROUP_CONTAINER_PATH_RECORD
from pas.plugins.identity.core.pas.plugin import GROUP_CONTENT_TYPE_RECORD
from pas.plugins.identity.core.pas.plugin import USER_CONTAINER_PATH_RECORD
from pas.plugins.identity.core.pas.plugin import USER_CONTENT_TYPE_RECORD
from plone import api

import pytest


@pytest.fixture
def configured(portal, acl_users):
    """A site keeping both its users and its groups as content.

    The stub enumerator matters as much as the records: PAS looks a group
    straight back up after creating it, and core does not enumerate. See
    :mod:`.stubs`.

    :param portal: The Plone site.
    :param acl_users: The site's PAS instance.
    :returns: The Plone site.
    """
    add_type(portal, USER_TYPE, f"{IStubUserSchema.__module__}.IStubUserSchema")
    add_type(portal, GROUP_TYPE, f"{IStubGroupSchema.__module__}.IStubGroupSchema")
    api.content.create(container=portal, type="Folder", id=USERS)
    api.content.create(container=portal, type="Folder", id=GROUPS)
    install_enumerator(acl_users)
    api.portal.set_registry_record(USER_CONTENT_TYPE_RECORD, USER_TYPE)
    api.portal.set_registry_record(USER_CONTAINER_PATH_RECORD, USERS)
    api.portal.set_registry_record(GROUP_CONTENT_TYPE_RECORD, GROUP_TYPE)
    api.portal.set_registry_record(GROUP_CONTAINER_PATH_RECORD, GROUPS)
    return portal


class TestASiteWithTheRecordsBlanked:
    """Not the default any more, and still reachable: an operator can clear
    the records in the control panel. Stock Plone is what they get."""

    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users) -> None:
        self.portal = portal
        self.plugin = acl_users[PLUGIN_ID]
        api.portal.set_registry_record(GROUP_CONTENT_TYPE_RECORD, "")
        api.portal.set_registry_record(GROUP_CONTAINER_PATH_RECORD, "")

    def test_add_declines(self):
        assert self.plugin.addGroup("editors") is False

    def test_remove_declines(self):
        assert self.plugin.removeGroup("editors") is False

    def test_a_group_is_still_created_by_source_groups(self):
        """The plugin being registered must not break adding a group on a
        site that ignores it."""
        api.group.create(groupname="editors")

        assert api.group.get(groupname="editors") is not None


class TestCreatingAndRemoving:
    @pytest.fixture(autouse=True)
    def _setup(self, configured, acl_users) -> None:
        self.portal = configured
        self.plugin = acl_users[PLUGIN_ID]

    def test_it_creates_the_content(self):
        assert self.plugin.addGroup("editors", title="Editors") is True
        assert "editors" in self.portal[GROUPS]

    def test_it_records_the_group_id_and_title(self):
        self.plugin.addGroup("editors", title="Editors")
        obj = self.portal[GROUPS]["editors"]

        assert obj.group_id == "editors"
        assert obj.title == "Editors"

    def test_the_title_falls_back_to_the_id(self):
        """A group with no title is still a group, and an empty one in a
        listing reads as a bug."""
        self.plugin.addGroup("editors")

        assert self.portal[GROUPS]["editors"].title == "editors"

    def test_it_removes_its_own(self):
        self.plugin.addGroup("editors")

        assert self.plugin.removeGroup("editors") is True
        assert "editors" not in self.portal[GROUPS]

    def test_the_tool_reaches_this_plugin(self):
        """End to end, which is the only way ordering gets tested.

        PlonePAS walks the IGroupManagement plugins in registration order and
        stops at the first that returns true. If ``source_groups`` is reached
        first every test above passes and the feature does nothing.
        """
        api.group.create(groupname="editors", title="Editors")

        assert "editors" in self.portal[GROUPS]

    def test_it_declines_to_remove_a_group_it_does_not_own(self):
        """A site running this and source_groups must not have one deleting
        the other's groups."""
        assert self.plugin.removeGroup("administrators") is False


class TestDeletingThroughTheTool:
    """Deletion as Plone performs it, rather than as the plugin performs it.

    Every test above calls ``plugin.removeGroup`` directly, and that is what
    let a plain 503 through review: ``GroupsTool.removeGroup`` loops *every*
    ``IGroupManagement`` plugin without stopping, and ``source_groups`` raises
    ``KeyError`` for a group it never had. Ours deleted the content object,
    the stock plugin raised on the same id, and the whole transaction rolled
    back -- so the caller saw a 503 and the group was still there.

    :mod:`pas.plugins.identity.core.patches` repairs the tool. These tests
    assert the *behavior*, not the patch, so they keep passing on the day
    PlonePAS ships the fix and the patch is dropped.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, configured, acl_users) -> None:
        self.portal = configured
        self.plugin = acl_users[PLUGIN_ID]
        self.tool = api.portal.get_tool("portal_groups")

    def test_it_deletes_a_content_group(self):
        api.group.create(groupname="editors", title="Editors")
        assert "editors" in self.portal[GROUPS]

        api.group.delete(groupname="editors")

        assert "editors" not in self.portal[GROUPS]

    def test_it_reports_the_removal(self):
        """False here reads as 'nothing was deleted' to every caller."""
        api.group.create(groupname="editors", title="Editors")

        assert api.group.delete(groupname="editors") is True

    def test_a_source_groups_group_still_deletes(self):
        """The repair must not cost the stock plugin its own deletions."""
        self.portal.acl_users.source_groups.addGroup("reviewers")

        assert api.group.delete(groupname="reviewers") is True
        assert "reviewers" not in self.portal.acl_users.source_groups.listGroupIds()

    def test_a_group_no_plugin_has_is_not_an_error(self):
        """Every manager declines, so nothing was removed and nothing raised."""
        assert api.group.delete(groupname="nobody-has-this") is False


class TestMembership:
    @pytest.fixture(autouse=True)
    def _setup(self, configured, acl_users) -> None:
        self.portal = configured
        self.plugin = acl_users[PLUGIN_ID]
        self.plugin.doAddUser("alice", "irrelevant")
        self.plugin.addGroup("editors")
        self.user = self.portal[USERS]["alice"]

    def test_membership_is_written_to_the_user(self):
        """Not to the group. ``getGroupsForPrincipal`` is the hot path."""
        assert self.plugin.addPrincipalToGroup("alice", "editors") is True

        assert self.user.group_ids == ("editors",)

    def test_adding_twice_does_not_duplicate(self):
        self.plugin.addPrincipalToGroup("alice", "editors")
        self.plugin.addPrincipalToGroup("alice", "editors")

        assert self.user.group_ids == ("editors",)

    def test_it_removes_a_membership(self):
        self.plugin.addPrincipalToGroup("alice", "editors")

        assert self.plugin.removePrincipalFromGroup("alice", "editors") is True
        assert self.user.group_ids == ()

    def test_removing_one_that_is_not_there_declines(self):
        assert self.plugin.removePrincipalFromGroup("alice", "editors") is False

    def test_an_unknown_user_declines(self):
        """Somebody in source_users, for instance. Their membership is not
        this plugin's to record."""
        assert self.plugin.addPrincipalToGroup("nobody", "editors") is False

    def test_an_unknown_group_declines(self):
        assert self.plugin.addPrincipalToGroup("alice", "nosuchgroup") is False

    def test_a_group_can_be_nested_in_a_group(self):
        """The same write on the same side: membership is a fact stored on the
        member, whether the member is a person or a group."""
        self.plugin.addGroup("staff")

        assert self.plugin.addPrincipalToGroup("staff", "editors") is True

    def test_nesting_writes_the_edge_on_the_inner_group(self):
        """Which is what makes the closure a walk over one field."""
        self.plugin.addGroup("staff")

        self.plugin.addPrincipalToGroup("staff", "editors")

        staff = self.plugin._content_group("staff")
        assert "editors" in staff.group_ids

    def test_un_nesting_removes_it_again(self):
        self.plugin.addGroup("staff")
        self.plugin.addPrincipalToGroup("staff", "editors")

        assert self.plugin.removePrincipalFromGroup("staff", "editors") is True
        assert self.plugin._content_group("staff").group_ids == ()

    def test_a_group_inside_itself_is_refused(self):
        """It grants nothing and means nothing; the closure would answer
        correctly and the edit form would show a row nobody can account
        for."""
        assert self.plugin.addPrincipalToGroup("editors", "editors") is False


class TestTheMethodsPloneNeverCalls:
    """Declared by the interface, unreachable through the tool.

    An honest refusal beats a success nobody performed: if PlonePAS ever does
    start calling them, a False is a visible no-op and a True is a silent
    data loss.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, configured, acl_users) -> None:
        self.plugin = acl_users[PLUGIN_ID]

    def test_update_refuses(self):
        assert self.plugin.updateGroup("editors", title="Other") is False

    def test_set_roles_refuses(self):
        assert self.plugin.setRolesForGroup("editors", ("Reader",)) is False

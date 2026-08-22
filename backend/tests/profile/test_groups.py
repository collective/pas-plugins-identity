"""Content-backed groups.

Membership lives on the Profile, not on the group, because that is the
direction Plone asks questions in: ``getGroupsForPrincipal`` runs on every
permission check that touches a local role, while ``getGroupMembers`` runs
when somebody opens a listing. Keeping membership on the member makes the hot
question one metadata read.

There is no write API. ``IGroupManagement`` is out of scope for v1, so
membership changes by editing a Profile and by nothing else.
"""

from . import PROFILE_ID
from pas.plugins.identity.profile.catalog import GROUP_PORTAL_TYPE
from pas.plugins.identity.profile.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.profile.pas import GROUP_STATES_RECORD
from pas.plugins.identity.profile.pas import PLUGIN_ID
from plone import api
from Products.PluggableAuthService.interfaces.plugins import IGroupEnumerationPlugin
from Products.PluggableAuthService.interfaces.plugins import IGroupsPlugin

import pytest


pytestmark = pytest.mark.portal(profiles=[PROFILE_ID])


@pytest.fixture
def make_member(portal, acl_users):
    """Return a factory for a user with a Profile and group memberships.

    :param portal: The Plone site.
    :param acl_users: The site's PAS instance.
    :returns: Callable taking a userid and group ids.
    """

    def factory(userid: str, *group_ids: str) -> object:
        acl_users.source_users.addUser(userid, userid, "placeholder-password")
        return api.content.create(
            container=portal["identity-profiles"],
            type=PROFILE_PORTAL_TYPE,
            id=userid,
            userid=userid,
            login=f"{userid}@example.com",
            group_ids=tuple(group_ids),
        )

    return factory


class TestInstallation:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users) -> None:
        self.portal = portal
        self.acl_users = acl_users

    def test_type_registered(self):
        """The group content type is installed with the extra."""
        types = api.portal.get_tool("portal_types")

        assert GROUP_PORTAL_TYPE in types.objectIds()

    def test_workflow_bound(self):
        """Two states, so a group can stop granting without being deleted."""
        workflows = api.portal.get_tool("portal_workflow")

        assert workflows.getChainForPortalType(GROUP_PORTAL_TYPE) == (
            "identity_group_workflow",
        )

    def test_groups_plugin_activated(self):
        """PAS asks this self.plugin who somebody's groups are."""
        assert PLUGIN_ID in self.acl_users.plugins.listPluginIds(IGroupsPlugin)

    def test_group_enumeration_activated(self):
        """And which groups exist."""
        assert PLUGIN_ID in self.acl_users.plugins.listPluginIds(
            IGroupEnumerationPlugin
        )

    def test_no_group_management(self):
        """v1 has no write API, deliberately.

        Pinned so that implementing one is a decision rather than something
        that happens because a base class grew a method.
        """
        from Products.PlonePAS.interfaces.group import IGroupManagement

        assert not IGroupManagement.providedBy(self.acl_users[PLUGIN_ID])


class TestMembership:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, plugin, make_group, make_member) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.plugin = plugin
        self.make_group = make_group
        self.make_member = make_member

    def test_groups_come_from_the_profile(self):
        """The gate's own wording: from brain metadata."""
        self.make_group("editors")
        self.make_member("alice", "editors")

        principal = self.acl_users.getUserById("alice")

        assert self.plugin.getGroupsForPrincipal(principal) == ("editors",)

    def test_several_groups(self):
        """Order follows the field, not the catalog."""
        self.make_group("editors")
        self.make_group("reviewers")
        self.make_member("alice", "editors", "reviewers")

        principal = self.acl_users.getUserById("alice")

        assert self.plugin.getGroupsForPrincipal(principal) == (
            "editors",
            "reviewers",
        )

    def test_a_user_without_a_profile_has_none(self):
        """A site can hold users this layer knows nothing about."""
        self.acl_users.source_users.addUser("bob", "bob", "placeholder-password")

        assert (
            self.plugin.getGroupsForPrincipal(self.acl_users.getUserById("bob")) == ()
        )

    def test_a_profile_without_groups_has_none(self):
        """The common case."""
        self.make_member("alice")

        assert (
            self.plugin.getGroupsForPrincipal(self.acl_users.getUserById("alice")) == ()
        )

    def test_a_group_that_does_not_exist_grants_nothing(self):
        """A deleted group must stop granting, not keep granting by id."""
        self.make_member("alice", "ghosts")

        assert (
            self.plugin.getGroupsForPrincipal(self.acl_users.getUserById("alice")) == ()
        )

    def test_membership_reaches_plone(self):
        """Through PAS, which is what every permission check goes through."""
        self.make_group("editors")
        self.make_member("alice", "editors")

        assert "editors" in api.user.get(userid="alice").getGroups()


class TestDeactivation:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, plugin, make_group, make_member) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.plugin = plugin
        self.make_group = make_group
        self.make_member = make_member

    def test_deactivated_group_stops_granting(self):
        """Without editing a single Profile, which is the point of the state."""
        group = self.make_group("editors")
        self.make_member("alice", "editors")
        api.content.transition(obj=group, transition="deactivate")

        assert (
            self.plugin.getGroupsForPrincipal(self.acl_users.getUserById("alice")) == ()
        )

    def test_the_profile_is_untouched(self):
        """Reactivating must bring the membership back exactly."""
        group = self.make_group("editors")
        profile = self.make_member("alice", "editors")
        api.content.transition(obj=group, transition="deactivate")

        assert profile.group_ids == ("editors",)

    def test_reactivation_restores_membership(self):
        """The membership it always had."""
        group = self.make_group("editors")
        self.make_member("alice", "editors")
        api.content.transition(obj=group, transition="deactivate")
        api.content.transition(obj=group, transition="reactivate")

        assert self.plugin.getGroupsForPrincipal(
            self.acl_users.getUserById("alice")
        ) == ("editors",)

    def test_deactivated_group_is_not_enumerated(self):
        """It disappears from listings as well as from membership."""
        group = self.make_group("editors")
        api.content.transition(obj=group, transition="deactivate")

        assert self.plugin.enumerateGroups(id="editors", exact_match=True) == ()

    def test_the_active_states_are_configuration(self):
        """Same machinery as the profile states."""
        self.make_group("editors")
        api.portal.set_registry_record(GROUP_STATES_RECORD, ("nothing",))

        assert self.plugin.enumerateGroups() == ()


class TestEnumeration:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, plugin, make_group, make_member) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.plugin = plugin
        self.make_group = make_group
        self.make_member = make_member

    def test_exact_id(self):
        """The lookup PAS does when resolving a stored group id."""
        self.make_group("editors")

        results = self.plugin.enumerateGroups(id="editors", exact_match=True)

        assert [record["id"] for record in results] == ["editors"]

    def test_substring_by_default(self):
        """Matching the stock plugins, which the Sharing tab expects."""
        self.make_group("editors")

        assert self.plugin.enumerateGroups(id="edit")

    def test_title_search(self):
        """People search for what they see, not for the id."""
        self.make_group("editors", title="Site Editors")

        results = self.plugin.enumerateGroups(title="site")

        assert [record["id"] for record in results] == ["editors"]

    def test_records_carry_title_and_plugin(self):
        """PAS needs both to render a row."""
        self.make_group("editors", title="Site Editors")

        record = self.plugin.enumerateGroups(id="editors", exact_match=True)[0]

        assert record["title"] == "Site Editors"
        assert record["pluginid"] == PLUGIN_ID

    def test_no_criteria_lists_everybody(self):
        """A bare call is "list them all"."""
        self.make_group("editors")
        self.make_group("reviewers")

        assert len(self.plugin.enumerateGroups()) == 2

    def test_a_non_matching_group_is_skipped(self):
        """Two groups, one criterion: only the match comes back."""
        self.make_group("editors", title="Site Editors")
        self.make_group("reviewers", title="Content Reviewers")

        results = self.plugin.enumerateGroups(title="Site")

        assert [record["id"] for record in results] == ["editors"]

    def test_max_results(self):
        """A listing asking for one must not be handed two."""
        self.make_group("editors")
        self.make_group("reviewers")

        assert len(self.plugin.enumerateGroups(max_results=1)) == 1


class TestIntrospection:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, plugin, make_group, make_member) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.plugin = plugin
        self.make_group = make_group
        self.make_member = make_member

    def test_group_ids(self):
        """Sorted, so a listing is stable between requests."""
        self.make_group("reviewers")
        self.make_group("editors")

        assert self.plugin.getGroupIds() == ["editors", "reviewers"]

    def test_get_group_by_id(self):
        """A real PloneGroup, not a dict that looks like one."""
        self.make_group("editors")

        group = self.plugin.getGroupById("editors")

        assert group is not None
        assert group.getId() == "editors"

    def test_an_unknown_group_gives_the_default(self):
        """Callers pass a default precisely because it may be missing."""
        assert self.plugin.getGroupById("nobody", default="fallback") == "fallback"

    def test_a_deactivated_group_is_not_found(self):
        """Consistent with enumeration; two answers here would be a bug."""
        group = self.make_group("editors")
        api.content.transition(obj=group, transition="deactivate")

        assert self.plugin.getGroupById("editors") is None

    def test_roles_assigned_to_a_group_are_on_it(self):
        """The group object is decorated the way PlonePAS decorates its own.

        Building something group-shaped by hand instead would look right until
        the first template asked it for its roles.
        """
        self.make_group("editors")
        self.acl_users.portal_role_manager.assignRoleToPrincipal("Reviewer", "editors")

        group = self.plugin.getGroupById("editors")

        assert "Reviewer" in group.getRoles()

    def test_every_group_is_authenticated(self):
        """As PAS expects of any principal it hands out."""
        self.make_group("editors")

        assert "Authenticated" in self.plugin.getGroupById("editors").getRoles()

    def test_get_groups(self):
        """The decorated form of getGroupIds."""
        self.make_group("editors")
        self.make_group("reviewers")

        assert [group.getId() for group in self.plugin.getGroups()] == [
            "editors",
            "reviewers",
        ]

    def test_group_members(self):
        """The rare direction of the question, answered from the index."""
        self.make_group("editors")
        self.make_member("alice", "editors")
        self.make_member("bob", "editors")
        self.make_member("carol")

        assert self.plugin.getGroupMembers("editors") == ("alice", "bob")

    def test_group_members_of_an_empty_group(self):
        """Empty, not an error."""
        self.make_group("editors")

        assert self.plugin.getGroupMembers("editors") == ()

    def test_deactivated_members_are_excluded(self):
        """A deactivated account is not a member of anything."""
        self.make_group("editors")
        profile = self.make_member("alice", "editors")
        api.content.transition(obj=profile, transition="deactivate")

        assert self.plugin.getGroupMembers("editors") == ()

    def test_enumeration_and_introspection_agree(self):
        """The gate asks for this explicitly: two views of one truth."""
        self.make_group("editors")
        self.make_group("reviewers")

        enumerated = sorted(record["id"] for record in self.plugin.enumerateGroups())

        assert enumerated == self.plugin.getGroupIds()


class TestCoexistenceWithStockPlugins:
    @pytest.fixture(autouse=True)
    def _setup(self, portal, acl_users, plugin, make_group, make_member) -> None:
        self.portal = portal
        self.acl_users = acl_users
        self.plugin = plugin
        self.make_group = make_group
        self.make_member = make_member

    def test_source_groups_still_active(self):
        """The premise: core does not switch the stock plugins off."""
        assert "source_groups" in self.acl_users.plugins.listPluginIds(IGroupsPlugin)

    def test_membership_is_a_union(self):
        """A user in a stock group and a content group is in both."""
        self.make_group("editors")
        self.make_member("alice", "editors")
        self.acl_users.source_groups.addGroup("stock")
        self.acl_users.source_groups.addPrincipalToGroup("alice", "stock")

        groups = api.user.get(userid="alice").getGroups()

        assert "editors" in groups
        assert "stock" in groups

    def test_no_duplicates(self):
        """A group id known to both plugins appears once.

        PAS collects group membership into a dict, so this holds because of
        how PAS is built rather than because of anything here. Pinned so that
        a change there surfaces instead of being compensated for.
        """
        self.make_group("shared")
        self.make_member("alice", "shared")
        self.acl_users.source_groups.addGroup("shared")
        self.acl_users.source_groups.addPrincipalToGroup("alice", "shared")

        groups = api.user.get(userid="alice").getGroups()

        assert groups.count("shared") == 1

    def test_auto_group_still_applies(self):
        """Every authenticated user keeps whatever auto_group grants."""
        self.make_group("editors")
        self.make_member("alice", "editors")

        groups = api.user.get(userid="alice").getGroups()

        assert "AuthenticatedUsers" in groups

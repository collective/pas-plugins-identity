"""Content-backed groups (Gate 6d).

Membership lives on the Profile, not on the group, because that is the
direction Plone asks questions in: ``getGroupsForPrincipal`` runs on every
permission check that touches a local role, while ``getGroupMembers`` runs
when somebody opens a listing. Keeping membership on the member makes the hot
question one metadata read.

There is no write API. ``IGroupManagement`` is out of scope for v1 (§7), so
membership changes by editing a Profile and by nothing else.
"""

from pas.plugins.identity.profile.catalog import GROUP_PORTAL_TYPE
from pas.plugins.identity.profile.catalog import PROFILE_PORTAL_TYPE
from pas.plugins.identity.profile.pas import GROUP_STATES_RECORD
from pas.plugins.identity.profile.pas import PLUGIN_ID
from plone import api
from Products.PluggableAuthService.interfaces.plugins import IGroupEnumerationPlugin
from Products.PluggableAuthService.interfaces.plugins import IGroupsPlugin

import pytest


@pytest.fixture
def acl_users(portal):
    """The site's PAS instance.

    :param portal: The Plone site.
    :returns: ``acl_users``.
    """
    return api.portal.get_tool("acl_users")


@pytest.fixture
def plugin(acl_users):
    """The profile PAS plugin.

    :param acl_users: The site's PAS instance.
    :returns: The plugin.
    """
    return acl_users[PLUGIN_ID]


@pytest.fixture
def make_group(portal):
    """Return a factory for Group content.

    :param portal: The Plone site.
    :returns: Callable taking a group id and title.
    """

    def factory(group_id: str, title: str | None = None) -> object:
        with api.env.adopt_roles(["Manager"]):
            return api.content.create(
                container=portal["identity-profiles"],
                type=GROUP_PORTAL_TYPE,
                id=group_id,
                group_id=group_id,
                title=title or group_id.title(),
            )

    return factory


@pytest.fixture
def make_member(portal, acl_users):
    """Return a factory for a user with a Profile and group memberships.

    :param portal: The Plone site.
    :param acl_users: The site's PAS instance.
    :returns: Callable taking a userid and group ids.
    """

    def factory(userid: str, *group_ids: str) -> object:
        acl_users.source_users.addUser(userid, userid, "placeholder-password")
        with api.env.adopt_roles(["Manager"]):
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
    def test_type_registered(self, portal):
        """The group content type is installed with the extra."""
        types = api.portal.get_tool("portal_types")

        assert GROUP_PORTAL_TYPE in types.objectIds()

    def test_workflow_bound(self, portal):
        """Two states, so a group can stop granting without being deleted."""
        workflows = api.portal.get_tool("portal_workflow")

        assert workflows.getChainForPortalType(GROUP_PORTAL_TYPE) == (
            "identity_group_workflow",
        )

    def test_groups_plugin_activated(self, acl_users):
        """PAS asks this plugin who somebody's groups are."""
        assert PLUGIN_ID in acl_users.plugins.listPluginIds(IGroupsPlugin)

    def test_group_enumeration_activated(self, acl_users):
        """And which groups exist."""
        assert PLUGIN_ID in acl_users.plugins.listPluginIds(IGroupEnumerationPlugin)

    def test_no_group_management(self, acl_users):
        """v1 has no write API, deliberately (§7).

        Pinned so that implementing one is a decision rather than something
        that happens because a base class grew a method.
        """
        from Products.PlonePAS.interfaces.group import IGroupManagement

        assert not IGroupManagement.providedBy(acl_users[PLUGIN_ID])


class TestMembership:
    def test_groups_come_from_the_profile(
        self, plugin, acl_users, make_group, make_member
    ):
        """The gate's own wording: from brain metadata."""
        make_group("editors")
        make_member("alice", "editors")

        principal = acl_users.getUserById("alice")

        assert plugin.getGroupsForPrincipal(principal) == ("editors",)

    def test_several_groups(self, plugin, acl_users, make_group, make_member):
        """Order follows the field, not the catalog."""
        make_group("editors")
        make_group("reviewers")
        make_member("alice", "editors", "reviewers")

        principal = acl_users.getUserById("alice")

        assert plugin.getGroupsForPrincipal(principal) == (
            "editors",
            "reviewers",
        )

    def test_a_user_without_a_profile_has_none(self, plugin, acl_users):
        """A site can hold users this layer knows nothing about."""
        acl_users.source_users.addUser("bob", "bob", "placeholder-password")

        assert plugin.getGroupsForPrincipal(acl_users.getUserById("bob")) == ()

    def test_a_profile_without_groups_has_none(self, plugin, acl_users, make_member):
        """The common case."""
        make_member("alice")

        assert plugin.getGroupsForPrincipal(acl_users.getUserById("alice")) == ()

    def test_a_group_that_does_not_exist_grants_nothing(
        self, plugin, acl_users, make_member
    ):
        """A deleted group must stop granting, not keep granting by id."""
        make_member("alice", "ghosts")

        assert plugin.getGroupsForPrincipal(acl_users.getUserById("alice")) == ()

    def test_membership_reaches_plone(self, acl_users, make_group, make_member):
        """Through PAS, which is what every permission check goes through."""
        make_group("editors")
        make_member("alice", "editors")

        assert "editors" in api.user.get(userid="alice").getGroups()


class TestDeactivation:
    def test_deactivated_group_stops_granting(
        self, plugin, acl_users, make_group, make_member
    ):
        """Without editing a single Profile, which is the point of the state."""
        group = make_group("editors")
        make_member("alice", "editors")
        with api.env.adopt_roles(["Manager"]):
            api.content.transition(obj=group, transition="deactivate")

        assert plugin.getGroupsForPrincipal(acl_users.getUserById("alice")) == ()

    def test_the_profile_is_untouched(self, portal, make_group, make_member):
        """Reactivating must bring the membership back exactly."""
        group = make_group("editors")
        profile = make_member("alice", "editors")
        with api.env.adopt_roles(["Manager"]):
            api.content.transition(obj=group, transition="deactivate")

        assert profile.group_ids == ("editors",)

    def test_reactivation_restores_membership(
        self, plugin, acl_users, make_group, make_member
    ):
        """The membership it always had."""
        group = make_group("editors")
        make_member("alice", "editors")
        with api.env.adopt_roles(["Manager"]):
            api.content.transition(obj=group, transition="deactivate")
            api.content.transition(obj=group, transition="reactivate")

        assert plugin.getGroupsForPrincipal(acl_users.getUserById("alice")) == (
            "editors",
        )

    def test_deactivated_group_is_not_enumerated(self, plugin, make_group):
        """It disappears from listings as well as from membership."""
        group = make_group("editors")
        with api.env.adopt_roles(["Manager"]):
            api.content.transition(obj=group, transition="deactivate")

        assert plugin.enumerateGroups(id="editors", exact_match=True) == ()

    def test_the_active_states_are_configuration(self, plugin, make_group):
        """Same machinery as the profile states."""
        make_group("editors")
        api.portal.set_registry_record(GROUP_STATES_RECORD, ("nothing",))

        assert plugin.enumerateGroups() == ()


class TestEnumeration:
    def test_exact_id(self, plugin, make_group):
        """The lookup PAS does when resolving a stored group id."""
        make_group("editors")

        results = plugin.enumerateGroups(id="editors", exact_match=True)

        assert [record["id"] for record in results] == ["editors"]

    def test_substring_by_default(self, plugin, make_group):
        """Matching the stock plugins, which the Sharing tab expects."""
        make_group("editors")

        assert plugin.enumerateGroups(id="edit")

    def test_title_search(self, plugin, make_group):
        """People search for what they see, not for the id."""
        make_group("editors", title="Site Editors")

        results = plugin.enumerateGroups(title="site")

        assert [record["id"] for record in results] == ["editors"]

    def test_records_carry_title_and_plugin(self, plugin, make_group):
        """PAS needs both to render a row."""
        make_group("editors", title="Site Editors")

        record = plugin.enumerateGroups(id="editors", exact_match=True)[0]

        assert record["title"] == "Site Editors"
        assert record["pluginid"] == PLUGIN_ID

    def test_no_criteria_lists_everybody(self, plugin, make_group):
        """A bare call is "list them all"."""
        make_group("editors")
        make_group("reviewers")

        assert len(plugin.enumerateGroups()) == 2

    def test_a_non_matching_group_is_skipped(self, plugin, make_group):
        """Two groups, one criterion: only the match comes back."""
        make_group("editors", title="Site Editors")
        make_group("reviewers", title="Content Reviewers")

        results = plugin.enumerateGroups(title="Site")

        assert [record["id"] for record in results] == ["editors"]

    def test_max_results(self, plugin, make_group):
        """A listing asking for one must not be handed two."""
        make_group("editors")
        make_group("reviewers")

        assert len(plugin.enumerateGroups(max_results=1)) == 1


class TestIntrospection:
    def test_group_ids(self, plugin, make_group):
        """Sorted, so a listing is stable between requests."""
        make_group("reviewers")
        make_group("editors")

        assert plugin.getGroupIds() == ["editors", "reviewers"]

    def test_get_group_by_id(self, plugin, make_group):
        """A real PloneGroup, not a dict that looks like one."""
        make_group("editors")

        group = plugin.getGroupById("editors")

        assert group is not None
        assert group.getId() == "editors"

    def test_an_unknown_group_gives_the_default(self, plugin):
        """Callers pass a default precisely because it may be missing."""
        assert plugin.getGroupById("nobody", default="fallback") == "fallback"

    def test_a_deactivated_group_is_not_found(self, plugin, make_group):
        """Consistent with enumeration; two answers here would be a bug."""
        group = make_group("editors")
        with api.env.adopt_roles(["Manager"]):
            api.content.transition(obj=group, transition="deactivate")

        assert plugin.getGroupById("editors") is None

    def test_roles_assigned_to_a_group_are_on_it(self, plugin, acl_users, make_group):
        """The group object is decorated the way PlonePAS decorates its own.

        Building something group-shaped by hand instead would look right until
        the first template asked it for its roles.
        """
        make_group("editors")
        acl_users.portal_role_manager.assignRoleToPrincipal("Reviewer", "editors")

        group = plugin.getGroupById("editors")

        assert "Reviewer" in group.getRoles()

    def test_every_group_is_authenticated(self, plugin, make_group):
        """As PAS expects of any principal it hands out."""
        make_group("editors")

        assert "Authenticated" in plugin.getGroupById("editors").getRoles()

    def test_get_groups(self, plugin, make_group):
        """The decorated form of getGroupIds."""
        make_group("editors")
        make_group("reviewers")

        assert [group.getId() for group in plugin.getGroups()] == [
            "editors",
            "reviewers",
        ]

    def test_group_members(self, plugin, make_group, make_member):
        """The rare direction of the question, answered from the index."""
        make_group("editors")
        make_member("alice", "editors")
        make_member("bob", "editors")
        make_member("carol")

        assert plugin.getGroupMembers("editors") == ("alice", "bob")

    def test_group_members_of_an_empty_group(self, plugin, make_group):
        """Empty, not an error."""
        make_group("editors")

        assert plugin.getGroupMembers("editors") == ()

    def test_deactivated_members_are_excluded(self, plugin, make_group, make_member):
        """A deactivated account is not a member of anything."""
        make_group("editors")
        profile = make_member("alice", "editors")
        with api.env.adopt_roles(["Manager"]):
            api.content.transition(obj=profile, transition="deactivate")

        assert plugin.getGroupMembers("editors") == ()

    def test_enumeration_and_introspection_agree(self, plugin, make_group):
        """The gate asks for this explicitly: two views of one truth."""
        make_group("editors")
        make_group("reviewers")

        enumerated = sorted(record["id"] for record in plugin.enumerateGroups())

        assert enumerated == plugin.getGroupIds()


class TestCoexistenceWithStockPlugins:
    def test_source_groups_still_active(self, acl_users):
        """The premise: core does not switch the stock plugins off."""
        assert "source_groups" in acl_users.plugins.listPluginIds(IGroupsPlugin)

    def test_membership_is_a_union(self, acl_users, make_group, make_member):
        """A user in a stock group and a content group is in both."""
        make_group("editors")
        make_member("alice", "editors")
        acl_users.source_groups.addGroup("stock")
        acl_users.source_groups.addPrincipalToGroup("alice", "stock")

        groups = api.user.get(userid="alice").getGroups()

        assert "editors" in groups
        assert "stock" in groups

    def test_no_duplicates(self, acl_users, make_group, make_member):
        """A group id known to both plugins appears once.

        PAS collects group membership into a dict, so this holds because of
        how PAS is built rather than because of anything here. Pinned so that
        a change there surfaces instead of being compensated for.
        """
        make_group("shared")
        make_member("alice", "shared")
        acl_users.source_groups.addGroup("shared")
        acl_users.source_groups.addPrincipalToGroup("alice", "shared")

        groups = api.user.get(userid="alice").getGroups()

        assert groups.count("shared") == 1

    def test_auto_group_still_applies(self, acl_users, make_group, make_member):
        """Every authenticated user keeps whatever auto_group grants."""
        make_group("editors")
        make_member("alice", "editors")

        groups = api.user.get(userid="alice").getGroups()

        assert "AuthenticatedUsers" in groups
